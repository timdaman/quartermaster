import logging
from typing import Tuple

import paramiko
from django.conf import settings

logger = logging.getLogger(__name__)


class QuartermasterSSHError(Exception):
    pass


def ssh_command(command: str, host: str) -> Tuple[int, str, str]:
    try:
        client = paramiko.SSHClient()
        # TODO: This is not great, perhaps record host keys in DB?
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        client.connect(host, username=settings.SSH_USERNAME, pkey=settings.SSH_PRIVATE_KEY)
        stdin, stdout, stderr = client.exec_command(command=command)
    except paramiko.SSHException as e:
        logger.exception(f'Error: host={host}, command={command}')
        raise QuartermasterSSHError(
            f"Ran into problems connecting to {settings.SSH_USERNAME}@{host}: {e}")

    return_code = stdout.channel.recv_exit_status()
    return return_code, stdout.read().decode('UTF-8'), stderr.read().decode('UTF-8')
