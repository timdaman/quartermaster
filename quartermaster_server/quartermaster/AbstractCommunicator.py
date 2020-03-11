import json
from typing import Union, NamedTuple, List


class CommandResponse(NamedTuple):
    return_code: Union[int, str]
    stdout: str
    stderr: str


class AbstractCommunicator(object):
    # Override this in subclasses or replace validate_configuration()
    CONFIGURATION_KEYS: List[str] = None

    def __init__(self, host: 'RemoteHost'):
        self.host = host
        # strict=False is there to allow use of \n in json values
        self.config = json.loads(host.config_json, strict=False)

    def execute_command(self, command: str) -> CommandResponse:
        raise NotImplemented

    def is_host_reachable(self) -> bool:
        raise NotImplemented
