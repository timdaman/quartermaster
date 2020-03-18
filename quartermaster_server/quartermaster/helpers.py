import logging
from typing import Iterable, TYPE_CHECKING

from quartermaster.AbstractCommunicator import AbstractCommunicator
from quartermaster.AbstractShareableDeviceDriver import AbstractShareableDeviceDriver

if TYPE_CHECKING:
    from data.models import Device, RemoteHost

logger = logging.getLogger(__name__)


def for_all_devices(devices: Iterable['Device'], method: str):
    for device in devices:
        driver = device.get_driver()
        getattr(driver, method)()


def get_driver_obj(device: 'Device') -> AbstractShareableDeviceDriver:
    for driver_impl in AbstractShareableDeviceDriver.__subclasses__():
        if device.driver == driver_impl.__name__:
            return driver_impl(device)
    raise NotImplementedError(f"Driver for {device} is '{device.driver}' but was not found")


def get_commincator_obj(remote_host: 'RemoteHost'):
    for communicator_impl in AbstractCommunicator.__subclasses__():
        if remote_host.communicator == communicator_impl.__name__:
            return communicator_impl(remote_host)
    raise NotImplementedError(f"Communicator for {remote_host} is '{remote_host.communicator}' but was not found")
