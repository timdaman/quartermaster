import asyncio
import logging
import platform
import shutil
from typing import Dict, NamedTuple, Set, Optional, Iterable, List

import paramiko
from django.conf import settings

from USB_Quartermaster_common import AbstractRemoteHostDriver, AbstractShareableDeviceDriver, AbstractLocalDriver, \
    CommandResponse

logger = logging.getLogger(__name__)


class DeviceDetails(NamedTuple):
    bus_id: str
    idVendor: str
    idProduct: str
    vendor: str
    product: str

class DriverMetaData(object):
    SUPPORTED_COMMUNICATORS = ('SSH',)
    SUPPORTED_HOST_TYPES = ('Linux_AMD64',)
    IDENTIFIER = "USBIP"

class UsbipOverSSHHost(AbstractRemoteHostDriver, DriverMetaData):
    NO_REMOTE_DEVICES = 'usbip: info: no exportable devices found on '
    USBIPD_NOT_RUNNING = 'error: could not connect to localhost:3240'
    MISSING_KERNEL_MODULE = 'error: unable to bind device on '
    USBIP_DRIVER_PATH = '/sys/bus/usb/plugins/usbip-host'



    def __init__(self, host: 'RemoteHost'):
        super().__init__(host=host)

    def execute_command(self, command: str):
        try:
            response = self.communicator.execute_command(command=command)
        except paramiko.SSHException as e:
            raise self.HostConnectionError(
                f"Ran into problems connecting to {settings.SSH_USERNAME}@{self.host.address}: {e}")
        if response.return_code != 0:
            if self.USBIPD_NOT_RUNNING in response.stderr:
                message = f"usbipd is not running on {self.host}"
                logger.error(message)
                raise self.HostCommandError(message)
            elif self.MISSING_KERNEL_MODULE in response.stderr:
                message = f"Kernel modules might not be loaded on {self.host}, try `sudo modprobe usbip_host`"
                logger.error(message)
                raise self.HostCommandError(message)

            message = f'Error: host={self.host}, command={command}, rc={response.return_code}, ' \
                      f'stdout={response.stdout}, stderr={response.stderr}'
            logger.error(message)
            raise self.HostCommandError(message)
        return response

    def get_device_list(self) -> Dict[str, DeviceDetails]:
        """
        This process output that look like this or else blank if there are no devices

         - busid 1-1 (0403:6015)
           Future Technology Devices International, Ltd : Bridge(I2C/SPI/UART/FIFO) (0403:6015)

         - busid 1-2 (05c6:901d)
           Qualcomm, Inc. : unknown product (05c6:901d)

        :return: Dict containing all the IDs and there string
        """

        command = "usbip list -l"
        response = self.execute_command(command)
        device_lines = response.stdout.split(" - ")
        devices = {}
        for line in device_lines[1:]:  # We skip the first line since it is always empty due to the leading separator
            bus_id = line.split(' ')[1]
            idVendor, idProduct = line.split(' ')[2].strip('()\n').split(':')
            vendor, product = line.splitlines()[1].lstrip().split(' : ')
            product = product[:-12]  # Strip the id information
            devices[bus_id] = DeviceDetails(bus_id=bus_id,
                                            idVendor=idVendor,
                                            idProduct=idProduct,
                                            vendor=vendor,
                                            product=product)
        return devices

    def get_shared_bus_ids(self) -> Set[str]:
        command = "ls -1 /sys/bus/usb/plugins/usbip-host/"
        response = self.execute_command(command)
        shared = set()
        # Look for bus_ids
        for line in response.stdout.splitlines(keepends=False):
            if line[0].isdigit():
                shared.add(line)
        return shared

    def update_device_states(self, devices: Iterable['Device']):
        shared = self.get_shared_bus_ids()
        remote_devices = self.get_device_list()
        for device in devices:
            actual_shared = device.config['bus_id'] in shared
            actual_online = device.config['bus_id'] in remote_devices

            if device.in_use and not actual_shared:
                device_driver = self.get_device_driver(device)
                device_driver.share()
            elif not device.in_use and actual_shared:
                device_driver = self.get_device_driver(device)
                device_driver.unshare()

            if device.online != actual_online:
                device.online = actual_online
                device.save()


class UsbipOverSSH(AbstractShareableDeviceDriver, DriverMetaData):
    CONFIGURATION_KEYS = ('bus_id',)

    def __init__(self, device: 'Device', host: Optional[UsbipOverSSHHost] = None):
        super().__init__(device=device, host=host)

    @property
    def host(self):
        return self.device.host

    def execute_command(self, command: str):
        return self.host_driver.execute_command(command)

    def get_share_state(self) -> bool:
        return self.device.config['bus_id'] in self.host_driver.get_shared_bus_ids()

    def get_online_state(self) -> bool:
        devices = self.host_driver.get_device_list()
        return self.device.config['bus_id'] in devices

    def start_sharing(self) -> None:
        if not self.get_share_state():
            command = f"sudo usbip bind -b {self.device.config['bus_id']}"
            self.execute_command(command)

    def stop_sharing(self) -> None:
        if self.get_share_state():
            command = f"sudo usbip unbind -b {self.device.config['bus_id']}"
            self.execute_command(command)

    # This Driver.py does not support authentication
    # def password_string(self):
    # def check_password(self, password: bytes) -> bool:


################################################################################
#
# This is being done to prevent circular dependencies
UsbipOverSSH.HOST_CLASS = UsbipOverSSHHost
UsbipOverSSHHost.DEVICE_CLASS = UsbipOverSSH


class UsbipLocal(AbstractLocalDriver, DriverMetaData):
    # FIXME: Look for the following in output and flash as unbound device
    REMOTE_DEVICE_MISSING = b'usbip: error: recv op_common\nusbip: error: query'

    # FIXME: Probably should run `usbip list -r` before trying to attach so I can handle missing devices better

    def __init__(self, conf):
        self.conf = conf
        self.usbip = shutil.which('usbip')

    def preflight_check(self):
        if platform.system().lower() != 'linux':
            raise self.UnsupportedPlatform("Unsupported OS, 'usbip' is only available on Linux")
        self.usbip = shutil.which('usbip')
        if self.usbip is None:
            raise self.CommandNotFound(f"usbip was not found in PATH. {self.setup_information()}")

    async def run_usbip(self, arguments: List[str]):
        command = ['sudo', self.usbip, *arguments]
        command_str = " ".join(command)
        logger.debug(command_str)
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        stdout_bytes, stderr_bytes = await proc.communicate()
        stdout = stdout_bytes.decode('ascii')
        stderr = stderr_bytes.decode('ascii')

        if proc.returncode != 0:
            response = CommandResponse(return_code=proc.returncode, stdout=stdout, stderr=stderr)
            raise self.CommandError(
                f'Error: command={command_str}, rc={proc.returncode}, stdout={stdout}, stderr={stderr}',
                response=response, command=arguments
            )

        return stdout

    async def connected(self) -> bool:
        port = await self.get_port()
        return port is not None

    async def connect(self) -> None:
        args = ['attach', '-r', self.conf['host_address'], '-b', self.conf['bus_id']]
        try:
            await self.run_usbip(args)
        except self.CommandError as e:
            print(f"Error attaching {self.conf['host_address']} {self.conf['bus_id']}, "
                  f"rc={e.rc}, stdout={e.stdout}, stderr={e.stderr}")
            raise e

    async def get_port(self) -> Optional[int]:
        """# usbip port
                Imported USB devices
                ====================
                Port 00: <Port in Use> at Low Speed(1.5Mbps)
                       unknown vendor : unknown product (1c4f:0002)
                       2-1 -> usbip://10.3.40.43:3240/1-11
                           -> remote bus/dev 001/008"""
        args = ['port']
        output = await self.run_usbip(args)
        header = True
        ports = output.split('\nPort ')[1:]  # Skip the first group which is just the header
        logger.debug(ports)
        for port_option in ports:
            if f"/{self.conf['bus_id']}\n" in port_option:  # FIXME: This should try to match host too
                port = port_option.split(':')[0]
                logger.debug(f"Found {self.conf['bus_id']} on port {port}")
                return int(port)
        else:
            return None

    async def disconnect(self) -> None:

        port = await self.get_port()
        if port:
            args = ['detach', '-p', port]
            await self.run_usbip(args)
        else:
            print(f"Could not find port for bus_id '{self.conf['bus_id']}', maybe device is already "
                  f"disconnected")

    def setup_information(self):
        return """Linux is the only supported platform for USBIP. To use these devices on a Debian/Ubuntu based host 
                  you need to do the following setup once

                   # As root
                   apt-get install linux-tools-generic
                   modprobe vhci-hcd
                   echo 'vhci-hcd' >> /etc/modules # To load the 'vhci-hcd' module on boot in the future"""
