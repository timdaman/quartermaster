from django.conf import settings

if __package__ in settings.INSTALLED_APPS:
    import logging

    from huey import crontab
    from huey.contrib.djhuey import db_periodic_task, lock_task

    from data.models import RemoteHost
    from VirtualHereOverSSH import VirtualHereOverSSH, VirtualHereOverSSHHost

    logger = logging.getLogger(__name__)


    @db_periodic_task(crontab(minute='*/15'))
    @lock_task('check_device_nicknames')
    def check_device_nicknames():
        for host in RemoteHost.objects.filter(device__driver=VirtualHereOverSSH.__name__).distinct():
            host_driver = VirtualHereOverSSHHost(host=host)
            states = host_driver.get_states()
            for device in host_driver.devices():
                device_address = device.config['device_address']
                if device_address not in states:
                    continue
                if states[device_address].nickname != device.name:
                    logger.error(f"Device nickname is incorrect. "
                                 f"Device is nickname is '{states[device_address].nickname}' "
                                 f"but but should be '{device.name}'. Device={device}")
                    device_driver = host_driver.get_device_driver(device)
                    device_driver.set_nickname()
