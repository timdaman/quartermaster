import json
import logging
from typing import Optional, List

from requests import Response

from Teamcity.config import TEAMCITY_HOST, TEAMCITY, TEAMCITY_BLOCKED_JOB_PREFIX, TEAMCITY_USER
from Teamcity.models import TeamCityPool
from data.models import Resource
from quartermaster.allocator import make_reservation, release_reservation

logger = logging.getLogger(__name__)


def teamcity_request(url: str, data: Optional[str] = None) -> Response:
    headers = {'Accept': 'application/json',
               'Content-Type': 'application/json',
               'Origin': TEAMCITY_HOST}
    if data:
        response = TEAMCITY.put(url, headers=headers, data=data)
    else:
        response = TEAMCITY.get(url, headers=headers)

    if 200 <= response.status_code < 300:
        return response

    message = f"Unexpected response from TeamCity. RC={response.status_code} body={response.content}"
    logger.error(message)
    raise IOError(message)


def teamcity_job_is_done(job_id: int) -> bool:
    # Check results
    job_status = teamcity_request(f"{TEAMCITY_HOST}/app/rest/2018.1/builds/id:{job_id}/?fields=state")
    return job_status.json()['state'] == 'finished'


def teamcity_blocked_jobs() -> List[dict]:
    queue_status = teamcity_request(f"{TEAMCITY_HOST}/app/rest/2018.1/buildQueue?fields=build(id,waitReason)")
    blocked = []
    for queued_build in queue_status.json()['build']:
        if 'waitReason' in queued_build and queued_build['waitReason'].startswith(TEAMCITY_BLOCKED_JOB_PREFIX):
            blocked.append(queued_build)
    return blocked


def teamcity_make_reservation(tc_pool: TeamCityPool, job_id: int):
    used_for = f"Teamcity_ID={job_id}"
    suitable_resources_qs = Resource.objects.filter(pool__teamcitypool=tc_pool)

    # Stop if we already have a reservation for the this build
    if suitable_resources_qs.filter(used_for=used_for, user=TEAMCITY_USER).exists():
        return

    selected_resource = suitable_resources_qs.filter(user=None).first()

    if selected_resource is None:  # No resources available
        logger.warning(f"Could not find unused tc_name={tc_pool.name} resource_pool={tc_pool.pool.name} resource for "
                       f"build {job_id}")
        return

    # We have everything we need, let make a reservation

    # Note: Race condition as this data could be updated before reinserting it
    teamcity_data = teamcity_request(f'{tc_pool.shared_resource_url}/properties/quota').json()
    current_quota = int(teamcity_data['value'])
    teamcity_data['value'] = current_quota + 1

    logger.info(f"Reserving {tc_pool.name} for build {job_id}, new quota is {teamcity_data['value']}")
    make_reservation(resource=selected_resource, user=TEAMCITY_USER, used_for=used_for)
    try:
        teamcity_request(f'{tc_pool.shared_resource_url}/properties/quota', data=json.dumps(teamcity_data))
    except IOError as e:
        logger.error(f"Error incrementing quota for {tc_pool.name}, "
                     f"rolling back reservation for {selected_resource}: {e}")
        release_reservation(resource=selected_resource)
        raise e


def teamcity_release_reservation(resource: Resource):
    tc_pool = resource.pool.teamcitypool
    teamcity_data = teamcity_request(f'{tc_pool.shared_resource_url}/properties/quota').json()
    current_quota = int(teamcity_data['value'])
    if current_quota > 0:
        logger.info(
            f"Releasing reserving of {tc_pool.name} for {resource.used_for}, new quota is {teamcity_data['value']}")

        teamcity_data['value'] = current_quota - 1
        teamcity_request(f'{tc_pool.shared_resource_url}/properties/quota', data=json.dumps(teamcity_data))
    else:
        logger.error(f"Attempting to remove TeamCity reservation from '{resource.used_for}' but the shared quota "
                     f"is already {current_quota}, setting to 0 instead")
        if current_quota < 0:
            teamcity_data['value'] = '0'
            teamcity_request(f'{tc_pool.shared_resource_url}/properties/quota', data=json.dumps(teamcity_data))
    release_reservation(resource=resource)
