import asyncio
import platform
import re
import shutil
from typing import List

from .LocalDriver import LocalDriver


class UsbipOverSSH(LocalDriver):
    NO_REMOTE_DEVICES = b'usbip: info: no exportable devices found on '

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
        proc = await asyncio.create_subprocess_exec(
            'sudo', self.usbip, *arguments,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        stdout, stderr = await proc.communicate()

        if proc.returncode != 0 and self.NO_REMOTE_DEVICES not in stderr:
            raise self.CommandError(
                f'Error: command={arguments}, rc={proc.returncode}, stdout={stdout}, stderr={stderr}')

        return stdout.decode('ascii')

    async def connected(self):
        args = ['list', '-r', self.conf['host']]
        output = await self.run_usbip(arguments=args)

        # This takes this
        #  1-11: SiGma Micro : Keyboard TRACER Gamma Ivory (1c4f:0002)
        # and makes this
        #  1-11
        device_lines = r'^ +\d+-[0-9.]+: '
        available = [line[:line.find(':')].replace(' ', '')
                     for line in output.splitlines()
                     if re.match(device_lines, line)]
        return self.conf['bus_id'] in available

    async def connect(self) -> None:
        args = ['attach', '-r', self.conf['host'], '-b', self.conf['bus_id']]
        await self.run_usbip(args)

    async def disconnect(self) -> None:
        """# usbip port
        Imported USB devices
        ====================
        Port 00: <Port in Use> at Low Speed(1.5Mbps)
               unknown vendor : unknown product (1c4f:0002)
               2-1 -> usbip://10.3.40.43:3240/1-11
                   -> remote bus/dev 001/008"""
        args = ['port']
        output = await self.run_usbip(args)
        ports = output.split('\nPort ')[1:]  # Skip the first group which is just the header
        for port_option in ports:
            if f"/{self.conf['bus_id']}\n" in port_option:
                port = port_option.split(':')[0]
                args = ['detach', '-p', port]
                await self.run_usbip(args)
        else:
            print(f"Could not find port for bus_id '{self.conf['bus_id']}', maybe device is already "
                  f"disconnected, Looked in {output}")

    def setup_information(self):
        return """Linux is the only supported platform for USBIP. To use these devices on a Debian/Ubuntu based host 
                  you need to do the following setup once

                   # As root
                   apt-get install linux-tools-generic
                   modprobe vhci-hcd
                   echo 'vhci-hcd' >> /etc/modules # To load the 'vhci-hcd' module on boot in the future"""
