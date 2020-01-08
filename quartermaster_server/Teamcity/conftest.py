import pytest

from Teamcity.models import TeamCityPool

job_id = 42
job_id_str = "Teamcity_ID=42"


@pytest.fixture
def make_teamcity_response():
    class MockTeamcityResponse(object):
        def __init__(self, data):
            self.data = data

        def json(self):
            return self.data

    def _make_teamcity_response(data):
        return MockTeamcityResponse(data)

    return _make_teamcity_response


@pytest.fixture
def sample_empty_tc_pool(sample_pool, monkeypatch):
    monkeypatch.setattr(TeamCityPool, 'get_teamcity_url', lambda _: "https://teamcity.example.com/some_path")
    return TeamCityPool.objects.create(pool=sample_pool, name='TEST_POOL_TEAMCITY')


@pytest.fixture
def sample_tc_pool_used(sample_shared_device, monkeypatch):
    monkeypatch.setattr(TeamCityPool, 'get_teamcity_url', lambda _: "https://teamcity.example.com/some_path")
    sample_shared_device.resource.used_for = job_id_str
    sample_shared_device.resource.save()
    return (TeamCityPool.objects.create(pool=sample_shared_device.resource.pool, name='TEST_POOL_TEAMCITY'),
            sample_shared_device.resource)


@pytest.fixture
def sample_tc_pool_unused(sample_unshared_device, monkeypatch):
    monkeypatch.setattr(TeamCityPool, 'get_teamcity_url', lambda _: "https://teamcity.example.com/some_path")
    return TeamCityPool.objects.create(pool=sample_unshared_device.resource.pool, name='TEST_POOL_TEAMCITY')
