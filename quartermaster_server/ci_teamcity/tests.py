import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from ci_teamcity import tc_allocator
from ci_teamcity.models import TeamCityPool
from data.models import Pool, Resource, Device


# Create your tests here.


class MockTeamcityResponse(object):
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


class AllocatorTestSuite(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.user = User.objects.create_superuser(username="TEST_USER_TEAMCITY",
                                                 email="not_real@example.com",
                                                 password="lolSecret")
        cls.pool = Pool.objects.create(name='TEST_POOL_TEAMCITY')
        cls.resource = Resource.objects.create(pool=cls.pool, name=f"RESOURCE_1_TEAMCITY")
        device_config = {'host': '127.0.0.4', 'bus_id': '1-111'}
        cls.device = Device.objects.create(resource=cls.resource, config_json=json.dumps(device_config),
                                           driver='UsbipOverSSH', name=f"Device 1-111")
        cls.tc_pool = TeamCityPool.objects.create(name='UNIT_TESTING_POOL', pool=cls.pool)

        super().setUpClass()

    def setUp(self) -> None:
        self.resource.user = None
        self.resource.use_password = ''
        self.resource.save()

    def test_teamcity_job_is_done(self):
        with patch('ci_teamcity.tc_allocator.teamcity_request') as teamcity_request:
            teamcity_request.return_value = MockTeamcityResponse({"state": "finished"})
            result = tc_allocator.teamcity_job_is_done(1)
            self.assertTrue(teamcity_request.called)
            self.assertTrue(result)

    def test_teamcity_job_is_done_not(self):
        with patch('ci_teamcity.tc_allocator.teamcity_request') as teamcity_request:
            teamcity_request.return_value = MockTeamcityResponse({"state": "queued"})
            result = tc_allocator.teamcity_job_is_done(1)
            self.assertTrue(teamcity_request.called)
            self.assertFalse(result)

    def test_teamcity_blocked_jobs(self):
        with patch('ci_teamcity.tc_allocator.teamcity_request') as teamcity_request:
            teamcity_request.return_value = MockTeamcityResponse({
                "count": 1,
                "href": "/app/rest/2018.1/buildQueue",
                "build": [
                    {
                        "id": 600999,
                        "buildTypeId": "Example_Build",
                        "state": "queued",
                        "branchName": "3195/head",
                        "href": "/app/rest/2018.1/buildQueue/id:600999",
                        "webUrl": "https://teamcity.example.com/viewQueued.html?itemId=600999",
                        "waitReason": "Build is waiting for the following resource to become available: TEST_VALUE"
                    }
                ]
            })

            result = tc_allocator.teamcity_blocked_jobs()
            self.assertTrue(teamcity_request.called)
            self.assertEqual(len(result), 1)

    def test_teamcity_blocked_jobs_only_ignored(self):
        with patch('ci_teamcity.tc_allocator.teamcity_request') as teamcity_request:
            teamcity_request.return_value = MockTeamcityResponse({
                "count": 1,
                "href": "/app/rest/2018.1/buildQueue",
                "build": [
                    {
                        "id": 600999,
                        "buildTypeId": "Example_Build",
                        "state": "queued",
                        "branchName": "3195/head",
                        "href": "/app/rest/2018.1/buildQueue/id:600999",
                        "webUrl": "https://teamcity.example.com/viewQueued.html?itemId=600999"
                    }
                ]
            })

            result = tc_allocator.teamcity_blocked_jobs()
            self.assertTrue(teamcity_request.called)
            self.assertListEqual(result, [])

    def test_teamcity_make_reservation(self):
        first_tc_response = MockTeamcityResponse({
            "name": "value",
            "value": "1"
        })
        # Not examined so it can be blank
        second_tc_response = MockTeamcityResponse({})

        with patch('ci_teamcity.tc_allocator.teamcity_request') as teamcity_request, \
                patch('ci_teamcity.tc_allocator.make_reservation') as share_devices:
            teamcity_request.side_effect = [first_tc_response, second_tc_response]
            tc_allocator.teamcity_make_reservation(tc_pool=self.tc_pool, job_id=42)

            self.assertEqual(teamcity_request.call_count, 2)
            self.assertEqual(share_devices.call_count, 1)

    def test_teamcity_make_reservation_none_available(self):
        first_tc_response = MockTeamcityResponse({
            "name": "value",
            "value": "0"
        })

        Resource.objects.create(pool=self.pool, name=f"RESOURCE_3_TEAMCITY")
        empty_pool = Pool.objects.create(name='TEST_POOL_TEAMCITY2')
        empty_pool_tc = TeamCityPool.objects.create(name='UNIT_TESTING_POOL2', pool=empty_pool)

        with patch('ci_teamcity.tc_allocator.teamcity_request') as teamcity_request:
            tc_allocator.teamcity_make_reservation(empty_pool_tc, 42)
            
            self.assertEqual(teamcity_request.call_count, 0)
