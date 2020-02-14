from django.conf import settings

from .apps import TeamcityConfig

# Disable teamcity support if not "installed"
if __package__ in settings.INSTALLED_APPS:
    import logging

    from huey import crontab
    from huey.contrib.djhuey import lock_task, db_periodic_task
    from data.models import Resource
    from .tc_allocator import \
        teamcity_job_is_done, \
        teamcity_blocked_jobs, \
        TEAMCITY_BLOCKED_JOB_PREFIX, \
        teamcity_make_reservation, teamcity_release_reservation
    from .config import TEAMCITY_USER
    from .models import TeamCityPool

    logger = logging.getLogger(__name__)

    if TEAMCITY_USER is not None:

        @db_periodic_task(crontab(minute='*'))
        @lock_task('monitor_teamcity_reservations')
        def manage_teamcity_reservations():
            for resource in Resource.objects.filter(user=TEAMCITY_USER):
                # Example of used_for is "Teamcity_ID=123"
                job_id = resource.used_for[len('Teamcity_ID='):]
                job_id = int(job_id)
                if teamcity_job_is_done(job_id):
                    logger.info(f"TeamCity job {job_id} completed, removing reservation for {str(resource)}")
                    teamcity_release_reservation(resource)
    
    
        @db_periodic_task(crontab(minute='*'))
        @lock_task('monitor_teamcity_queue')
        def monitor_teamcity_queue():
            blocked_jobs = teamcity_blocked_jobs()
            for job in blocked_jobs:
                teamcity_parameter = job['waitReason'][len(TEAMCITY_BLOCKED_JOB_PREFIX):]
                try:
                    tc_pool = TeamCityPool.objects.get(name=teamcity_parameter)
                except TeamCityPool.DoesNotExist:
                    continue
    
                logger.info(f"TeamCity job {job['id']} waiting for {tc_pool.name}, trying to add reservation")
                teamcity_make_reservation(tc_pool, job['id'])
