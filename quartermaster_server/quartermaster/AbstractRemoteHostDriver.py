import logging
from typing import TYPE_CHECKING, List, Dict, Type, Iterable, Any, Tuple, NoReturn

from quartermaster.AbstractCommunicator import AbstractCommunicator

if TYPE_CHECKING:
    from data.models import Device, RemoteHost

logger = logging.getLogger(__name__)


class AbstractRemoteHostDriver(object):
    """
    This is closely related to the AbstractShareableDeviceDriver. Where as that focuses on acting on a single device
    this class is aimed at managing groupings of devices. This allows for more efficient network interactions as
    some operations such as getting status, can be performed on many devices at once.
    """

    DEVICE_CLASS: Type['AbstractShareableDeviceDriver']

    SUPPORTED_COMMUNICATORS: Tuple[str] = None

    class HostError(Exception):
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
