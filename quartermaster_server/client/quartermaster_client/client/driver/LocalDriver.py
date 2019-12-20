class LocalDriver(object):
    class DriverError(Exception):
        pass

    class CommandNotFound(DriverError):
        pass

    class CommandError(DriverError):
        pass

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
