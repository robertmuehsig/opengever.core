from opengever.core.debughelpers import all_plone_sites
from opengever.core.debughelpers import setup_plone
from opengever.nightlyjobs.runner import nightly_jobs_feature_enabled
from opengever.nightlyjobs.runner import NightlyJobRunner
import logging


logger = logging.getLogger('opengever.nightlyjobs')


def run_nightly_jobs_handler(app, args):
    # Set Zope's default StreamHandler's level to INFO (default is WARNING)
    # to make sure send_digests()'s output gets logged on console
    stream_handler = logger.root.handlers[0]
    stream_handler.setLevel(logging.INFO)
    logger.setLevel(logging.INFO)

    for plone_site in all_plone_sites(app):
        setup_plone(plone_site)
        invoke_nightly_job_runner(plone_site)


def invoke_nightly_job_runner(plone_site):
    if not nightly_jobs_feature_enabled():
        logger.info('Nightly jobs feature is not enabled in registry - '
                    'not running any jobs for %r' % plone_site)
        return

    runner = NightlyJobRunner(setup_own_task_queue=True)
    logger.info('Found {} providers: {}'.format(len(runner.job_providers),
                                                runner.job_providers.keys()))
    logger.info('Number of jobs: {}'.format(runner.get_initial_jobs_count()))

    exc = runner.execute_pending_jobs()
    if exc:
        logger.info('Early abort')
        logger.info(runner.format_early_abort_message(exc))

    logger.info('Successfully executed {} jobs'.format(runner.get_executed_jobs_count()))

    if runner.get_remaining_jobs_count() == 0:
        logger.info('No jobs remaining')
    else:
        logger.info('{} jobs remaining'.format(runner.get_remaining_jobs_count()))
