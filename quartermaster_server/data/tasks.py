import logging

from django.utils.timezone import now
from huey import crontab
from huey.contrib.djhuey import lock_task, db_periodic_task, db_task

from data.models import Resource, RemoteHost, loaded_host_drivers
from quartermaster.allocator import release_reservation

logger = logging.getLogger(__name__)


@db_periodic_task(crontab(minute='*'))
@lock_task('update_reservations')
def update_reservations():
    for resource in Resource.objects.filter(last_check_in__isnull=False):
        if now() > resource.reservation_expiration or now() > resource.checkin_expiration:
            release_reservation(resource)


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

        host_driver.update_device_states(devices_to_update)
