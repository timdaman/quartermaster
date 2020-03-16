import logging

from typing import TYPE_CHECKING, List, Optional, Union

if TYPE_CHECKING:
    from data.models import Device

logger = logging.getLogger(__name__)


class AbstractShareableDevice(object):
    # Override this in subclasses or replace validate_configuration()
    CONFIGURATION_KEYS: List[str] = None

    COMPATIBLE_COMMUNICATORS: List[str] = None

    class DeviceError(Exception):
        """
        Generic error when trying to interact with device
        """

        def __init__(self, message: str = None):
            self.message = message

    class DeviceConnectionError(DeviceError):
        """
        Error related to setting up connection to remote host that hosts device
        """
        pass

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

    def __init__(self, device: 'Device'):
        self.device = device
        
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
