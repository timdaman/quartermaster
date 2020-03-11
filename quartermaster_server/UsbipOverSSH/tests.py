from unittest.mock import patch

import pytest

from UsbipOverSSH import UsbipOverSSH

sample_bus_id = '1-11'
sample_hostname = 'example.com'


@pytest.fixture()
def sample_list_stdout() -> str:
    return """
         - busid 1-11 (1c4f:0002)
           SiGma Micro : Keyboard TRACER Gamma Ivory (1c4f:0002)
        
         - busid 1-12 (0000:0538)
           unknown vendor : unknown product (0000:0538)
        """


@pytest.mark.django_db
def test_device_is_shared(sample_shared_device):
    with patch('UsbipOverSSH.UsbipOverSSH.ssh') as ssh_command:
        ssh_command.return_value = 0, '', ''
        driver = sample_shared_device.get_driver()
        assert True == driver.is_shared()


@pytest.mark.django_db
def test_device_is_not_shared(sample_unshared_device):
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
def test_share_devices_initial_off(sample_unshared_device):
    with patch('UsbipOverSSH.UsbipOverSSH.ssh') as ssh_command, \
            patch('UsbipOverSSH.UsbipOverSSH.is_shared') as device_is_shared:
        device_is_shared.return_value = False
        # A successful attachment has no output
        ssh_command.return_value = (0, '', None)
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
def test_turn_off_devices_initial_on(sample_shared_device):
    with patch('UsbipOverSSH.UsbipOverSSH.ssh') as ssh_command, \
            patch('UsbipOverSSH.UsbipOverSSH.is_shared') as device_is_shared:
        device_is_shared.return_value = True
        # A successful attachment has no output
        ssh_command.return_value = (0, '', None)
        driver = sample_shared_device.get_driver()

        driver.unshare()
        assert 2 == ssh_command.call_count


@pytest.mark.django_db
def test_host_address(sample_shared_device):
    driver = sample_shared_device.get_driver()
    assert sample_hostname == driver.host.address


@pytest.mark.django_db
def test_get_online_state_online(sample_shared_device, sample_list_stdout):
    with patch('UsbipOverSSH.UsbipOverSSH.ssh') as ssh_command:
        ssh_command.return_value = 0, sample_list_stdout, ''
        driver = sample_shared_device.get_driver()
        assert True == driver.get_online_state()


@pytest.mark.django_db
def test_get_online_state_offline(sample_unshared_device):
    with patch('UsbipOverSSH.UsbipOverSSH.ssh') as ssh_command:
        ssh_command.return_value = (0, '', '')
        driver = sample_unshared_device.get_driver()
        assert False == driver.get_online_state()


@pytest.mark.django_db
def test_get_online_state_error(sample_unshared_device):
    with patch('UsbipOverSSH.UsbipOverSSH.ssh') as ssh_command:
        ssh_command.return_value = (1, '', '')
        driver = sample_unshared_device.get_driver()
        with pytest.raises(UsbipOverSSH.DeviceCommandError):
            driver.get_online_state()


@pytest.mark.django_db
def test_get_online_state_none(sample_unshared_device):
    with patch('UsbipOverSSH.UsbipOverSSH.ssh') as ssh_command:
        ssh_command.return_value = (0, '', UsbipOverSSH.NO_REMOTE_DEVICES)
        driver = sample_unshared_device.get_driver()
        assert False == driver.get_online_state()
