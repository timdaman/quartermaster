import paramiko
from ..quartermaster.settings import find_setting

# TODO: Move to driver
SSH_USERNAME = find_setting('SSH_USERNAME')
SSH_PRIVATE_KEY_FILE = find_setting('SSH_PRIVATE_KEY_FILE')
SSH_PRIVATE_KEY = paramiko.Ed25519Key(filename=SSH_PRIVATE_KEY_FILE)

