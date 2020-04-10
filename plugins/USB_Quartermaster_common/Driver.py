import logging
from typing import TYPE_CHECKING, List, Dict, Type, Iterable, Any, Tuple, NoReturn, Optional, Union

from .Communicator import AbstractCommunicator
from .Exceptions import USB_Quartermaster_Exception
from .util import CommandResponse

if TYPE_CHECKING:
    from data.models import Device, RemoteHost

logger = logging.getLogger(__name__)


class AbstractRemoteHostDriver(object):
    """
    This code runs on the quartermaster server
    
    This is closely related to the AbstractShareableDeviceDriver. Where as that focuses on acting on a single device
    this class is aimed at managing groupings of devices on a single host. This allows for more efficient network
    interactions as some operations such as getting status, can be performed on many devices at once on a host.
    """

    DEVICE_CLASS: Type['AbstractShareableDeviceDriver']

    SUPPORTED_COMMUNICATORS: Tuple[str]
    SUPPORTED_HOST_TYPES: Tuple[str]
    IDENTIFIER: str

    class HostError(USB_Quartermaster_Exception):
        """
        Generic error when trying to interact with device
        """

        def __init__(self, message: str = None):
            self.message = message

    class HostConnectionError(HostError):
        """
        Error related to setting up connection to remote host that hosts device
        """
        pass

    class HostCommandError(HostError):
        """
        This error indicates a problem trying configure device on remote host
        """
        pass

    def __init__(self, host: 'RemoteHost'):
        self.host = host
        self.communicator: AbstractCommunicator = host.get_communicator_obj()

    @property
    def address(self):
        return self.host.address

    @property
    def is_reachable(self) -> bool:
        return self.communicator.is_host_reachable()

    def devices(self) -> Iterable['Device']:
        return self.host.device_set.filter(driver=self.DEVICE_CLASS.__name__)

    def get_device_driver(self, device: 'Device') -> 'AbstractShareableDeviceDriver':
        return self.DEVICE_CLASS(device=device, host=self)

    def online_statuses(self) -> List[Dict['Device', Any]]:
        raise NotImplemented

    def update_statuses(self):
        raise NotImplemented

    def share_statuses(self) -> Dict[Any, Any]:
        raise NotImplemented

    def update_device_states(self, devices: Iterable['Device']) -> NoReturn:
        raise NotImplemented

    def __str__(self):
        return f"RemoteHostDriver - {self.host}"


class AbstractShareableDeviceDriver(object):
    """
    This code runs on the quartermaster server

    This is the service side code that allows to server to manages deveces to be shared on a remote host. This
    represents and handles a single device providing the interface that the server uses to find and control the state
    of devices on remote hosts.
    """

    # Override this in subclasses or replace validate_configuration()
    CONFIGURATION_KEYS: List[str] = None
    
    HOST_CLASS: Type['AbstractRemoteHostDriver']

    IDENTIFIER: str
    
    host_driver: 'AbstractRemoteHostDriver' = None

    class DeviceError(Exception):
        """
        Generic error when trying to interact with device
        """

        def __init__(self, message: str = None):
            self.message = message

    class DeviceNotFound(DeviceError):
        """
        This error indicates the target device was not found on the remote host
        """
        pass

    class DeviceCommandError(DeviceError):
        """
        This error indicates a problem trying configure device on remote host
        """
        pass

    def __init__(self, device: 'Device', host: Optional['AbstractRemoteHostDriver'] = None):
        self.device = device
        if host:
            self.host_driver = host
        else:
            self.host_driver = self.HOST_CLASS(host=device.host)

    def is_online(self) -> bool:
        logger.info(f"Checking is {self} is online")
        state = self.get_online_state()
        logger.info(f"{self} is online={state}")
        return state

    def is_shared(self) -> bool:
        logger.info(f"Get share stat of {self}")
        state = self.get_share_state()
        logger.info(f"{self} shared={state}")
        return state

    def share(self, **kwargs) -> None:
        if not self.is_shared():
            logger.info(f"Sharing {self}")
            self.start_sharing(**kwargs)

    def unshare(self) -> None:
        if self.is_shared():
            logger.info(f"Un-sharing {self.device}")
            self.stop_sharing()

    def refresh(self, **_) -> None:
        """Renew shares if they have been lost for some reason"""
        self.start_sharing()

    def start_sharing(self, **kwargs) -> None:
        raise NotImplemented

    def stop_sharing(self) -> None:
        raise NotImplemented

    def get_share_state(self) -> bool:
        raise NotImplemented

    def get_online_state(self) -> bool:
        raise NotImplementedError

    def validate_configuration(self) -> List[str]:
        errors_found = []
        for key in self.device.config.keys():
            if key not in self.CONFIGURATION_KEYS:
                errors_found.append(f"Unsupported attribute, '{key}'")
        for key in self.CONFIGURATION_KEYS:
            if key not in self.device.config:
                errors_found.append(f"Value for '{key}' is needed")
        return errors_found

    def password_string(self) -> Optional[str]:
        """Return the password needed for accessing this device. If None no password is needed"""
        raise NotImplemented

    def check_password(self, password: bytes) -> bool:
        """Returns true when "password" matches the expected value from the driver + resource"""
        raise NotImplemented

    def __str__(self):
        return f"ShareableUsbDevice - {self.device}"


class AbstractLocalDriver(object):
    """
    This code runs on the client machine

    This is the interfaced used to attach, manage, and detach devices form the client computer. It adds support for a
    USB sharing technology to the quartermaster_client command.
    """
    
    IDENTIFIER: str

    class DriverError(USB_Quartermaster_Exception):
        pass

    class CommandNotFound(DriverError):
        pass

    class CommandError(DriverError):

        def __init__(self, message: str,
                     response: CommandResponse,
                     command: Optional[Union[List[str], str]] = None):
            self.message = message
            self.response = response
            self.command = command

    class UnsupportedPlatform(DriverError):
        pass

    async def async_init(self):
        pass

    async def connect(self):
        raise NotImplementedError

    async def disconnect(self):
        raise NotImplementedError

    async def connected(self) -> bool:
        raise NotImplementedError

    def preflight_check(self):
        pass

    def setup_information(self) -> str:
        raise NotImplementedError
