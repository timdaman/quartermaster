import logging

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
    for resource in Resource.objects.filter(last_check_in__isnull=False):
        if now() > resource.reservation_expiration or now() > resource.checkin_expiration:
            release_reservation(resource)


@db_periodic_task(crontab(minute='*'))
@lock_task('update_device_state')
def confirm_device_state():
    for device in Device.objects.all():
        device_driver: AbstractShareableUsbDevice = device.get_driver_obj()

        try:
            device.online = device_driver.is_online()
            device.save()
        except AbstractShareableUsbDevice.DeviceError:
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
        except AbstractShareableUsbDevice.DeviceError:
            logger.exception(f"Error getting device status. Device={device}")
            continue
