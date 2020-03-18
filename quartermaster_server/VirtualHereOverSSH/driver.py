import logging
import re
from typing import Optional, NamedTuple, Dict, List, Iterable
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

from quartermaster.AbstractCommunicator import CommandResponse
from quartermaster.AbstractRemoteHostDriver import AbstractRemoteHostDriver
from quartermaster.AbstractShareableDeviceDriver import AbstractShareableDeviceDriver

logger = logging.getLogger(__name__)


class DeviceInfo(NamedTuple):
    address: str
    nickname: str
    online: bool
    shared: bool


class VirtualHereOverSSHHost(AbstractRemoteHostDriver):
    SUPPORTED_COMMUNICATORS = ('SSH',)

    class VirtualHereDriverError(AbstractShareableDeviceDriver.DeviceCommandError):
        pass

    class VirtualHereExecutionError(VirtualHereDriverError):
        pass

    # FIXME: Update to probe remote endpoint and detect client automatically
    # FIXME: or allow the client to be part of the config obj
    @property
    def vh_client_cmd(self):
        return "vhclientx86_64"

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
        try:
            full_command = [self.vh_client_cmd, '-t', f"'{command}'"]
            response = self.ssh(" ".join(full_command))
            return response
        except self.HostCommandError as e:
            if self.client_service_not_running(e.message):
                raise self.VirtualHereExecutionError(
                    f"VirtualHere client service is needed but does not appear to be running on {self.host.address}")
            else:
                raise e

    def get_states(self) -> Dict[str, DeviceInfo]:
        response = self.vh_command('GET CLIENT STATE')
        tree: Element = ElementTree.fromstring(response.stdout)
        connection: Element
        for connection in tree.iter('connection'):
            if connection.attrib['ip'] == '127.0.0.1':
                hostname = connection.attrib['hostname']
                break
        else:
            raise Exception(f"Could not find device on local machine, is this a server? {self.host}")
        devices = {}
        device: Element
        for device in tree.iter('device'):
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


class VirtualHereOverSSH(AbstractShareableDeviceDriver):
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
        # FIXME: Make this true
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
