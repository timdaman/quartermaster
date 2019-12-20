import json

from django.contrib.auth.models import User
from django.test import TestCase, RequestFactory
# Create your tests here.
from django.urls import reverse

from data.models import Pool, Resource, Device


class TestViews(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.device_driver = 'VirtualHere'
        cls.user = User.objects.create_superuser(username="TEST_USER_API",
                                                 email="not_real@example.com",
                                                 password="lolSecret")
        cls.pool = Pool.objects.create(name='TEST_POOL_API')
        cls.resource = Resource.objects.create(pool=cls.pool, name=f"RESOURCE_1_API")
        device_config = {'hub_address': 'hub_address', 'device_address': 'device_address'}
        cls.device = Device.objects.create(resource=cls.resource, driver=cls.device_driver,
                                           config_json=json.dumps(device_config), name=f"DeviceAPI1-11")
        cls.rf = RequestFactory()

        super().setUpClass()
