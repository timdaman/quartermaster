from datetime import timedelta
from urllib.parse import urlparse

import paramiko
from io import StringIO

from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'REPLACE_THIS'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

SERVER_BASE_URL = 'http://localhost:8000'
parsed_server_base_url = urlparse(SERVER_BASE_URL)

ALLOWED_HOSTS = ['backend', 'localhost', parsed_server_base_url.netloc]

INSTALLED_APPS.extend([
    'Teamcity',
    'UsbipOverSSH',
    'VirtualHereOverSSH'
])

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'REPLAC_THIS',
        'USER': 'REPLACE_THIS',
        'PASSWORD': 'REPLACE_THIS',
        'HOST': 'REPLACE_THIS',
    }
}

HUEY['connection']['host'] = "localhost"
HUEY['consumer']['workers'] = 2

RESERVATION_MAX_MINUTES = timedelta(minutes=10)
RESERVATION_CHECKIN_TIMEOUT_MINUTES = timedelta(minutes=5)

########### SSH ###########
SSH_USERNAME = 'REPLACE_THIS'
SSH_PRIVATE_KEY = paramiko.Ed25519Key.from_private_key(StringIO(
    """-----BEGIN OPENSSH PRIVATE KEY-----
REPLACE_THIS
-----END OPENSSH PRIVATE KEY-----
"""))

########### TeamCity Intergration ###########
TEAMCITY_USER = 'REPLACE_THIS'
TEAMCITY_PASSWORD = 'REPLACE_THIS'
TEAMCITY_HOST = 'https://REPLACE_THIS'
TEAMCITY_RESERVATION_USERNAME = 'REPLACE_THIS'
