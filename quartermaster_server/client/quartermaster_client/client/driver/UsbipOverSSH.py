import asyncio
import logging
import platform
import shutil
from typing import List, Optional

from .LocalDriver import LocalDriver

logger = logging.getLogger()


class UsbipOverSSH(LocalDriver):
    # FIXME: Look for the following in output and flash as unbound device
    REMOTE_DEVICE_MISSING = b'usbip: error: recv op_common\nusbip: error: query'
    # FIXME: Probably should run `usbip list -r` before trying to attach so I can handle missing devices better

    def __init__(self, conf):
        self.conf = conf
        self.usbip = shutil.which('usbip')

    def preflight_check(self):
        if platform.system().lower() != 'linux':
            raise self.UnsupportedPlatform("Unsupported OS, 'usbip' is only available on Linux")
        self.usbip = shutil.which('usbip')
        if self.usbip is None:
            raise self.CommandNotFound(f"usbip was not found in PATH. {self.setup_information()}")

    async def run_usbip(self, arguments: List[str]):
        command = ['sudo', self.usbip, *arguments]
        logger.debug(" ".join(command))
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise self.CommandError(
                f'Error: command={arguments}, rc={proc.returncode}, stdout={stdout}, stderr={stderr}',
                rc=proc.returncode, stdout=stdout, stderr=stderr, command=arguments
            )

        return stdout.decode('ascii')

    async def connected(self) -> bool:
        port = await self.get_port()
        return port is not None

    async def connect(self) -> None:
        args = ['attach', '-r', self.conf['host'], '-b', self.conf['bus_id']]

        await self.run_usbip(args)

    async def get_port(self) -> Optional[int]:
        """# usbip port
                Imported USB devices
                ====================
                Port 00: <Port in Use> at Low Speed(1.5Mbps)
                       unknown vendor : unknown product (1c4f:0002)
                       2-1 -> usbip://10.3.40.43:3240/1-11
                           -> remote bus/dev 001/008"""
        args = ['port']
        output = await self.run_usbip(args)
        header=True
        ports = output.split('\nPort ')[1:]  # Skip the first group which is just the header
        for port_option in ports:
            if f"/{self.conf['bus_id']}\n" in port_option:  # FIXME: This should try to match host too
                return port_option.split(':')[0]
        else:
            return None

    async def disconnect(self) -> None:

        port = await self.get_port()
        if port:
            args = ['detach', '-p', port]
            await self.run_usbip(args)
        else:
            print(f"Could not find port for bus_id '{self.conf['bus_id']}', maybe device is already "
                  f"disconnected")

    def setup_information(self):
        return """Linux is the only supported platform for USBIP. To use these devices on a Debian/Ubuntu based host 
                  you need to do the following setup once

                   # As root
                   apt-get install linux-tools-generic
                   modprobe vhci-hcd
                   echo 'vhci-hcd' >> /etc/modules # To load the 'vhci-hcd' module on boot in the future"""
