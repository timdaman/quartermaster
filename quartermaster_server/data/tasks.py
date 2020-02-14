import logging

from django.conf import settings
from django.utils.timezone import now
from huey import crontab
from huey.contrib.djhuey import lock_task, db_periodic_task

from data.models import Resource, Device
from quartermaster.AbstractShareableUsbDevice import AbstractShareableUsbDevice
from quartermaster.allocator import \
    release_reservation

logger = logging.getLogger(__name__)


@db_periodic_task(crontab(minute='*'))
@lock_task('update_reservations')
def update_reservations():
    reservation_limit = now() - settings.RESERVATION_MAX_MINUTES
    checkin_limit = now() - settings.RESERVATION_CHECKIN_TIMEOUT_MINUTES

    for resource in Resource.objects.filter(last_check_in__isnull=False):
        if reservation_limit > resource.last_reserved:
            release_reservation(resource)
        elif checkin_limit > resource.last_check_in:
            release_reservation(resource)


@db_periodic_task(crontab(minute='*/15'))
@lock_task('confirm_device_state')
def confirm_device_state():
    for device in Device.objects.all():
        device_driver: AbstractShareableUsbDevice = device.get_driver_obj()
        try:
            being_shared = device_driver.is_shared()
        except AbstractShareableUsbDevice.DeviceError:
            logger.exception(f"Error getting device status. Device={device}")
            continue

        share_expected = device.in_use
        if being_shared != share_expected:
            logger.error(f"Device state does not match expected state. Device is shared={being_shared} "
                         f"but is expected to be shared={share_expected}. Device={device}")
            if share_expected:
                device_driver.share()
            else:
                device_driver.unshare()


@db_periodic_task(crontab(minute='*'))
@lock_task('confirm_devices_are_online')
def confirm_devices_are_online():
    for device in Device.everything.all():
        device_driver: AbstractShareableUsbDevice = device.get_driver()
        try:
            device.online = device_driver.is_online()
            device.save()
        except AbstractShareableUsbDevice.DeviceError:
            logger.exception(f"Error checking if {device} is online")
            continue
