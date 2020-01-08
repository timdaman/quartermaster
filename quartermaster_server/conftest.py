import json

import pytest

from UsbipOverSSH import UsbipOverSSH
from UsbipOverSSH.tests import sample_host, sample_bus_id
from data.models import Device, Resource, Pool


@pytest.fixture()
def sample_pool():
    return Pool.objects.create(name='TEST_POOL_DEVICE_MANAGER')


@pytest.fixture()
def sample_shared_resource(sample_pool, admin_user):
    pool = sample_pool
    return Resource.objects.create(pool=pool, name=f"RESOURCE_1", user=admin_user)


@pytest.fixture()
def sample_unshared_resource(sample_pool, admin_user):
    pool = sample_pool
    return Resource.objects.create(pool=pool, name=f"RESOURCE_2", user=None)


@pytest.fixture()
def sample_shared_device(sample_shared_resource):
    config_json = {'host': sample_host, 'bus_id': sample_bus_id}
    return Device.objects.create(resource=sample_shared_resource, driver=UsbipOverSSH.__name__,
                                 config_json=json.dumps(config_json), name=f"Device usbip {sample_bus_id}")


@pytest.fixture()
def sample_unshared_device(sample_unshared_resource):
    config_json = {'host': sample_host, 'bus_id': '20-20'}
    return Device.objects.create(resource=sample_unshared_resource, driver=UsbipOverSSH.__name__,
                                 config_json=json.dumps(config_json), name=f"Device usbip {sample_bus_id}")
