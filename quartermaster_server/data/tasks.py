import logging

from django.utils.timezone import now
from huey import crontab
from huey.contrib.djhuey import lock_task, db_periodic_task, db_task

from data.models import Resource, Device, RemoteHost, loaded_device_drivers, loaded_host_drivers
from quartermaster.AbstractShareableDeviceDriver import AbstractShareableDeviceDriver
from quartermaster.allocator import release_reservation

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
        device_driver: AbstractShareableDeviceDriver = device.get_driver_obj()

        try:
            device.online = device_driver.is_online()
            device.save()
        except AbstractShareableDeviceDriver.DeviceError:
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
        except AbstractShareableDeviceDriver.DeviceError:
            logger.exception(f"Error getting device status. Device={device}")
            continue

@db_periodic_task(crontab(minute='*'))
@lock_task('update_host_state')
def confirm_device_state():
    for host in RemoteHost.objects.all():
        update_host_devices(host)


@db_task()
def update_host_devices(host: RemoteHost):
    # For each driver
    for host_driver_class in loaded_host_drivers():
        # If compatible with communicator
        if host.communicator not in host_driver_class.SUPPORTED_COMMUNICATORS:
            continue

        host_driver = host_driver_class(host=host)

        devices_to_update = host.device_set.filter(driver=host_driver_class.DEVICE_CLASS.__name__)

        if not host_driver.is_reachable:
            logger.exception(f"Could not reach host {host}")
            for device in devices_to_update:
                device.online = False
                device.save()
            continue

        # TODO: Should this (or is it already) list be filtered by online and enabled?
        host_driver.update_device_states(devices_to_update)

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
