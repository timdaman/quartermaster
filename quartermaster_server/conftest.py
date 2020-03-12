import json

import pytest

from UsbipOverSSH import UsbipOverSSH
from UsbipOverSSH.tests import sample_hostname, sample_bus_id
from data.models import Device, Resource, Pool, RemoteHost


@pytest.fixture()
def sample_remote_host():
    # Test key information, not used anywhere else.
    return RemoteHost.objects.create(address='example.com', communicator="SSH",
                                     config_json='{'
                                                 '"host_key": "AAAAC3NzaC1lZDI1NTE5AAAAICmd8eZ0AP9SfNA7YSNJE3PGGiA2O8XD971aTyUOgB3r", '
                                                 '"host_key_type": "ssh-ed25519", '
                                                 '"username": "test_user", '
                                                 '"private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW\nQyNTUxOQAAACApnfHmdAD/UnzQO2EjSRNzxhogNjvFw/e9Wk8lDoAd6wAAAJBwBV0RcAVd\nEQAAAAtzc2gtZWQyNTUxOQAAACApnfHmdAD/UnzQO2EjSRNzxhogNjvFw/e9Wk8lDoAd6w\nAAAEBnMObmKBMzneox6+iND8x8fXaib5ax5WF1TS2bd4xioimd8eZ0AP9SfNA7YSNJE3PG\nGiA2O8XD971aTyUOgB3rAAAADHJvb3RAbnVjLTE1MQE=\n-----END OPENSSH PRIVATE KEY-----", '
                                                 '"private_key_type": "Ed25519"'
                                                 '}')


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
def sample_shared_device(sample_shared_resource, sample_remote_host):
    config_json = {'host': sample_hostname, 'bus_id': sample_bus_id}
    return Device.objects.create(resource=sample_shared_resource, driver=UsbipOverSSH.__name__,
                                 host=sample_remote_host, config_json=json.dumps(config_json),
                                 name=f"Device usbip {sample_bus_id}")


@pytest.fixture()
def sample_unshared_device(sample_unshared_resource, sample_remote_host):
    config_json = {'host': sample_hostname, 'bus_id': '20-20'}
    return Device.objects.create(resource=sample_unshared_resource, driver=UsbipOverSSH.__name__,
                                 host=sample_remote_host, config_json=json.dumps(config_json),
                                 name=f"Device usbip {sample_bus_id}")
