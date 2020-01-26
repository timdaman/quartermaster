#!/usr/bin/env python3
import asyncio
import json
import logging
import signal
import socket
import ssl
import sys
from argparse import Namespace, ArgumentParser
from asyncio import CancelledError
from functools import partial
from typing import Dict, List, NamedTuple, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen, Request

from . import driver

TEARDOWN_COMMAND = b"teardown"
TEARDOWN_ACK = b"Teardown started"
REFRESH_RETRY_LIMIT = 3
REFRESH_RETRY_SLEEP = 10

VERSION = '1.0'

logger = logging.getLogger()

error_counter = 0


#
#  ___  _____   _____ ___ ___ ___
# |   \| __\ \ / /_ _/ __| __/ __|
# | |) | _| \ V / | | (__| _|\__ \
# |___/|___| \_/ |___\___|___|___/
#
class Device(object):
    connect_complete = False

    def __init__(self, conf: Dict):
        self.conf = conf
        self.name = conf['name']
        loaded_drivers = {driver_class.__name__: driver_class for driver_class in driver.LocalDriver.__subclasses__()}
        if conf['driver'] in loaded_drivers:
            self.driver = loaded_drivers[conf['driver']](conf=conf)
        else:
            raise SystemError(f"No driver found to support driver='{conf['driver']}'")

    async def async_init(self):
        await self.driver.async_init()
        await self.connect()

    async def connect(self):
        if not await self.connected():
            print(f"Connecting {self.name}")
            await self.driver.connect()
            self.connect_complete = True
            print(f"Done connecting {self.name}")

    async def disconnect(self):
        if await self.connected():
            print(f"Disconnecting {self.name}")
            await self.driver.disconnect()
            print(f"Done disconnecting {self.name}")

    async def connected(self):
        return await self.driver.connected()

    def __str__(self):
        return self.name


class Reservation(NamedTuple):
    devices: List[Device]
    use_password: str
    resource_url: str
    reservation_url: str
    auth_token: str = None


async def manage_devices(devices: List[Device], polling_interval: int):
    for device in devices:
        await device.async_init()
    print("Setup complete, keep this terminal open to keep your reservation active")

    while True:
        logger.debug('.')
        for device in devices:
            await device.connect()  # connect() is lazy, if device is connected it won't do anything
        await asyncio.sleep(polling_interval)


async def disconnect_devices(devices: List[Device]):
    """
    Disconnect devices

    """
    global error_counter
    for device in devices:
        if device.connect_complete:
            print(f"Disconnecting {device.name}")
            try:
                await device.disconnect()
            except Exception as e:  # Swallowing exception so disconnection failures don't impact each other
                error_counter += 1
                print(f"Got the following exception when trying to disconnect {device.name}: {e}")
        else:
            print(f"Skipping disconnecting {device.name} as it never completed connecting")


async def get_resource_status(url: str, config: Namespace, teardown: asyncio.Event):
    while True:
        logger.debug('+')
        refresh_successful = None
        for _ in range(0, REFRESH_RETRY_LIMIT):
            try:
                refresh_successful = refresh_reservation(url, config.auth_token, config.disable_validation)
                break # The retry loop
            except Exception:
                await asyncio.sleep(REFRESH_RETRY_SLEEP)
        else:
            logger.error(f"Failed to reach Quartermaster server after {REFRESH_RETRY_LIMIT} tries. Triggering teardown")
            teardown.set()

        if refresh_successful:
            await asyncio.sleep(config.reservation_polling)
            continue
        else:
            print("Reservation expired, triggering teardown")
            teardown.set()


def preflight_checks(reservation: Reservation):
    """
    This calls every driver being used by the current reservation to perform basic checks to catch problem before we
    start attaching devices. Success is running this function not raising any Exceptions.
    """
    drivers_checked = set()
    for device in reservation.devices:
        driver = device.conf['driver']
        if driver in drivers_checked:
            continue
        print(f"Preflight checking {driver}")
        device.driver.preflight_check()
        drivers_checked.add(driver)


#
#  ___ ___ _____   _____ ___    ___ ___  __  __ __  __ ___
# / __| __| _ \ \ / / __| _ \  / __/ _ \|  \/  |  \/  / __|
# \__ \ _||   /\ V /| _||   / | (_| (_) | |\/| | |\/| \__ \
# |___/___|_|_\ \_/ |___|_|_\  \___\___/|_|  |_|_|  |_|___/
#
class QuartermasterServerError(Exception):
    pass


def quartermaster_request(url: str, method: str,
                          token: Optional[str] = None,
                          data: Optional[bytes] = None,
                          disable_validation=False) -> [int, bytes, str]:
    headers = {'Accept': 'application/json',
               "Quartermaster_client_version": VERSION}
    if token:
        headers["Authorization"] = f'Token {token}'
    logger.debug(f"headers={headers}")

    request_args = {'url': url,
                    'method': method,
                    'headers': headers
                    }
    if data:
        request_args['data'] = data

    req = Request(**request_args)

    extra_urlopen_args = {}
    if disable_validation:
        extra_urlopen_args['context'] = ssl._create_unverified_context()
    try:
        # TODO: Probably should add a retry loop here
        response = urlopen(req, timeout=10, **extra_urlopen_args)
        http_code = response.code
        content = response.read()
        final_url = response.geturl()
        logger.debug(f"Final URL = {final_url}")
    except HTTPError as e:
        http_code = e.code
        content = e.msg,
        final_url = url
    except URLError as e:
        raise QuartermasterServerError(f"Error trying to reach quartermaster server: {e}")

    logger.debug(f"Response {http_code} {content}")

    return http_code, content, final_url


def get_quartermaster_reservation(url: str, message: Optional[str],
                                  auth_token: Optional[str] = None,
                                  disable_validation=False) -> Reservation:
    # POST method because data is being passed. Server will create a reservation, or if the token own already
    # has one it will return the already active reservation

    values = {}
    if message is not None:
        values['used_for'] = message

    data = urlencode(values).encode('utf-8')
    http_code, content, final_url = quartermaster_request(url=url,
                                                          token=auth_token,
                                                          method='POST',
                                                          data=data,
                                                          disable_validation=disable_validation)

    if http_code == 404:
        raise QuartermasterServerError(f"That reservation was not found")
    elif http_code not in [200, 201]:
        raise QuartermasterServerError(f"Got unexpected response from server when retrieving reservation. "
                                       f"HTTP STATUS={http_code}, BODY={content}")
    decoded = json.loads(content, encoding='utf-8')
    return Reservation(devices=[Device(device) for device in decoded['devices']],
                       use_password=decoded['use_password'],
                       resource_url=final_url,
                       reservation_url=url, auth_token=auth_token)


def refresh_reservation(url: str, auth_token: Optional[str] = None, disable_validation=False) -> bool:
    http_code, content, _ = quartermaster_request(url=url,
                                                  token=auth_token,
                                                  method='PATCH',
                                                  disable_validation=disable_validation)
    if http_code == 404:
        return False
    elif http_code != 202:
        raise ConnectionError(f"Unexpected response from server, HTTP CODE={http_code}, CONTENT={content}")
    return True


def cancel_reservation(url: str, auth_token: Optional[str] = None, disable_validation=False) -> bool:
    print(f"Canceling reservation {url}")
    http_code, content, _ = quartermaster_request(url=url,
                                                  token=auth_token,
                                                  method='DELETE',
                                                  disable_validation=disable_validation)
    if http_code == 204:
        print("Reservation canceled successfully")
        return True
    raise ConnectionError(f"Unexpected response when canceling reservation, HTTP CODE={http_code}, CONTENT={content}")


async def process_command(reader, writer, teardown: asyncio.Event):
    while True:
        data = await reader.read(100)
        if data == b'':  # This means EOF was received and the internal buffer is empty
            break

        logger.debug(f"Command received, {data}")
        if data.startswith(TEARDOWN_COMMAND + b"\r") or data.startswith(TEARDOWN_COMMAND + b"\n"):
            writer.write(TEARDOWN_ACK)
            print(TEARDOWN_ACK.decode('utf-8'))
            teardown.set()
            await writer.drain()
            writer.close()
            await writer.wait_closed()


async def wait_for_commands(config: Namespace, teardown: asyncio.Event):
    while True and not teardown.is_set():
        try:
            server = await asyncio.start_server(partial(process_command, teardown=teardown), host=config.listen_ip,
                                                port=config.listen_port)

            async with server:
                logger.debug(f"Listening on {config.listen_ip}:{config.listen_port} for commands")
                await server.serve_forever()
        except Exception as e:
            print(f"Exception when trying to to start command listener: {e}")
            teardown.set()


def initiate_teardown(config: Namespace):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((config.listen_ip, config.listen_port))
        s.sendall(b'teardown\r')
        data = s.recv(100)
    print(data.decode('utf-8'))
    if data == TEARDOWN_ACK:
        exit(0)
    else:
        print(f"Unexpected response from client at {config.listen_ip}:{config.listen_port}")
        exit(1)


async def start_tasks(reservation: Reservation, config: Namespace):
    teardown_event = asyncio.Event()
    loop = asyncio.get_event_loop()
    runtime_tasks = [
        loop.create_task(manage_devices(devices=reservation.devices, polling_interval=config.device_polling)),
        loop.create_task(
            get_resource_status(url=reservation.resource_url, config=config, teardown=teardown_event)),
        loop.create_task(wait_for_commands(config=config, teardown=teardown_event))
    ]

    loop.add_signal_handler(signal.SIGINT, teardown_event.set)  # ctrl-c
    loop.add_signal_handler(signal.SIGTERM, teardown_event.set)  # kill
    loop.add_signal_handler(signal.SIGTERM, teardown_event.set)  # quit
    loop.add_signal_handler(signal.SIGHUP, teardown_event.set)  # Hangup (closed terminal?)

    teardown_task = loop.create_task(
        perform_teardown(tasks=runtime_tasks, teardown_event=teardown_event, devices=reservation.devices))
    try:
        await asyncio.gather(*runtime_tasks, teardown_task)
    except CancelledError:
        pass  # This is expected as part of the teardown flow
    except Exception as e:  # If any task blows up trigger a teardown
        teardown_event.set()
        await teardown_task
        raise e


async def perform_teardown(tasks: List, teardown_event: asyncio.Event, devices: List[Device]):
    """
    This does the work of cleanly shutting down the client.
    That includes canceling all the other tasks and disconnect
    """
    await teardown_event.wait()
    for task in tasks:
        task.cancel()

    await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)

    errors_encountered = await disconnect_devices(devices)  # TODO: Should make this durable, i.e. ignore exceptions


def load_arguments(args: List[str], reservation_message=None, auth_token=None, reservation_url=None) -> Namespace:
    parser = ArgumentParser()
    parser.add_argument("--listen_ip", type=str, default='127.0.0.1', help="Where to listen for local commands")
    parser.add_argument("--listen_port", type=int, default=4242, help="What port to listen for local commands")
    parser.add_argument("--debug", action="store_true", default=False, help="Enable debugging output")

    parser.add_argument("--auth_token", type=str, default=auth_token,
                        help="Quartermaster server authentication token, only needed when --reservation_url doesn't "
                             "include use credential")
    parser.add_argument("--reservation_message", type=str, help="Message displayed with reservation",
                        default=reservation_message)
    parser.add_argument("--device_polling", type=int, default=5,
                        help="How many seconds to wait between checks to ensure devices are connected")
    parser.add_argument("--reservation_polling", type=int, default=60,
                        help="How many seconds to wait between checks to ensure resource reservation is still active")
    parser.add_argument("--disable_validation", action='store_true',
                        help="Disable TLS validation of server certificates")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--stop_client", action='store_true',
                       help="Stop the Quartermaster client. uses the --listen-* arguments if present")
    group.add_argument('quartermaster_url', metavar='quartermaster_url', type=str, default=reservation_url,
                       help='URL to quartermaster server reservation', nargs='?')
    all_parsed = parser.parse_args(args)
    return all_parsed


def main(args: List[str]):
    config = load_arguments(args)

    # Setup logging
    if config.debug:
        logging.basicConfig(level=logging.DEBUG)

    if config.stop_client:
        initiate_teardown(config=config)
        return

    reservation = None
    try:
        reservation = get_quartermaster_reservation(url=config.quartermaster_url,
                                                    auth_token=config.auth_token,
                                                    message=config.reservation_message,
                                                    disable_validation=config.disable_validation)
        print(f"Reservation active for resource {reservation.resource_url}")
        preflight_checks(reservation)
        asyncio.run(start_tasks(reservation, config), debug=config.debug)
        print("Cleanup done")
    except Exception as e:
        print(e)
        if reservation is not None:
            print(f"Canceling reservation for resource {reservation.resource_url}, please wait")
            try:
                cancel_reservation(url=reservation.reservation_url, auth_token=reservation.auth_token,
                                   disable_validation=config.disable_validation)
            except Exception as ee:
                print(f"We got an exception while trying to cancel our reservation: {ee}")

        if config.debug:  # So we get a stack traces
            raise e
        exit(1)

    if reservation is not None:
        print(f"Canceling reservation for resource {reservation.resource_url}, please wait")
        cancel_reservation(url=reservation.reservation_url, auth_token=reservation.auth_token,
                           disable_validation=config.disable_validation)

    exit(error_counter)


if __name__ == '__main__':
    main(sys.argv[1:])
