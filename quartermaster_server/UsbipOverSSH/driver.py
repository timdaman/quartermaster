import logging

import paramiko
from django.conf import settings

from quartermaster.AbstractShareableDevice import AbstractShareableDevice

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


class UsbipOverSSH(AbstractShareableDevice):
    NO_REMOTE_DEVICES = 'usbip: info: no exportable devices found on '
    CONFIGURATION_KEYS = ('bus_id',)
    USBIPD_NOT_RUNNING = 'error: could not connect to localhost:3240'
    MISSING_KERNEL_MODULE = 'error: unable to bind device on '
    USBIP_DRIVER_PATH = '/sys/bus/usb/drivers/usbip-host'

    COMPATIBLE_COMMUNICATORS = ('SSH',)

    def __init__(self, device: 'Device'):
        super().__init__(device=device)
        self.communicator = self.device.host.get_communicator_obj()

    @property
    def host(self):
        return self.device.host

    def ssh(self, command: str):
        try:
            return_code, stdout, stderr = self.communicator.execute_command(command=command)
        except paramiko.SSHException as e:
            raise self.DeviceConnectionError(
                f"Ran into problems connecting to {settings.SSH_USERNAME}@{self.host.address}: {e}")
        if return_code != 0:
            if self.USBIPD_NOT_RUNNING in stderr:
                message = f"usbipd is not running on {self.host}"
                logger.error(message)
                raise self.DeviceCommandError(message)
            elif self.MISSING_KERNEL_MODULE in stderr:
                message = f"Kernel modules might not be loaded on {self.host}, try `sudo modprobe usbip_host`"
                logger.error(message)
                raise self.DeviceCommandError(message)

            message = f'Error: host={self.host}, command={command}, rc={return_code}, ' \
                      f'stdout={stdout}, stderr={stderr}'
            logger.error(message)
            raise self.DeviceCommandError(message)
        return return_code, stdout, stderr

    def execute_command(self, command: str):
        if self.communicator.__class__.__name__ == 'SSH':
            return self.ssh(command)

    def get_share_state(self) -> bool:
        command = f"test -d /sys/bus/usb/drivers/usbip-host/{self.device.config['bus_id']} || echo  missing"
        return_code, stdout, stderr = self.execute_command(command)

        if return_code != 0 and self.NO_REMOTE_DEVICES not in stderr:
            message = f'Error: host={self.host}, command={command}, rc={return_code}, ' \
                      f'stdout={stdout}, stderr={stderr}'
            logger.error(message)
            raise self.DeviceCommandError(message)

        return 'missing' not in stdout

    def get_online_state(self) -> bool:
        command = "usbip list -l"
        return_code, stdout, stderr = self.execute_command(command)

        if return_code != 0:
            message = f'Error: host={self.host}, command={command}, rc={return_code}, ' \
                      f'stdout={stdout}, stderr={stderr}'
            logger.error(message)
            raise self.DeviceCommandError(message)

        return f"- busid {self.device.config['bus_id']} " in stdout

    def start_sharing(self) -> None:
        if not self.get_share_state():
            command = f"sudo usbip bind -b {self.device.config['bus_id']}"
            self.execute_command(command)

    def stop_sharing(self) -> None:
        if self.get_share_state():
            command = f"sudo usbip unbind -b {self.device.config['bus_id']}"
            self.execute_command(command)

    # This Driver does not support authentication
    # def password_string(self):
    # def check_password(self, password: bytes) -> bool:
