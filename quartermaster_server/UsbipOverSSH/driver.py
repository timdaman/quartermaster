import logging
import re
from typing import Tuple

import paramiko
from django.conf import settings

from quartermaster.AbstractShareableUsbDevice import AbstractShareableUsbDevice

logger = logging.getLogger(__name__)

"""
The schema for the Device `config` file is the following

{
"host": "<HOSTNAME OR IP ADDRESS OF SERVER WITH DEVICE>",
"bus_id": "<`busid` listed in `usbip list`>"
}

and example is this

{
"host": "usb_host.example.com",
"bus_id": "1-11"
}
"""


def ssh_command(command: str, host: str) -> Tuple:
    try:
        client = paramiko.SSHClient()
        # TODO: This is not great, perhaps record host keys in DB?
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        client.connect(host, username=settings.SSH_USERNAME, pkey=settings.SSH_PRIVATE_KEY)
        stdin, stdout, stderr = client.exec_command(command=command)
    except paramiko.SSHException as e:
        logger.exception(f'Error: host={host}, command={command}')
        raise e
    return_code = stdout.channel.recv_exit_status()
    return return_code, stdout, stderr


class UsbipOverSSH(AbstractShareableUsbDevice):
    NO_REMOTE_DEVICES = b'usbip: info: no exportable devices found on '
    CONFIGURATION_KEYS = ("host", "bus_id")

    @property
    def host(self):
        return self.config['host']

    def ssh(self, command: str):
        try:
            return_code, stdout, stderr = ssh_command(command=command, host=self.host)
        except paramiko.SSHException as e:
            raise self.DeviceConnectionError(
                f"Ran into problems connecting to {settings.SSH_USERNAME}@{self.host}: {e}")
        if return_code != 0:
            message = f'Error: host={self.host}, command={command}, rc={return_code}, ' \
                      f'stdout={stdout}, stderr={stderr}'
            logger.error(message)
            raise self.DeviceCommandError(message)
        return return_code, stdout, stderr

    def get_share_state(self) -> bool:
        command = "sudo usbip list -r localhost"
        return_code, stdout, stderr = self.ssh(command)

        error_messages = stderr
        if return_code != 0 and self.NO_REMOTE_DEVICES not in error_messages:
            message = f'Error: host={self.host}, command={command}, rc={return_code}, ' \
                      f'stdout={stdout}, stderr={error_messages}'
            logger.error(message)
            raise self.DeviceCommandError(message)

        output: str = stdout
        # This takes this
        #  1-11: SiGma Micro : Keyboard TRACER Gamma Ivory (1c4f:0002)
        # and makes this
        #  1-11
        device_lines = r'^ +\d+-[0-9.]+: '
        available = [line[:line.find(':')].replace(' ', '')
                     for line in output.splitlines()
                     if re.match(device_lines, line)]

        return self.config['bus_id'] in available

    def get_online_state(self) -> bool:
        return self.get_share_state()

    def start_sharing(self) -> None:
        command = f"sudo usbip bind -b {self.config['bus_id']}"
        self.ssh(command)

    def stop_sharing(self) -> None:
        command = f"sudo usbip unbind -b {self.config['bus_id']}"
        self.ssh(command)

    # This Driver does not support authentication
    # def password_string(self):
    # def check_password(self, password: bytes) -> bool:
