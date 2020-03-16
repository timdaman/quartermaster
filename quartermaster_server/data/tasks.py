import logging

from django.utils.timezone import now
from huey import crontab
from huey.contrib.djhuey import lock_task, db_periodic_task, db_task

from data.models import Resource, Device, RemoteHost, loaded_drivers
from quartermaster.AbstractShareableDevice import AbstractShareableDevice
from quartermaster.allocator import \
    release_reservation

logger = logging.getLogger(__name__)


@db_periodic_task(crontab(minute='*'))
@lock_task('update_reservations')
def update_reservations():
    for resource in Resource.objects.filter(last_check_in__isnull=False):
        if now() > resource.reservation_expiration or now() > resource.checkin_expiration:
            release_reservation(resource)


@db_periodic_task(crontab(minute='*'))
@lock_task('update_device_state')
def confirm_device_state():
    for device in Device.objects.all():
        device_driver: AbstractShareableDevice = device.get_driver_obj()

        try:
            device.online = device_driver.is_online()
            device.save()
        except AbstractShareableDevice.DeviceError:
            logger.exception(f"Error checking if {device} is online")
            continue

        if not device.online:
            continue

        try:
            being_shared = device_driver.is_shared()
            share_expected = device.in_use
            if being_shared != share_expected:
                logger.error(f"Device state does not match expected state. Device is shared={being_shared} "
                             f"but is expected to be shared={share_expected}. Device={device}")
                if share_expected:
                    device_driver.share()
                else:
                    device_driver.unshare()
        except AbstractShareableDevice.DeviceError:
            logger.exception(f"Error getting device status. Device={device}")
            continue

@db_periodic_task(crontab(minute='*'))
@lock_task('update_host_state')
def confirm_device_state():
    for host in RemoteHost.objects.all():
        update_host_devices(host)


@db_task()
def update_host_devices(host: RemoteHost):
    # FIXME: Handle offline hosts gracefully
    # For each driver
    for driver in loaded_drivers:
        # If compatible with communicator
        if host.communicator not in driver.SUPPORTED_COMMUNICATORS:
            continue

        devices_to_update = host.device_set.filter(driver=driver.__name__)
        communicator = host.get_communicator_obj()
        if not communicator.is_host_reachable():
            logger.exception(f"Could not reach host {host}")
            for device in devices_to_update:
                device.online = False
                device.save()
            continue

        # TODO: Should this (or is it already) list be filtered by online and enabled?
        driver.update_device_states(host, devices_to_update)

        # TODO: Move this to driver?
        # for devices in host.device_set.all():
        #     device_driver: AbstractShareableUsbDevice = device.get_driver_obj()
        #
        #     try:
        #         device.online = device_driver.is_online()
        #         device.save()
        #     except AbstractShareableUsbDevice.DeviceError:
        #         logger.exception(f"Error checking if {device} is online")
        #         continue
        #
        #     if not device.online:
        #         continue
        #
        #     try:
        #         being_shared = device_driver.is_shared()
        #         share_expected = device.in_use
        #         if being_shared != share_expected:
        #             logger.error(f"Device state does not match expected state. Device is shared={being_shared} "
        #                          f"but is expected to be shared={share_expected}. Device={device}")
        #             if share_expected:
        #                 device_driver.share()
        #             else:
        #                 device_driver.unshare()
        #     except AbstractShareableUsbDevice.DeviceError:
        #         logger.exception(f"Error getting device status. Device={device}")
        #         continue