from typing import Optional, Union, List


class LocalDriver(object):
    class DriverError(Exception):
        pass

    class CommandNotFound(DriverError):
        pass

    class CommandError(DriverError):

        def __init__(self, message: str,
                     rc: Optional[int] = None,
                     stdout: bytes = b'',
                     stderr: bytes = b'',
                     command: Optional[Union[List[str], str]] = None):
            self.message = message
            self.rc = rc
            self.stdout = stdout
            self.stderr = stderr
            self.command = command

    class UnsupportedPlatform(DriverError):
        pass

    async def async_init(self):
        pass

    async def connect(self):
        raise NotImplementedError

    async def disconnect(self):
        raise NotImplementedError

    async def connected(self) -> bool:
        raise NotImplementedError

    def preflight_check(self):
        pass

    def setup_information(self) -> str:
        raise NotImplementedError
