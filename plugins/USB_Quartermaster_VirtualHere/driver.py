import asyncio
import logging
import platform
import re
import shutil
import subprocess
import time
from typing import Optional, NamedTuple, Dict, Iterable, List
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

from USB_Quartermaster_common import AbstractRemoteHostDriver, AbstractShareableDeviceDriver, CommandResponse, \
    AbstractLocalDriver

logger = logging.getLogger(__name__)


class DeviceInfo(NamedTuple):
    address: str
    nickname: str
    online: bool
    shared: bool


class DriverMetaData(object):
    SUPPORTED_COMMUNICATORS = {'SSH'}
    SUPPORTED_HOST_TYPES = {"Darwin", "Linux_AMD64", "Windows"}
    IDENTIFIER = "VirtualHere"


class VirtualHereOverSSHHost(AbstractRemoteHostDriver, DriverMetaData):
    class VirtualHereDriverError(AbstractShareableDeviceDriver.DeviceCommandError):
        pass

    class VirtualHereExecutionError(VirtualHereDriverError):
        pass

    @property
    def vh_client_cmd(self):
        if "virtualhere_command" in self.host.config:
            return self.host.config["virtualhere_command"]
        elif self.host.type == "Linux_AMD64":
            return "vhclientx86_64"
        elif self.host.type == "Windows":
            return "vhui64.exe"
        elif self.host.type == "Darwin":
            return "/Applications/VirtualHere.app/Contents/MacOS/VirtualHere"

    def ssh(self, command: str) -> CommandResponse:
        response = self.communicator.execute_command(command=command)
        if response.return_code != 0:
            message = f'Error: host={self.host.address}, command={command}, rc={response.return_code}, ' \
                      f'stdout={response.stdout}, stderr={response.stderr}'
            logger.error(message)
            raise self.HostCommandError(message)
        return response

    def client_service_not_running(self, output: str) -> bool:
        for error in (
                'IPC client, server response open failed', 'An existing client is not running.',
                'No response from IPC server'):
            if error in output:
                return True
        return False

    def vh_command(self, command) -> CommandResponse:
        if self.host.type == "Windows":
            # This forces the the command shell to wait for the executable to exit before exiting ensuring
            # we get the output from VirtualHere.
            full_command = f'start "quartermaster" /W {self.vh_client_cmd} -t "{command}" -r "quartermaster.tmp" ' \
                           f'& type quartermaster.tmp ' \
                           f'& del quartermaster.tmp'
        else:
            full_command = f'{self.vh_client_cmd} -t "{command}"'

        try:
            response = self.ssh(full_command)
            return response
        except self.HostCommandError as e:
            if self.client_service_not_running(e.message):
                raise self.VirtualHereExecutionError(
                    f"VirtualHere client service is needed but does not appear to be running on {self.host.address}")
            else:
                raise e

    def _find_localhost_hostname(self, tree: Element) -> Optional[str]:
        """
        Given the parsed `GET CLIENT STATE` output look for a connection to the localhost server (on the remote host)

        :param tree: ElementTree.Element
        :return: The name of the localhost server or None if not found
        """
        connection: Element
        for connection in tree.iter('connection'):
            if connection.attrib['ip'] == '127.0.0.1':
                return connection.attrib['hostname']
        return None

    def _get_state_data(self) -> Element:
        response = self.vh_command('GET CLIENT STATE')
        try:
            return ElementTree.fromstring(response.stdout)
        except ElementTree.ParseError as e:
            raise self.VirtualHereExecutionError(f"Error parsing VirtualHere client status, "
                                                 f"host={self.host.communicator}:{self.host.address} xml=>>{response.stdout}<< stderr=>>{response.stderr}<<")

    def get_states(self) -> Dict[str, DeviceInfo]:
        state_data = self._get_state_data()
        hostname = self._find_localhost_hostname(state_data)

        # Sometimes the client doesn't have the local hub registered. I have seen this on Windows.
        # This will, if a localhost hub is not found, add one and try one more time
        if hostname is None:
            response = self.vh_command('MANUAL HUB ADD,127.0.0.1')
            if response.stdout.startswith('OK'):
                state_data = self._get_state_data()
                hostname = self._find_localhost_hostname(state_data)
            else:
                raise self.VirtualHereExecutionError(
                    f"Error, {response}, when trying to add connection to local server, {self.host}.")

        if hostname is None:
            raise self.VirtualHereExecutionError(
                f"Could not find device on local machine, is this running the VirtualHere server? {self.host}")

        devices = {}
        device: Element
        for device in state_data.iter('device'):
            address = f"{hostname}.{device.attrib['address']}"
            shared: bool
            devices[address] = DeviceInfo(
                address=address,
                nickname=device.attrib['nickname'],
                online=True,  # If we see then it has to be online
                shared=device.attrib['state'] != "1"  # So far as I can tell, 1=Unused, 3=Used
            )
        return devices

    def update_device_states(self, devices: Iterable['Device']):
        states = self.get_states()
        for device in devices:
            try:
                state_info = states[device.config['device_address']]
            except KeyError:
                # If we don't see the device in the state info then it is offline
                device.online = False
                device.save()
                continue
            else:
                if not device.online:
                    device.online = True
                    device.save()

            # Devices are always shared, just disconnect users who don't have them reserved.
            if not device.in_use and state_info.shared:
                device_driver = self.get_device_driver(device)
                device_driver.unshare()


class VirtualHereOverSSH(AbstractShareableDeviceDriver, DriverMetaData):
    USER_MATCHER = re.compile("^IN USE BY: (?P<user>.+)$", flags=re.MULTILINE)
    OK_MATCHER = re.compile("^OK$", flags=re.MULTILINE)
    NICKNAME_MATCHER = re.compile("^NICKNAME: (?P<nickname>.+)$", flags=re.MULTILINE)
    CONFIGURATION_KEYS = ("device_address",)
    CMD_TIMEOUT_SEC = 10

    class VirtualHereDriverError(AbstractShareableDeviceDriver.DeviceCommandError):
        pass

    class VirtualHereExecutionError(VirtualHereDriverError):
        pass

    def get_share_state(self) -> bool:
        device_address = self.device.config['device_address']
        states: List[DeviceInfo] = self.host_driver.get_states()
        if device_address in states:
            return states[device_address].shared
        else:
            raise self.DeviceNotFound(f"Did not find {device_address} on {self.device.host}")

    def get_online_state(self) -> bool:
        device_address = self.device.config['device_address']
        states: List[DeviceInfo] = self.host_driver.get_states()
        return device_address in states

    def get_nickname(self) -> Optional[str]:
        device_address = self.device.config['device_address']
        states: List[DeviceInfo] = self.host_driver.get_states()
        if device_address in states:
            return states[device_address].nickname
        else:
            raise self.DeviceNotFound(f"Did not find {device_address} on {self.device.host}")

    def set_nickname(self) -> None:
        self.host_driver.vh_command(f"DEVICE RENAME,{self.device.config['device_address']},{self.device.name}")

    def start_sharing(self) -> None:
        # FIXME: Make this do something
        # shares are always available and are controlled by knowing the password if enabled
        pass

    def stop_sharing(self) -> None:
        states: Dict[str, DeviceInfo] = self.host_driver.get_states()
        if states[self.device.config['device_address']].shared:
            self.host_driver.vh_command(f"STOP USING,{self.device.config['device_address']}")


################################################################################
#
# This is being done to prevent circular dependencies
VirtualHereOverSSH.HOST_CLASS = VirtualHereOverSSHHost
VirtualHereOverSSHHost.DEVICE_CLASS = VirtualHereOverSSH


class VirtualHereLocal(AbstractLocalDriver, DriverMetaData):
    OK_MATCHER = re.compile("^OK$", flags=re.MULTILINE)
    LINUX_CLIENT_NAME = f"vhclient{platform.machine()}"

    vh: str

    def __init__(self, conf):
        self.conf = conf

    def preflight_check(self):
        # Confirm VirtualHere client is installed and running
        self.start_client_service()

    async def async_init(self):
        self.vh = self.find_vh()
        await self.attach_hub()

    def start_client_service(self):
        target_platform = platform.system().lower()
        if target_platform in ('darwin', 'mac', 'macos', 'macosx'):
            self.setup_mac_client()
        elif target_platform == 'linux':
            self.setup_linux_client()
        else:
            raise self.UnsupportedPlatform(f"Unsupported platform {target_platform}")

    @staticmethod
    def mac_find_vh() -> Optional[str]:
        try:
            app_name_fragment = 'VirtualHere.app/Contents/MacOS/VirtualHere'
            output = subprocess.check_output(('pgrep', '-lf', app_name_fragment),
                                             encoding='utf-8')
            # Find path in output, assume it looks like on the following
            # '18643 /Applications/VirtualHere.app/Contents/MacOS/VirtualHere'
            # '1598 /Applications/VirtualHere.app/Contents/MacOS/VirtualHere --log=OSEventLog -n'
            match = re.match(f"^\d+ (?P<cmd>.+{app_name_fragment})", output.splitlines()[0])
            return match['cmd']
        except subprocess.CalledProcessError:
            # Assume process is not running
            return None

    def linux_find_vh(self):
        return shutil.which(self.LINUX_CLIENT_NAME)

    def find_vh(self) -> str:
        target_platform = platform.system().lower()
        if target_platform in ('darwin', 'mac', 'macos', 'macosx'):
            return self.mac_find_vh()
        elif target_platform == 'linux':
            return self.linux_find_vh()
        else:
            raise self.UnsupportedPlatform(f"Unsupported platform {target_platform}")

    def setup_mac_client(self) -> List[str]:
        # check if client is running and get path
        vh_path = self.mac_find_vh()

        if not vh_path:
            # Assume process is not running
            try:
                print("Starting VirtualHere")
                subprocess.check_call(('open', '-ga', 'VirtualHere'))
                time.sleep(2)  # Give client service some time to start
            except subprocess.CalledProcessError:
                raise self.CommandError("Looks like VirtualHere might not be installed or runnable")
            vh_path = self.mac_find_vh()

        if vh_path is None:
            # Start if needed and get path
            try:
                print("Starting VirtualHere")
                subprocess.check_call(('open', '-ga', 'VirtualHere'))
                time.sleep(2)  # Give client service some time to start
            except subprocess.CalledProcessError:
                raise self.CommandError("Looks like VirtualHere might not be installed or runnable")
            vh_path = self.mac_find_vh()
        return [vh_path]

    def setup_linux_client(self):
        # Check for sudo
        sudo = shutil.which('sudo')
        if not sudo:
            raise self.CommandError("sudo is needed and was not found in path")

        # Check for client
        vhclient = self.linux_find_vh()
        if not vhclient:
            raise self.CommandError(
                f"{self.LINUX_CLIENT_NAME} is needed and was not found in path. {self.setup_information()}")

        # start client if needed
        try:
            subprocess.check_output(('pgrep', self.LINUX_CLIENT_NAME))
        except subprocess.CalledProcessError:
            # Assume client is not running if we get a non-zero
            print("Starting VirtualHere client service, if this failed you may need to start it "
                  f"manually by running `sudo {vhclient} -n`")
            subprocess.check_call(('sudo', vhclient, '-n'))  # TODO: Can I pass through stdin?
            time.sleep(2)  # Give client service some time to start

    async def run_vh(self, args):
        proc = await asyncio.create_subprocess_exec(
            self.vh, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT)
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            stdout_str = stdout.decode('ascii')
            stderr_str = ""
            raise self.CommandError(
                f'Error: command={self.vh} {args}, rc={proc.returncode}, stdout={stdout}, stderr={stderr}',
                CommandResponse(return_code=proc.returncode, stdout=stdout_str, stderr=stderr_str),
                [self.vh, *args]
            )

        return stdout.decode('ascii')

    async def attach_hub(self):
        args = ['-t', 'MANUAL HUB LIST']
        hub_list = await self.run_vh(args)
        for hub in hub_list.splitlines():
            if hub.startswith(self.conf['host_address']):  # Hub already connected
                break
        else:
            args = ['-t', f"MANUAL HUB ADD,{self.conf['host_address']}"]
            output = await self.run_vh(args)
            if not self.OK_MATCHER.search(output):
                raise self.CommandError(
                    f"VirtualHere did not return 'OK' when connecting hub '{self.conf['host_address']}', "
                    f"instead I got '{output}'"
                )

    async def connect(self):
        args = ['-t', f"USE,{self.conf['device_address']}"]
        output = await self.run_vh(args)
        if not self.OK_MATCHER.search(output):
            raise self.CommandError(f"VirtualHere did not return 'OK' when connecting device, instead I got '{output}'")

    async def disconnect(self):
        args = ['-t', f"STOP USING,{self.conf['device_address']}"]
        output = await self.run_vh(args)
        if not self.OK_MATCHER.search(output):
            raise self.CommandError(
                f"VirtualHere did not return 'OK' when disconnecting device, instead I got '{output}'")

    async def connected(self) -> bool:
        """
        # vhclientx86_64 -t 'device info,spf3-topaz-1.17'
        ADDRESS: spf3-topaz-1.17
        VENDOR: Android
        VENDOR ID: 0x05c6
        PRODUCT: Android
        PRODUCT ID: 0x901d
        SERIAL: 1f53203a
        NICKNAME: KonaFrames01
        IN USE BY: NO ONE
        """
        args = ['-t', f"DEVICE INFO,{self.conf['device_address']}"]
        output = await self.run_vh(args)
        return "IN USE BY: NO ONE" not in output

    def setup_information(self):
        return "To use these Virtual here resources you must have the VirtualHere client installed and running. " \
               "You can download the client at https://virtualhere.com/usb_client_software"
