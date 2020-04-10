from typing import NamedTuple, Union


class CommandResponse(NamedTuple):
    return_code: Union[int, str]
    stdout: str
    stderr: str
