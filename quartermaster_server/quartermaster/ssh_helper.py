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
        return_code = stdout.channel.recv_exit_status()
        stdout_str = stdout.read().decode('UTF-8')
        stderr_str = stderr.read().decode('UTF-8')
        logger.info(
            f"host={settings.SSH_USERNAME}@{host} rc={return_code} command={command} stdout={stdout_str} stderr={stderr_str}")
    except paramiko.SSHException as e:
        logger.exception(f'Error: host={settings.SSH_USERNAME}@{host}, command={command}')
        raise QuartermasterSSHError(
            f"Ran into problems connecting to {settings.SSH_USERNAME}@{host}: {e}")

    return return_code, stdout_str, stderr_str
