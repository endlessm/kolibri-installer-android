import logging

from ..android_utils import make_service_foreground


class Application(object):
    def run(self):
        logging.info("Starting Kolibri task workers")

        # ensure the service stays running by "foregrounding" it with a persistent notification
        make_service_foreground("Kolibri service", "Running tasks.")

        _init_kolibri(skip_update=True)
        self.__run_worker()

    def __run_worker(self):
        from kolibri.core.tasks.main import initialize_workers
        from kolibri.core.tasks.main import job_storage
        from kolibri.core.analytics.utils import DEFAULT_PING_JOB_ID
        from kolibri.core.deviceadmin.tasks import SCH_VACUUM_JOB_ID

        # schedule the pingback job if not already scheduled
        if DEFAULT_PING_JOB_ID not in job_storage:
            from kolibri.core.analytics.utils import schedule_ping

            schedule_ping()

        # schedule the vacuum job if not already scheduled
        if SCH_VACUUM_JOB_ID not in job_storage:
            from kolibri.core.deviceadmin.tasks import schedule_vacuum

            schedule_vacuum()

        # Initialize the iceqube engine to handle queued tasks
        worker = initialize_workers()
        # Join the job checker thread to loop forever
        worker.job_checker.join()


def _init_kolibri(**kwargs):
    from ..kolibri_utils import init_kolibri

    init_kolibri(**kwargs)
