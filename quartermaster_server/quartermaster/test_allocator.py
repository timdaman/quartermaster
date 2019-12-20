import json
from datetime import datetime
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils.timezone import utc

from data.models import Pool, Resource, Device
from quartermaster import allocator


class AllocatorTestSuite(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.user = User.objects.create_superuser(username="TEST_USER_ALLOCATE",
                                                 email="not_real@example.com",
                                                 password="lolSecret")
        cls.pool = Pool.objects.create(name='TEST_POOL_ALLOCATE')
        cls.resource = Resource.objects.create(pool=cls.pool, name=f"RESOURCE_1_ALLOCATE")
        device_config = {'host': '127.0.0.3', 'bus_id': '1-11'}
        cls.device = Device.objects.create(resource=cls.resource, driver='UsbipOverSSH',
                                           config_json=json.dumps(device_config), name=f"Device 1-11")
        super().setUpClass()

    def setUp(self) -> None:
        self.resource.user = None
        self.resource.used_for = ''
        self.resource.save()

    def test_make_reservation(self):
        with patch('driver_UsbipOverSSH.UsbipOverSSH.share') as share_devices:
            allocator.make_reservation(self.resource, self.user, used_for='TEST')
            self.assertEqual(share_devices.call_count, 1)
            self.resource.refresh_from_db()
            self.assertEquals(self.resource.user, self.user)

    def test_update_reservation(self):
        old_timestamp = datetime(year=200, month=1, day=1, tzinfo=utc)
        self.resource.last_check_in = old_timestamp
        self.resource.user = self.user
        self.resource.save()

        allocator.update_reservation(self.resource)

        self.resource.refresh_from_db()
        self.assertNotEqual(self.resource.last_check_in, old_timestamp)

    def test_release_reservation(self):
        with patch('driver_UsbipOverSSH.UsbipOverSSH.unshare') as unshare_devices:
            self.resource.user = self.user
            self.resource.save()

            allocator.release_reservation(self.resource)
            self.assertEqual(unshare_devices.call_count, 1)
            self.resource.refresh_from_db()
            self.assertIsNone(self.resource.user)
