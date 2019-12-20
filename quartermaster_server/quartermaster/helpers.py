# TODO: Cache connections
import logging
from typing import Tuple, Iterable, TYPE_CHECKING

import paramiko

from .AbstractShareableUsbDevice import AbstractShareableUsbDevice

if TYPE_CHECKING:
    from data.models import Device
from quartermaster import settings

logger = logging.getLogger(__name__)


def ssh_command(command: str, host: str) -> Tuple:
    try:
        client = paramiko.SSHClient()
        # TODO: This is not great, perhaps record host keys in DB?
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        client.connect(host, username=settings.SSH_USERNAME, pkey=settings.SSH_PRIVATE_KEY)
        stdin, stdout, stderr = client.exec_command(command=command)
    except paramiko.SSHException as e:
        logger.exception(f'Error: host={host}, command={command}')
        raise e
    return_code = stdout.channel.recv_exit_status()
    return return_code, stdout, stderr


def for_all_devices(devices: Iterable['Device'], method: str):
    for device in devices:
        driver = device.get_driver()
        getattr(driver, method)()


def get_driver(device: 'Device'):
    for driver_impl in AbstractShareableUsbDevice.__subclasses__():
        if device.driver == driver_impl.__name__:
            return driver_impl(device)
    raise NotImplementedError(f"Driver for {device} is '{device.driver}' but was not found")
