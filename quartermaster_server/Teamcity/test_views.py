from unittest.mock import patch, MagicMock

import pytest
from django.urls import reverse

import Teamcity
from . import views, conftest


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("method, expected_rc", (('GET', 302), ('POST', 302), ('PATCH', 302)))
def test_build_reservation_redirected(method: str, expected_rc: int, rf, sample_tc_pool_used):
    expected_dest = reverse('api:show_reservation', kwargs={'resource_pk': sample_tc_pool_used[1].pk})
    request = rf.request(method=method)
    response = views.build_reservation(request, conftest.job_id)
    assert expected_rc == response.status_code
    assert expected_dest == response.url


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("method, expected_rc", (('get', 302), ('post', 302), ('patch', 302)))
def test_build_reservation_redirected(method: str, expected_rc: int, rf, sample_tc_pool_used):
    expected_dest = reverse('api:show_reservation', kwargs={'resource_pk': sample_tc_pool_used[1].pk})
    request_method = getattr(rf, method)
    request = request_method('/')
    response = views.build_reservation(request, conftest.job_id)
    assert expected_rc == response.status_code
    assert expected_dest == response.url


@pytest.mark.django_db(transaction=True)
def test_build_reservation_delete(rf, sample_tc_pool_used, monkeypatch):
    pool, resource = sample_tc_pool_used
    assert resource.used_for != ''
    mock = MagicMock()
    monkeypatch.setattr(views, 'teamcity_release_reservation', mock)
    request = rf.delete('/')
    response = views.build_reservation(request, conftest.job_id)
    assert response.status_code == 204
    assert mock.call_count == 1
