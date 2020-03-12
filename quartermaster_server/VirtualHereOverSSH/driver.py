import logging
import re
from typing import Optional, Tuple

from quartermaster.AbstractShareableUsbDevice import AbstractShareableUsbDevice

logger = logging.getLogger(__name__)

"""
The schema for the Device `config` file is the following

{
"hub_address": "<HOSTNAME OR IP ADDRESS OF SERVER WITH DEVICE>",
"device_address": "<value surrounded by '()' returned by `vhclient* -t list`>"
}

and example is this

{
"hub_address": "remote_host.example.com",
"device_address": "remote_host-1.17"
}
"""


class VirtualHereOverSSH(AbstractShareableUsbDevice):
    USER_MATCHER = re.compile("^IN USE BY: (?P<user>.+)$", flags=re.MULTILINE)
    OK_MATCHER = re.compile("^OK$", flags=re.MULTILINE)
    NICKNAME_MATCHER = re.compile("^NICKNAME: (?P<nickname>.+)$", flags=re.MULTILINE)
    CONFIGURATION_KEYS = ("device_address",)
    CMD_TIMEOUT_SEC = 10
    COMPATIBLE_COMMUNICATORS = ('SSH',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.communicator = self.device.host.get_communicator_obj()

    class VirtualHereDriverError(AbstractShareableUsbDevice.DeviceCommandError):
        pass

    class VirtualHereExecutionError(VirtualHereDriverError):
        pass

    @property
    def hub_address(self):
        return self.device.config['hub_address']

    # FIXME: Update to probe remote endpoint and detect client automatically
    # FIXME: or allow the client to be part of the config obj
    @property
    def vh_client_cmd(self):
        return "vhclientx86_64"

    def ssh(self, command: str) -> Tuple[int, str, str]:
        full_command = f"{self.vh_client_cmd} -t '{command}'"
        return_code, stdout, stderr = self.communicator.execute_command(command=command)
        if return_code != 0:
            message = f'Error: host={self.device.host}, command={command}, rc={return_code}, ' \
                      f'stdout={stdout}, stderr={stderr}'
            logger.error(message)
            raise self.DeviceCommandError(message)
        return return_code, stdout, stderr

    def execute_command(self, command: str):
        if self.communicator.__class__.__name__ == 'SSH':
            return self.ssh(command)

    def client_service_not_running(self, output: str) -> bool:
        for error in (
                'IPC client, server response open failed', 'An existing client is not running.',
                'No response from IPC server'):
            if error in output:
                return True
        return False

    def vh_command(self, *args) -> Tuple[str, str]:
        try:
            return_code, stdout, stderr = self.ssh(" ".join(args))
            # Throw away return code, we know it is zero because no exception was raised
            return stdout, stderr
        except self.DeviceCommandError as e:
            if self.client_service_not_running(e.message):
                raise self.VirtualHereExecutionError(
                    f"VirtualHere client service is needed but does not appear to be running on {self.hub_address}")
            else:
                raise e

    def get_share_state(self) -> bool:
        stdout, stderr = self.vh_command(f"DEVICE INFO,{self.device.config['device_address']}")
        match = self.USER_MATCHER.search(stdout)
        if match and match.group('user') == 'NO ONE':
            return False
        else:
            return True

    def get_online_state(self) -> bool:
        # Confirm device is online
        device_output = self.vh_command(f"DEVICE INFO,{self.device.config['device_address']}")
        if 'ADDRESS: ' in device_output:
            return True
        return False

    def get_nickname(self) -> Optional[str]:
        output = self.vh_command(f"DEVICE INFO,{self.device.config['device_address']}")
        match = self.NICKNAME_MATCHER.search(output)
        if match:
            return match.group('nickname')
        return None

    def set_nickname(self) -> None:
        self.vh_command(f"DEVICE RENAME,{self.device.config['device_address']},{self.device.name}")

    def start_sharing(self) -> None:
        # FIXME: Make this true
        # shares are always available and are controlled by knowing the password
        pass

    def stop_sharing(self) -> None:
        self.vh_command(f"STOP USING,{self.device.config['device_address']}")
