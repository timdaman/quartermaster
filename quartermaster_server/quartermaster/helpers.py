# TODO: Cache connections
import logging
from typing import Iterable, TYPE_CHECKING

from quartermaster.AbstractShareableUsbDevice import AbstractShareableUsbDevice

if TYPE_CHECKING:
    from data.models import Device

logger = logging.getLogger(__name__)


def for_all_devices(devices: Iterable['Device'], method: str):
    for device in devices:
        driver = device.get_driver()
        getattr(driver, method)()


def get_driver_obj(device: 'Device'):
    for driver_impl in AbstractShareableUsbDevice.__subclasses__():
        if device.driver == driver_impl.__name__:
            return driver_impl(device)
    raise NotImplementedError(f"Driver for {device} is '{device.driver}' but was not found")
