import binascii
import logging
from base64 import decodebytes
from io import StringIO

import paramiko
from django.conf import settings
from paramiko import HostKeys, ECDSAKey, PKey
from paramiko.hostkeys import InvalidHostKey

from USB_Quartermaster_common import CommunicatorError, AbstractCommunicator, CommandResponse

logger = logging.getLogger(__name__)


class SSHError(CommunicatorError):
    pass


class SSH(AbstractCommunicator):
    CONFIGURATION_KEYS = ("host_key", "host_key_type", "username", "private_key", "private_key_type")
    SUPPORTED_HOST_TYPES = ("Darwin", "Linux_AMD64", "Windows")
    IDENTIFIER = "SSH"
    
    PRIVATE_KEY_FORMAT_MAPPINGS = {'DSS': paramiko.DSSKey.from_private_key,
                                   'RSA': paramiko.RSAKey.from_private_key,
                                   'ECDSA': paramiko.ECDSAKey.from_private_key,
                                   'Ed25519': paramiko.Ed25519Key.from_private_key
                                   }

    HOST_KEY_FORMAT_MAPPINGS = {'ssh-dss': paramiko.DSSKey,
                                'ssh-rsa': paramiko.RSAKey,
                                'ssh-ed25519': paramiko.Ed25519Key
                                }
    for key in ECDSAKey.supported_key_format_identifiers():
        HOST_KEY_FORMAT_MAPPINGS[key] = paramiko.ECDSAKey

    def __init__(self, host):
        super().__init__(host)
        self.username = self.config["username"]

    def get_host_key(self) -> PKey:
        # Decide what kind of key we're looking at and create an object
        # to hold it accordingly.
        key_type = self.host.config['host_key_type']
        if key_type not in self.HOST_KEY_FORMAT_MAPPINGS:
            raise SSHError(f"Unable to handle key of type {key_type}")

        try:
            key = self.host.config['host_key'].encode('utf-8')
            host_key = self.HOST_KEY_FORMAT_MAPPINGS[key_type](data=decodebytes(key))
        except binascii.Error as e:
            raise InvalidHostKey(repr(self.host), e)
        return host_key

    def get_private_key(self):
        # Decide what kind of key we're looking at and create an object
        # to hold it accordingly.
        key_type = self.config['private_key_type']
        if key_type not in self.PRIVATE_KEY_FORMAT_MAPPINGS:
            raise SSHError(f"Unable to handle key of type {key_type}")

        try:
            key = self.config['private_key']
            private_key = self.PRIVATE_KEY_FORMAT_MAPPINGS[key_type](StringIO(key))
        except binascii.Error as e:
            raise SSHError(f"Private key error {repr(self.host)}", e)
        return private_key

    def get_client(self):
        client = paramiko.SSHClient()
        host_keys = HostKeys()
        host_keys.add(hostname=self.host.address,
                      keytype=self.config['host_key_type'],
                      key=self.get_host_key())
        client._host_keys = host_keys  # If you not a better way than accessing a private member I am all ears
        return client

    def execute_command(self, command: str) -> CommandResponse:
        client = self.get_client()
        try:
            client.connect(self.host.address,
                           username=self.config["username"],
                           pkey=self.get_private_key(),
                           timeout=settings.SSH_CONNECT_TIMEOUT)
            stdin, stdout, stderr = client.exec_command(command=command, timeout=settings.SSH_EXEC_TIMEOUT)
            return_code = stdout.channel.recv_exit_status()
            stdout_str = stdout.read().decode('UTF-8')
            stderr_str = stderr.read().decode('UTF-8')
            if return_code != 0:
                logger.info(
                    f"host={self.username}@{self.host.address} rc={return_code} command={command} stdout={stdout_str} stderr={stderr_str}")
        except paramiko.SSHException as e:
            logger.exception(f"Error: host={self.username}@{self.host.address}, command={command}")
            raise SSHError(
                f"Ran into problems connecting to {self.username}@{self.host.address}: {e}")
        finally:
            client.close()

        return CommandResponse(return_code, stdout_str, stderr_str)

    def is_host_reachable(self) -> bool:
        try:
            if self.host.type == "Windows":
                response = self.execute_command('date /t')
            else:
                response = self.execute_command('true')
        except Exception:
            return False
        return True
