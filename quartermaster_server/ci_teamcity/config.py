from django.contrib.auth.models import User
from requests import Session

from quartermaster.settings import find_setting

TEAMCITY = Session()
TEAMCITY.auth = (find_setting('teamcity_user', None), find_setting('teamcity_password', None))
TEAMCITY_HOST = find_setting('teamcity_host', None)
TEAMCITY_RESERVATION_USERNAME = find_setting('TEAMCITY_RESERVATION_USERNAME', None)

TEAMCITY_BLOCKED_JOB_PREFIX = "Build is waiting for the following resource to become available: "
try:
    TEAMCITY_USER = User.objects.get(username=TEAMCITY_RESERVATION_USERNAME)
except Exception:
    print(
        f"********Error retrieving Teamcity user, '{TEAMCITY_RESERVATION_USERNAME}. Add this user or disable TeamCity "
        f"support (by removing `ci_teamcity` from ENABLED_CI")
    # We support a missing user here because the server needs to start before
    # before we create it
    TEAMCITY_USER = None
