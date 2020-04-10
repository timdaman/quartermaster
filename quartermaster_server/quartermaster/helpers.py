import logging
from typing import Iterable, TYPE_CHECKING, Optional, Type

import plugins
from USB_Quartermaster_common import AbstractShareableDeviceDriver, AbstractCommunicator

if TYPE_CHECKING:
    from data.models import Device, RemoteHost

logger = logging.getLogger(__name__)


def for_all_devices(devices: Iterable['Device'], method: str):
    for device in devices:
        driver = device.get_driver()
        getattr(driver, method)()


def get_driver_obj(device: 'Device') -> AbstractShareableDeviceDriver:
    driver_impl: Type[AbstractShareableDeviceDriver]
    for driver_impl in plugins.shareable_device_classes():
        if device.driver == driver_impl.IDENTIFIER:
            return driver_impl(device)
    raise NotImplementedError(f"Driver for {device} is '{device.driver}' but was not found")


def get_communicator_class(name: str) -> Optional[Type[AbstractCommunicator]]:
    communicator_impl: Type[AbstractCommunicator]
    for communicator_impl in plugins.communicator_classes():
        if name == communicator_impl.IDENTIFIER:
            return communicator_impl
        return None


def get_communicator_obj(remote_host: 'RemoteHost') -> AbstractCommunicator:
    communicator_class = get_communicator_class(remote_host.communicator)
    if communicator_class is None:
        raise NotImplementedError(f"Communicator for {remote_host} is '{remote_host.communicator}' but was not found")
    return communicator_class(remote_host)
