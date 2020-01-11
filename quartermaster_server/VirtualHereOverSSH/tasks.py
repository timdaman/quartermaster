import logging

from django.conf import settings
from huey import crontab
from huey.contrib.djhuey import db_periodic_task, lock_task

from data.models import Device
from VirtualHereOverSSH import VirtualHereOverSSH

logger = logging.getLogger(__name__)

if __package__ in settings.INSTALLED_APPS:
    @db_periodic_task(crontab(minute='*/15'))
    @lock_task('check_device_nicknames')
    def check_device_nicknames():
        for device in Device.objects.filter(driver=VirtualHere.__name__):
            device_driver: VirtualHere = device.get_driver_obj()
            try:
                nickname = device_driver.get_nickname()
            except VirtualHere.DeviceError:
                logger.exception(f"Error getting device nickname. Device={device}")
                continue

            nickname_expected = device.name
            if nickname != nickname_expected:
                logger.error(f"Device nickname is incorrect. Device is nickname is '{nickname}' "
                             f"but but should be '{nickname_expected}'. Device={device}")
                device_driver.set_nickname()
