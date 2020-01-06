from datetime import datetime
from unittest.mock import MagicMock

import pytest
# from quartermaster_server.data.models import Pool, Resource, Device
from pytz import utc

from data.models import Resource
from quartermaster import allocator


@pytest.mark.django_db(transaction=True)
def test_make_reservation(admin_user, sample_unshared_resource: Resource, monkeypatch):
    assert sample_unshared_resource.user != admin_user
    mock_for_all_devices = MagicMock()
    monkeypatch.setattr(allocator, 'for_all_devices', mock_for_all_devices)
    allocator.make_reservation(sample_unshared_resource, admin_user, used_for='TEST')
    assert mock_for_all_devices.call_count == 1
    assert 'share' in mock_for_all_devices.call_args[0]
    sample_unshared_resource.refresh_from_db(fields=['user'])
    assert sample_unshared_resource.user == admin_user


@pytest.mark.django_db(transaction=True)
def test_update_reservation(sample_shared_resource: Resource):
    old_timestamp = datetime(year=200, month=1, day=1, tzinfo=utc)
    sample_shared_resource.last_check_in = old_timestamp
    sample_shared_resource.save()

    allocator.update_reservation(sample_shared_resource)
    sample_shared_resource.refresh_from_db(fields=['last_check_in'])
    assert sample_shared_resource.last_check_in != old_timestamp


@pytest.mark.django_db(transaction=True)
def test_release_reservation(sample_shared_resource, monkeypatch):
    mock_for_all_devices = MagicMock()
    monkeypatch.setattr(allocator, 'for_all_devices', mock_for_all_devices)

    allocator.release_reservation(sample_shared_resource)

    assert mock_for_all_devices.call_count == 1
    assert 'unshare' in mock_for_all_devices.call_args[0]
    sample_shared_resource.refresh_from_db(fields=['user'])
    assert sample_shared_resource.user is None
