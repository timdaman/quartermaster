import asyncio
import platform
import re
import shutil
import subprocess
import time
from typing import Optional, List

from .LocalDriver import LocalDriver


class VirtualHereOverSSH(LocalDriver):
    OK_MATCHER = re.compile("^OK$", flags=re.MULTILINE)
    LINUX_CLIENT_NAME = f"vhclient{platform.machine()}"

    vh: str

    def __init__(self, conf):
        self.conf = conf

    def preflight_check(self):
        # Confirm VirtualHere client is installed and running
        self.start_client_service()

    async def async_init(self):
        self.vh = self.find_vh()
        await self.attach_hub()

    def start_client_service(self):
        target_platform = platform.system().lower()
        if target_platform in ('darwin', 'mac', 'macos', 'macosx'):
            self.setup_mac_client()
        elif target_platform == 'linux':
            self.setup_linux_client()
        else:
            raise self.UnsupportedPlatform(f"Unsupported platform {target_platform}")

    @staticmethod
    def mac_find_vh() -> Optional[str]:
        try:
            app_name_fragment = 'VirtualHere.app/Contents/MacOS/VirtualHere'
            output = subprocess.check_output(('pgrep', '-lf', app_name_fragment),
                                             encoding='utf-8')
            # Find path in output, assume it looks like on the following
            # '18643 /Applications/VirtualHere.app/Contents/MacOS/VirtualHere'
            # '1598 /Applications/VirtualHere.app/Contents/MacOS/VirtualHere --log=OSEventLog -n'
            match = re.match(f"^\d+ (?P<cmd>.+{app_name_fragment})", output.splitlines()[0])
            return match['cmd']
        except subprocess.CalledProcessError:
            # Assume process is not running
            return None

    def linux_find_vh(self):
        return shutil.which(self.LINUX_CLIENT_NAME)

    def find_vh(self) -> str:
        target_platform = platform.system().lower()
        if target_platform in ('darwin', 'mac', 'macos', 'macosx'):
            return VirtualHereOverSSH.mac_find_vh()
        elif target_platform == 'linux':
            return self.linux_find_vh()
        else:
            raise self.UnsupportedPlatform(f"Unsupported platform {target_platform}")

    def setup_mac_client(self) -> List[str]:
        # check if client is running and get path
        vh_path = self.mac_find_vh()

        if not vh_path:
            # Assume process is not running
            try:
                print("Starting VirtualHere")
                subprocess.check_call(('open', '-ga', 'VirtualHere'))
                time.sleep(2)  # Give client service some time to start
            except subprocess.CalledProcessError:
                raise LocalDriver.CommandError("Looks like VirtualHere might not be installed or runnable")
            vh_path = VirtualHereOverSSH.mac_find_vh()

        if vh_path is None:
            # Start if needed and get path
            try:
                print("Starting VirtualHere")
                subprocess.check_call(('open', '-ga', 'VirtualHere'))
                time.sleep(2)  # Give client service some time to start
            except subprocess.CalledProcessError:
                raise LocalDriver.CommandError("Looks like VirtualHere might not be installed or runnable")
            vh_path = VirtualHereOverSSH.mac_find_vh()
        return [vh_path]

    def setup_linux_client(self):
        # Check for sudo
        sudo = shutil.which('sudo')
        if not sudo:
            raise LocalDriver.CommandError("sudo is needed and was not found in path")

        # Check for client
        vhclient = self.linux_find_vh()
        if not vhclient:
            raise LocalDriver.CommandError(
                f"{self.LINUX_CLIENT_NAME} is needed and was not found in path. {self.setup_information()}")

        # start client if needed
        try:
            subprocess.check_output(('pgrep', self.LINUX_CLIENT_NAME))
        except subprocess.CalledProcessError:
            # Assume client is not running if we get a non-zero
            print("Starting VirtualHere client service, if this failed you may need to start it "
                  f"manually by running `sudo {vhclient} -n`")
            subprocess.check_call(('sudo', vhclient, '-n'))  # TODO: Can I pass through stdin?
            time.sleep(2)  # Give client service some time to start

    async def run_vh(self, args):
        proc = await asyncio.create_subprocess_exec(
            self.vh, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT)
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise self.CommandError(
                f'Error: command={self.vh} {args}, rc={proc.returncode}, stdout={stdout}, stderr={stderr}')

        return stdout.decode('ascii')

    async def attach_hub(self):
        args = ['-t', 'MANUAL HUB LIST']
        hub_list = await self.run_vh(args)
        for hub in hub_list.splitlines():
            if hub.startswith(self.conf['host_address']):  # Hub already connected
                break
        else:
            args = ['-t', f"MANUAL HUB ADD,{self.conf['host_address']}"]
            output = await self.run_vh(args)
            if not self.OK_MATCHER.search(output):
                raise self.CommandError(
                    f"VirtualHere did not return 'OK' when connecting hub '{self.conf['host_address']}', "
                    f"instead I got '{output}'")

    async def connect(self):
        args = ['-t', f"USE,{self.conf['device_address']}"]
        output = await self.run_vh(args)
        if not self.OK_MATCHER.search(output):
            raise self.CommandError(f"VirtualHere did not return 'OK' when connecting device, instead I got '{output}'")

    async def disconnect(self):
        args = ['-t', f"STOP USING,{self.conf['device_address']}"]
        output = await self.run_vh(args)
        if not self.OK_MATCHER.search(output):
            raise self.CommandError(
                f"VirtualHere did not return 'OK' when disconnecting device, instead I got '{output}'")

    async def connected(self) -> bool:
        """
        # vhclientx86_64 -t 'device info,spf3-topaz-1.17'
        ADDRESS: spf3-topaz-1.17
        VENDOR: Android
        VENDOR ID: 0x05c6
        PRODUCT: Android
        PRODUCT ID: 0x901d
        SERIAL: 1f53203a
        NICKNAME: KonaFrames01
        IN USE BY: NO ONE
        """
        args = ['-t', f"DEVICE INFO,{self.conf['device_address']}"]
        output = await self.run_vh(args)
        return "IN USE BY: NO ONE" not in output

    def setup_information(self):
        return "To use these Virtual here resources you must have the VirtualHere client installed and running. " \
               "You can download the client at https://virtualhere.com/usb_client_software"
