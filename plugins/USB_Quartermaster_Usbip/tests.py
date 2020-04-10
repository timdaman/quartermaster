from unittest.mock import patch, MagicMock

import pytest

from UsbipOverSSH.driver import UsbipOverSSHHost
from quartermaster.AbstractCommunicator import CommandResponse

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
    with patch('USB_Quartermaster_Usbip.USB_Quartermaster_Usbip.get_share_state') as share_state:
        share_state.return_value = True
        driver = sample_shared_device.get_driver()
        assert True == driver.is_shared()


@pytest.mark.django_db
def test_device_is_not_shared(sample_unshared_device):
    with patch('USB_Quartermaster_Usbip.USB_Quartermaster_Usbip.get_share_state') as share_state:
        share_state.return_value = False
        driver = sample_unshared_device.get_driver()
        assert False == driver.is_shared()


@pytest.mark.django_db
def test_share_devices_double_on(sample_shared_device):
    with patch('USB_Quartermaster_Usbip.USB_Quartermaster_Usbip.execute_command') as execute_command, \
            patch('USB_Quartermaster_Usbip.USB_Quartermaster_Usbip.get_share_state') as share_state:
        share_state.return_value = [True, True]
        driver = sample_shared_device.get_driver()
        driver.share()
        assert 0 == execute_command.call_count


@pytest.mark.django_db(transaction=True)
def test_share_devices_initial_off(sample_unshared_device):
    with patch('USB_Quartermaster_Usbip.USB_Quartermaster_Usbip.execute_command') as execute_command, \
            patch('USB_Quartermaster_Usbip.USB_Quartermaster_Usbip.get_share_state') as get_share_state:
        get_share_state.return_value = False
        # A successful attachment has no output
        execute_command.return_value = CommandResponse(0, '', '')
        driver = sample_unshared_device.get_driver()

        driver.share()
        assert 1 == execute_command.call_count


@pytest.mark.django_db
def test_unshare_devices_double_off(sample_unshared_device):
    with patch('USB_Quartermaster_Usbip.USB_Quartermaster_Usbip.stop_sharing') as stop_sharing, \
            patch('USB_Quartermaster_Usbip.USB_Quartermaster_Usbip.is_shared') as is_shared:
        is_shared.return_value = False
        driver = sample_unshared_device.get_driver()

        driver.unshare()
        assert 0 == stop_sharing.call_count


@pytest.mark.django_db(transaction=True)
def test_turn_off_devices_initial_on(sample_shared_device):
    with patch('USB_Quartermaster_Usbip.USB_Quartermaster_Usbip.execute_command') as execute_command, \
            patch('USB_Quartermaster_Usbip.USB_Quartermaster_Usbip.get_share_state') as get_share_state:
        get_share_state.return_value = True
        # A successful attachment has no output
        execute_command.return_value = (0, '', '')
        driver = sample_shared_device.get_driver()

        driver.unshare()
        assert 1 == execute_command.call_count


@pytest.mark.django_db
def test_host_address(sample_shared_device):
    driver = sample_shared_device.get_driver()
    assert sample_hostname == driver.host.address


@pytest.mark.django_db
def test_get_online_state_online(sample_shared_device, sample_list_stdout):
    driver = sample_shared_device.get_driver()
    mock_host_driver = MagicMock()
    mock_host_driver.get_device_list.return_value = {sample_bus_id: None}  # All we check for is the presence of the key
    driver.host_driver = mock_host_driver
    assert driver.get_online_state()


@pytest.mark.django_db
def test_get_online_state_offline(sample_unshared_device):
    driver = sample_unshared_device.get_driver()
    mock_host_driver = MagicMock()
    mock_host_driver.get_device_list.return_value = {sample_bus_id: None}  # All we check for is the presence of the key
    driver.host_driver = mock_host_driver
    assert not driver.get_online_state()


@pytest.mark.django_db
def test_get_online_state_none(sample_unshared_device):
    driver = sample_unshared_device.get_driver()
    mock_host_driver = MagicMock()
    mock_host_driver.execute_command.return_value = CommandResponse(0, '', UsbipOverSSHHost.NO_REMOTE_DEVICES)
    driver.host_driver = mock_host_driver
    assert False == driver.get_online_state()
