from django.conf import settings
from django.contrib.auth.models import User
from requests import Session

TEAMCITY = Session()
TEAMCITY.auth = (settings.TEAMCITY_USER, settings.TEAMCITY_PASSWORD)
TEAMCITY_HOST = settings.TEAMCITY_HOST
TEAMCITY_RESERVATION_USERNAME = settings.TEAMCITY_RESERVATION_USERNAME

TEAMCITY_BLOCKED_JOB_PREFIX = "Build is waiting for the following resource to become available: "
try:
    TEAMCITY_USER = User.objects.get(username=TEAMCITY_RESERVATION_USERNAME)
except Exception:
    print(
        f"********Error retrieving Teamcity user, '{TEAMCITY_RESERVATION_USERNAME}. Add this user or disable TeamCity "
        f"support (by removing `Teamcity` from INSTALLED_APPS")
    # We support a missing user here because the server needs to start before
    # before we create it
    TEAMCITY_USER = None
