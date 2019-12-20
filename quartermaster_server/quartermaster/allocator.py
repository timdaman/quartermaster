import logging
from secrets import token_urlsafe

from django.conf import settings
from django.db import transaction
from django.utils.timezone import now

from data.models import Resource
from quartermaster.helpers import for_all_devices

logger = logging.getLogger(__name__)


def make_reservation(resource: Resource, user: settings.AUTH_USER_MODEL, used_for: str):
    # If we are multi threaded there could be a race condition here between when grab and when used
    logger.info(f"Reservation being made user={user.username} used_for={used_for} resource={resource}")
    with transaction.atomic():
        resource.user = user
        resource.used_for = used_for
        resource.use_password = token_urlsafe(nbytes=10)
        resource.last_check_in = now()
        resource.last_reserved = now()
        resource.save()
        for_all_devices(resource.device_set.all(), 'share')


def update_reservation(resource: Resource):
    logger.info(f"Reservation being being updated user={resource.user.username} resource={resource}")
    resource.last_check_in = now()
    resource.save()


def refresh_reservation(resource: Resource):
    logger.info(f"Reservation device shares being refresh resource={resource}")
    resource.last_check_in = now()
    for_all_devices(resource.device_set.all(), 'refresh')
    resource.save()


def release_reservation(resource):
    with transaction.atomic():
        logger.info(f"Reservation being released user={getattr(resource.user,'username', None)} used_for={resource.used_for} resource={resource}")
        for_all_devices(resource.device_set.all(), 'unshare')
        resource.user = None
        resource.used_for = ""
        resource.use_password = ""
        resource.last_check_in = None
        resource.save()
