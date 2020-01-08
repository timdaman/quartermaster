import logging
import os
import platform
import re
import shutil
import socket
import subprocess
from functools import lru_cache
from typing import Optional

from quartermaster.AbstractShareableUsbDevice import AbstractShareableUsbDevice

logger = logging.getLogger(__name__)

RETRIES = 2


def default_client_name(os_name: Optional[str] = None):
    if os_name:
        target_platform = os_name.lower()
    else:
        target_platform = platform.system().lower()

    if target_platform in ('darwin', 'mac', 'macos', 'macosx'):
        return '/Applications/VirtualHere.app/Contents/MacOS/VirtualHere'
    elif target_platform == 'linux':
        return f"vhclient{platform.machine()}"
    elif target_platform == 'windows':
        # Ugly hack, I just assume Windows is 64 bit
        return 'vhui64.exe'

    raise NotImplementedError(f"Don't know what binary to look for on platform '{target_platform}'")


@lru_cache()
def find_vhclient() -> str:
    user_supplied = os.environ.get('vh_client_path')
    if user_supplied is not None and os.path.exists(user_supplied):
        return user_supplied

    command_name_guess = default_client_name()
    path_guess = shutil.which(command_name_guess)
    if path_guess is not None:
        return path_guess
    else:
        raise SystemError("Could not find VirtualHere console client. Add client to search path or set "
                          "vh_client_path` in environment")


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


def lazy_initialize(func):
    def wrapper(self, *args, **kwargs):
        if not self.hub_attached:
            self.attach_hub()
        return func(self, *args, **kwargs)

    return wrapper


class VirtualHere(AbstractShareableUsbDevice):
    vhclient = find_vhclient()
    USER_MATCHER = re.compile("^IN USE BY: (?P<user>.+)$", flags=re.MULTILINE)
    OK_MATCHER = re.compile("^OK$", flags=re.MULTILINE)
    NICKNAME_MATCHER = re.compile("^NICKNAME: (?P<nickname>.+)$", flags=re.MULTILINE)
    CONFIGURATION_KEYS = ("hub_address", "device_address")
    CMD_TIMEOUT_SEC = 10

    hub_attached = False

    def __init__(self, *args, **kwargs):
        super(VirtualHere, self).__init__(*args, **kwargs)

    class VirtualHereDriverError(AbstractShareableUsbDevice.DeviceCommandError):
        pass

    class VirtualHereExecutionError(VirtualHereDriverError):
        pass

    def _vh_wrapper(self, *args):

        command = [self.vhclient, *args]
        output = 'NO OUTPUT AVAILABLE'

        try:
            output = subprocess.check_output(command, stderr=subprocess.STDOUT, timeout=self.CMD_TIMEOUT_SEC)
            return output.decode("ascii")
        except subprocess.CalledProcessError as e:
            raise self.VirtualHereExecutionError(f"Error when running {command}: {e}", e.output.decode('utf-8'))

    def client_service_not_running(self, output: str) -> bool:
        for error in (
                'IPC client, server response open failed', 'An existing client is not running.',
                'No response from IPC server'):
            if error in output:
                return True
        return False

    def vh_command(self, *args) -> str:
        exception = None
        for _ in range(0, RETRIES):
            try:
                return self._vh_wrapper('-t', *args)
            except self.VirtualHereExecutionError as e:
                # Don't bother retrying if the client service is not running
                if self.client_service_not_running(e.args[1]):
                    exception = self.VirtualHereExecutionError(
                        f"VirtualHere client service is needed but does not appear to be running")

                    break
                else:
                    exception = e
        raise exception

    def attach_hub(self):
        try:
            output = self.vh_command(f"MANUAL HUB ADD,{self.device.config['hub_address']}")
            if not self.OK_MATCHER.search(output):
                raise SystemError(f"VirtualHere did not return 'OK' when connecting hub, instead I got '{output}'")
        except subprocess.CalledProcessError as e:
            raise SystemError(f"Error attaching VirtualHere hub: {e}: {e.output}")

    @lazy_initialize
    def get_share_state(self) -> bool:
        output = self.vh_command(f"DEVICE INFO,{self.device.config['device_address']}")
        match = self.USER_MATCHER.search(output)
        if match and match.group('user') == 'NO ONE':
            return False
        else:
            return True

    @lazy_initialize
    def get_online_state(self) -> bool:

        def strip_port(x):
            return x.split(':')[0]

        # Confirm hub is online
        hub_ip = socket.gethostbyname(self.config['hub_address'])
        hub_ip = strip_port(hub_ip)
        #  list hubs
        hub_output = self.vh_command('MANUAL HUB LIST')
        #  compare address resolution to hub_address
        for line in hub_output.splitlines():
            candidate_address = strip_port(line)
            candidate_ip = socket.gethostbyname(candidate_address)
            if candidate_ip == hub_ip:
                break
        else:  # fail if no match
            return False

        # Confirm device is online
        device_output = self.vh_command(f"DEVICE INFO,{self.config['device_address']}")
        if 'ADDRESS: ' in device_output:
            return True
        return False

    @lazy_initialize
    def get_nickname(self) -> Optional[str]:
        output = self.vh_command(f"DEVICE INFO,{self.device.config['device_address']}")
        match = self.NICKNAME_MATCHER.search(output)
        if match:
            return match.group('nickname')
        return None

    @lazy_initialize
    def set_nickname(self) -> None:
        self.vh_command(f"DEVICE RENAME,{self.device.config['device_address']},{self.device.name}")

    def start_sharing(self) -> None:
        # shares are always available and are controlled by knowing the password
        pass

    @lazy_initialize
    def stop_sharing(self) -> None:
        self.vh_command(f"STOP USING,{self.device.config['device_address']}")
