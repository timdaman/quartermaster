from unittest.mock import patch

import pytest

from Teamcity import tc_allocator
from Teamcity.conftest import job_id
# Create your tests here.
from UsbipOverSSH import UsbipOverSSH


def test_teamcity_job_is_done(make_teamcity_response):
    with patch('Teamcity.tc_allocator.teamcity_request') as teamcity_request:
        teamcity_request.return_value = make_teamcity_response({"state": "finished"})
        result = tc_allocator.teamcity_job_is_done(1)
        assert 1 == teamcity_request.call_count
        assert result


def test_teamcity_job_is_done_not(make_teamcity_response):
    with patch('Teamcity.tc_allocator.teamcity_request') as teamcity_request:
        teamcity_request.return_value = make_teamcity_response({"state": "queued"})
        result = tc_allocator.teamcity_job_is_done(1)
        assert 1 == teamcity_request.call_count
        assert not result


def test_teamcity_blocked_jobs(make_teamcity_response):
    with patch('Teamcity.tc_allocator.teamcity_request') as teamcity_request:
        teamcity_request.return_value = make_teamcity_response({
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
        assert 1 == teamcity_request.call_count
        assert 1 == len(result)


def test_teamcity_blocked_jobs_only_ignored(make_teamcity_response):
    with patch('Teamcity.tc_allocator.teamcity_request') as teamcity_request:
        teamcity_request.return_value = make_teamcity_response({
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
        assert 1 == teamcity_request.call_count
        assert 0 == len(result)


@pytest.mark.django_db(transaction=True)
def test_teamcity_make_reservation(make_teamcity_response, sample_tc_pool_unused, monkeypatch, admin_user):
    first_tc_response = make_teamcity_response({
        "name": "value",
        "value": "1"
    })
    # Not examined so it can be blank
    second_tc_response = make_teamcity_response({})

    monkeypatch.setattr('Teamcity.tc_allocator.TEAMCITY_USER', admin_user)

    with patch('Teamcity.tc_allocator.teamcity_request') as teamcity_request:
        monkeypatch.setattr(UsbipOverSSH, 'get_share_state', lambda _: False)
        monkeypatch.setattr(UsbipOverSSH, 'start_sharing', lambda _: None)
        teamcity_request.side_effect = [first_tc_response, second_tc_response]
        tc_allocator.teamcity_make_reservation(tc_pool=sample_tc_pool_unused, job_id=job_id)

        assert 2 == teamcity_request.call_count


@pytest.mark.django_db
def test_teamcity_make_reservation_none_available(sample_empty_tc_pool, monkeypatch):
    with patch('Teamcity.tc_allocator.teamcity_request') as teamcity_request:
        monkeypatch.setattr(UsbipOverSSH, 'get_share_state', lambda _: True)
        tc_allocator.teamcity_make_reservation(sample_empty_tc_pool, job_id)
        assert 0 == teamcity_request.call_count


@pytest.mark.django_db(transaction=True)
def test_teamcity_make_reservation_duplicate(sample_tc_pool_used, admin_user, monkeypatch):
    with patch('Teamcity.tc_allocator.teamcity_request') as teamcity_request:
        monkeypatch.setattr('Teamcity.tc_allocator.TEAMCITY_USER', admin_user)
        tc_allocator.teamcity_make_reservation(tc_pool=sample_tc_pool_used[0], job_id=job_id)
        assert 0 == teamcity_request.call_count


@pytest.mark.django_db(transaction=True)
def test_teamcity_release_reservation(make_teamcity_response, sample_tc_pool_used, monkeypatch):
    first_tc_response = make_teamcity_response({
        "name": "value",
        "value": "1"
    })
    # Not examined so it can be blank
    second_tc_response = make_teamcity_response({})
    assert '' != sample_tc_pool_used[1].used_for
    with patch('Teamcity.tc_allocator.teamcity_request') as teamcity_request:
        teamcity_request.side_effect = [first_tc_response, second_tc_response]
        monkeypatch.setattr(UsbipOverSSH, 'get_share_state', lambda _: False)
        tc_allocator.teamcity_release_reservation(resource=sample_tc_pool_used[1])
        assert 2 == teamcity_request.call_count
        assert '' == sample_tc_pool_used[1].used_for


@pytest.mark.django_db(transaction=True)
def test_teamcity_release_reservation_zero(make_teamcity_response, sample_tc_pool_used, monkeypatch):
    first_tc_response = make_teamcity_response({
        "name": "value",
        "value": "0"
    })
    # Not examined so it can be blank
    second_tc_response = make_teamcity_response({})
    assert '' != sample_tc_pool_used[1].used_for
    with patch('Teamcity.tc_allocator.teamcity_request') as teamcity_request:
        teamcity_request.side_effect = [first_tc_response, second_tc_response]
        monkeypatch.setattr(UsbipOverSSH, 'get_share_state', lambda _: False)
        tc_allocator.teamcity_release_reservation(resource=sample_tc_pool_used[1])
        assert 1 == teamcity_request.call_count
        assert '' == sample_tc_pool_used[1].used_for


@pytest.mark.django_db(transaction=True)
def test_teamcity_release_reservation_negative(make_teamcity_response, sample_tc_pool_used, monkeypatch):
    # In Teamcity -1 means infinite quota. In our use case this is never desired so we should reset to zero to
    # prevent problems
    first_tc_response = make_teamcity_response({
        "name": "value",
        "value": "-1"
    })
    # Not examined so it can be blank
    second_tc_response = make_teamcity_response({})
    assert '' != sample_tc_pool_used[1].used_for
    with patch('Teamcity.tc_allocator.teamcity_request') as teamcity_request:
        teamcity_request.side_effect = [first_tc_response, second_tc_response]
        monkeypatch.setattr(UsbipOverSSH, 'get_share_state', lambda _: False)
        tc_allocator.teamcity_release_reservation(resource=sample_tc_pool_used[1])
        assert 2 == teamcity_request.call_count
        assert '' == sample_tc_pool_used[1].used_for
