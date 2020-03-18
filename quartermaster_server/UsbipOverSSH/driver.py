import logging
from typing import Dict, NamedTuple, Set, Optional, Iterable

import paramiko
from django.conf import settings

from quartermaster.AbstractRemoteHostDriver import AbstractRemoteHostDriver
from quartermaster.AbstractShareableDeviceDriver import AbstractShareableDeviceDriver

logger = logging.getLogger(__name__)


class DeviceDetails(NamedTuple):
    bus_id: str
    idVendor: str
    idProduct: str
    vendor: str
    product: str


class UsbipOverSSHHost(AbstractRemoteHostDriver):
    NO_REMOTE_DEVICES = 'usbip: info: no exportable devices found on '
    USBIPD_NOT_RUNNING = 'error: could not connect to localhost:3240'
    MISSING_KERNEL_MODULE = 'error: unable to bind device on '
    USBIP_DRIVER_PATH = '/sys/bus/usb/drivers/usbip-host'

    SUPPORTED_COMMUNICATORS = ('SSH',)

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
        command = "ls -1 /sys/bus/usb/drivers/usbip-host/"
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


class UsbipOverSSH(AbstractShareableDeviceDriver):
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

    # This Driver does not support authentication
    # def password_string(self):
    # def check_password(self, password: bytes) -> bool:


################################################################################
#
# This is being done to prevent circular dependencies
UsbipOverSSH.HOST_CLASS = UsbipOverSSHHost
UsbipOverSSHHost.DEVICE_CLASS = UsbipOverSSH
