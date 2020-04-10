import json
from typing import List

from .Exceptions import USB_Quartermaster_Exception
from .util import CommandResponse


class CommunicatorError(USB_Quartermaster_Exception):
    pass


class AbstractCommunicator(object):
    """
    This is the base class that defines how plugins communicate remotes hosts.
    If you want to support some other communication protocol subclass this and implement it's commands.

    This base class is structured around the concept all of the activities can be accomplished vis command line
    interface on the remote host.
    """

    # Override these in subclasses or replace validate_configuration()
    CONFIGURATION_KEYS: List[str] = None
    SUPPORTED_HOST_TYPES: List[str] = None
    IDENTIFIER: str
    
    def __init__(self, host: 'RemoteHost'):
        self.host = host
        # strict=False is there to allow use of \n in json values
        self.config = json.loads(host.config_json, strict=False)

    def execute_command(self, command: str) -> CommandResponse:
        raise NotImplemented

    def is_host_reachable(self) -> bool:
        raise NotImplemented
