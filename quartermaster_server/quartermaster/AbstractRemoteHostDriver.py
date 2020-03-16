import logging

from typing import TYPE_CHECKING, List, , Literal, Dict

from quartermaster.AbstractShareableDevice import AbstractShareableDevice

if TYPE_CHECKING:
    from data.models import Device, RemoteHost

logger = logging.getLogger(__name__)


class AbstractRemoteHostDriver(object):
    """
    This is closely related to the AbstractShareableDeviceDriver. Where as that focuses on acting on a single device
    this class is aimed at managing groupings of devices. This allows for more efficient network interactions as
    some operations such as getting status, can be performed on many devices at once.
    """

    DEVICE_CLASS: AbstractShareableDevice


    ONLINE_STATE_TYPE = Literal['Online', 'Offline', 'Missing', 'Unknown']
    SHARE_STATE_TYPE = Literal['Shared', 'Unshared', 'NA', 'Unknown']

    def __init__(self, host: 'RemoteHost'):
        self.host = host

    def devices(self) -> List['Device']:
        self.host.device_set.filter(driver=self.DEVICE_CLASS.__name__)

    def online_statuses(self) -> List[Dict['Device', ONLINE_STATE_TYPE]]:

        for device in self.devices():
            device.

        logger.info(f"Checking is {self} is online")
        state = self.get_online_state()
        logger.info(f"{self} is online={state}")
        return state

    def update_statuses(self):
        
    def share_statuses(self) -> List[Dict['Device', SHARE_STATE_TYPE]]:
        logger.info(f"Get share stat of {self}")
        state = self.get_share_state()
        logger.info(f"{self} shared={state}")
        return state

    def __str__(self):
        return f"RemoteHostDriver - {self.device}"
