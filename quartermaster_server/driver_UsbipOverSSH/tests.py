import json
import unittest
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import User

from data.models import Pool, Resource, Device


class UsbipOverSSHTestCase(unittest.TestCase):
    sample_list_stdout = BytesIO("""
            Exportable USB devices
            ======================
             - localhost
                   1-11: SiGma Micro : Keyboard TRACER Gamma Ivory (1c4f:0002)
                       : /sys/devices/pci0000:00/0000:00:14.0/usb1/1-11
                       : (Defined at Interface level) (00/00/00)
                       :  0 - Human Interface Device / Boot Interface Subclass / Keyboard (03/01/01)
                       :  1 - Human Interface Device / No Subclass / None (03/00/00)
            """.encode('ascii'))
    blank_bytes = BytesIO(''.encode('ascii'))

    sample_list_ssh_output = (0, sample_list_stdout, blank_bytes)

    @classmethod
    def setUpClass(cls) -> None:
        cls.user = User.objects.create_superuser(username="TEST_USER_DEVICE_MANAGER",
                                                 email="not_real@example.com",
                                                 password="lolSecret")
        cls.pool = Pool.objects.create(name='TEST_POOL_DEVICE_MANAGER')
        cls.resource = Resource.objects.create(pool=cls.pool, name=f"RESOURCE_1_DEVICE_MANAGER")

        cls.devices = []
        for bus_id in ('1-11', '1-1', '11-1.1', '1-11.11'):
            device_config = {'host': '127.0.0.5', 'bus_id': bus_id}
            cls.devices.append(
                Device.objects.create(resource=cls.resource, driver='UsbipOverSSH',
                                      config_json=json.dumps(device_config), name=f"Device usbip {bus_id}")
            )
        super().setUpClass()

    def setUp(self) -> None:
        self.blank_bytes.seek(0)
        self.sample_list_stdout.seek(0)

    def test_device_is_shared(self):
        with patch('driver_UsbipOverSSH.UsbipOverSSH.ssh') as ssh_command:
            ssh_command.return_value = self.sample_list_ssh_output
            driver = self.devices[0].get_driver()
            self.assertTrue(driver.is_shared())

    def test_device_is_not_shared(self):
        with patch('driver_UsbipOverSSH.UsbipOverSSH.ssh') as ssh_command:
            ssh_command.return_value = self.sample_list_ssh_output
            driver = self.devices[1].get_driver()
            self.assertFalse(driver.is_shared())

    def test_share_devices_double_on(self):
        with patch('driver_UsbipOverSSH.UsbipOverSSH.ssh') as ssh_command, \
                patch('driver_UsbipOverSSH.UsbipOverSSH.is_shared') as device_is_shared:
            device_is_shared.return_value = True
            driver = self.devices[1].get_driver()
            driver.share()
            self.assertFalse(ssh_command.called)

    def test_share_devices_initial_off(self):
        with patch('driver_UsbipOverSSH.UsbipOverSSH.ssh') as ssh_command, \
                patch('driver_UsbipOverSSH.UsbipOverSSH.is_shared') as device_is_shared:
            device_is_shared.return_value = False
            # A successful attachment has no output
            ssh_command.return_value = (0, self.blank_bytes, None)
            driver = self.devices[1].get_driver()

            driver.share()
            self.assertTrue(ssh_command.called)

    def test_unshare_devices_double_off(self):
        with patch('driver_UsbipOverSSH.UsbipOverSSH.stop_sharing') as stop_sharing, \
                patch('driver_UsbipOverSSH.UsbipOverSSH.is_shared') as is_shared:
            is_shared.return_value = False
            driver = self.devices[1].get_driver()

            driver.unshare()
            self.assertFalse(stop_sharing.called)

    def test_turn_off_devices_initial_on(self):
        with patch('driver_UsbipOverSSH.UsbipOverSSH.ssh') as ssh_command, \
                patch('driver_UsbipOverSSH.UsbipOverSSH.is_shared') as device_is_shared:
            device_is_shared.return_value = True
            # A successful attachment has no output
            ssh_command.return_value = (0, self.blank_bytes, None)
            driver = self.devices[1].get_driver()

            driver.unshare()
            self.assertTrue(ssh_command.called)

    # TODO: Test for ssh failures
