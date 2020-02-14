from io import BytesIO
from typing import Tuple
from unittest.mock import patch

import pytest

from UsbipOverSSH import UsbipOverSSH

sample_bus_id = '1-11'
sample_host = 'example.com'


@pytest.fixture()
def sample_list_stdout() -> BytesIO:
    return BytesIO("""
        Exportable USB devices
        ======================
         - localhost
               1-11: SiGma Micro : Keyboard TRACER Gamma Ivory (1c4f:0002)
                   : /sys/devices/pci0000:00/0000:00:14.0/usb1/1-11
                   : (Defined at Interface level) (00/00/00)
                   :  0 - Human Interface Device / Boot Interface Subclass / Keyboard (03/01/01)
                   :  1 - Human Interface Device / No Subclass / None (03/00/00)
        """.encode('ascii'))


@pytest.fixture()
def blank_bytes() -> BytesIO:
    return BytesIO(''.encode('ascii'))


@pytest.fixture()
def sample_ssh_output(sample_list_stdout, blank_bytes) -> Tuple[int, BytesIO, BytesIO]:
    return (0, sample_list_stdout, blank_bytes)


@pytest.mark.django_db
def test_device_is_shared(blank_bytes, sample_shared_device):
    with patch('UsbipOverSSH.UsbipOverSSH.ssh') as ssh_command:
        ssh_command.return_value = 0, '', ''
        driver = sample_shared_device.get_driver()
        assert True == driver.is_shared()


@pytest.mark.django_db
def test_device_is_not_shared(blank_bytes, sample_unshared_device):
    with patch('UsbipOverSSH.UsbipOverSSH.ssh') as ssh_command:
        ssh_command.return_value = 0, 'missing', ''
        driver = sample_unshared_device.get_driver()
        assert False == driver.is_shared()


@pytest.mark.django_db
def test_share_devices_double_on(sample_shared_device):
    with patch('UsbipOverSSH.UsbipOverSSH.ssh') as ssh_command, \
            patch('UsbipOverSSH.UsbipOverSSH.is_shared') as device_is_shared:
        device_is_shared.return_value = True
        driver = sample_shared_device.get_driver()
        driver.share()
        assert 0 == ssh_command.call_count


@pytest.mark.django_db
def test_share_devices_double_on(sample_shared_device):
    with patch('UsbipOverSSH.UsbipOverSSH.ssh') as ssh_command, \
            patch('UsbipOverSSH.UsbipOverSSH.is_shared') as device_is_shared:
        device_is_shared.return_value = True
        driver = sample_shared_device.get_driver()
        driver.share()
        assert 0 == ssh_command.call_count


@pytest.mark.django_db(transaction=True)
def test_share_devices_initial_off(sample_unshared_device, blank_bytes):
    with patch('UsbipOverSSH.UsbipOverSSH.ssh') as ssh_command, \
            patch('UsbipOverSSH.UsbipOverSSH.is_shared') as device_is_shared:
        device_is_shared.return_value = False
        # A successful attachment has no output
        ssh_command.return_value = (0, blank_bytes, None)
        driver = sample_unshared_device.get_driver()

        driver.share()
        assert 1 == ssh_command.call_count


@pytest.mark.django_db
def test_unshare_devices_double_off(sample_unshared_device):
    with patch('UsbipOverSSH.UsbipOverSSH.stop_sharing') as stop_sharing, \
            patch('UsbipOverSSH.UsbipOverSSH.is_shared') as is_shared:
        is_shared.return_value = False
        driver = sample_unshared_device.get_driver()

        driver.unshare()
        assert 0 == stop_sharing.call_count


@pytest.mark.django_db(transaction=True)
def test_turn_off_devices_initial_on(sample_shared_device, blank_bytes):
    with patch('UsbipOverSSH.UsbipOverSSH.ssh') as ssh_command, \
            patch('UsbipOverSSH.UsbipOverSSH.is_shared') as device_is_shared:
        device_is_shared.return_value = True
        # A successful attachment has no output
        ssh_command.return_value = (0, blank_bytes, None)
        driver = sample_shared_device.get_driver()

        driver.unshare()
        assert 2 == ssh_command.call_count


@pytest.mark.django_db
def test_host(sample_shared_device):
    driver = sample_shared_device.get_driver()

    assert sample_host == driver.host


@pytest.mark.django_db
def test_get_online_state_online(sample_shared_device, sample_ssh_output):
    with patch('UsbipOverSSH.UsbipOverSSH.ssh') as ssh_command:
        ssh_command.return_value = 0, sample_ssh_output, ''
        driver = sample_shared_device.get_driver()
        assert True == driver.get_online_state()


@pytest.mark.django_db
def test_get_online_state_offline(sample_unshared_device, blank_bytes):
    with patch('UsbipOverSSH.UsbipOverSSH.ssh') as ssh_command:
        ssh_command.return_value = (0, blank_bytes, blank_bytes)
        driver = sample_unshared_device.get_driver()
        assert False == driver.get_online_state()


@pytest.mark.django_db
def test_get_online_state_error(sample_unshared_device, blank_bytes):
    with patch('UsbipOverSSH.UsbipOverSSH.ssh') as ssh_command:
        ssh_command.return_value = (1, blank_bytes, blank_bytes)
        driver = sample_unshared_device.get_driver()
        with pytest.raises(UsbipOverSSH.DeviceCommandError):
            driver.get_online_state()


@pytest.mark.django_db
def test_get_online_state_none(sample_unshared_device, blank_bytes):
    with patch('UsbipOverSSH.UsbipOverSSH.ssh') as ssh_command:
        ssh_command.return_value = (0, '', UsbipOverSSH.NO_REMOTE_DEVICES)
        driver = sample_unshared_device.get_driver()
        assert False == driver.get_online_state()
