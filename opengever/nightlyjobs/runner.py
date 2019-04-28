from datetime import datetime
from datetime import timedelta
from opengever.base.sentry import log_msg_to_sentry
from opengever.nightlyjobs.interfaces import INightlyJobProvider
from opengever.nightlyjobs.interfaces import INightlyJobsSettings
from plone import api
from zope.component import getAdapters
from zope.globalrequest import getRequest
import psutil
import transaction


class TimeWindowExceeded(Exception):

    message = "Time window exceeded. Window: {}-{}. "\
              "Current time: {:%H:%M}"

    def __init__(self, now, start, end):
        self.current_time = now
        self.start = start
        self.end = end
        message = self.message.format(start, end, self.current_time)
        super(TimeWindowExceeded, self).__init__(message)


class SystemLoadCritical(Exception):

    message = "System overloaded.\n"\
              "Available memory: {}MB; limit: {}MB\n"\
              "Percent memory: {}; limit: {}"

    def __init__(self, load, limits):
        self.load = load
        self.limits = limits
        message = self.message.format(load['virtual_memory_available'] / 1024 / 1024,
                                      limits['virtual_memory_available'] / 1024 / 1024,
                                      load['virtual_memory_percent'],
                                      limits['virtual_memory_percent'])
        super(SystemLoadCritical, self).__init__(message)


class NightlyJobRunner(object):
    """ This class is used to execute nightly jobs.
    It will try to execute all jobs provided by the registered
    nightly job providers (named multiadapters of INightlyJobProvider).
    It will stop execution when not in the defined timeframe or when
    the system load is too high.
    """

    LOAD_LIMITS = {'virtual_memory_available': 100 * 1024 *1024,
                   'virtual_memory_percent': 95}

    def __init__(self):
        # retrieve window start and end times
        self.window_start = api.portal.get_registry_record(
            'start_time', interface=INightlyJobsSettings)
        self.window_end = api.portal.get_registry_record(
            'end_time', interface=INightlyJobsSettings)

        # retrieve all providers
        self.job_providers = {name: provider for name, provider
                              in getAdapters([api.portal.get(), getRequest()],
                                             INightlyJobProvider)}

        self.initial_jobs_count = {name: len(provider) for name, provider
                                   in self.job_providers.items()}

    def execute_pending_jobs(self, early_check=True):
        if early_check:
            # When invoked from a cron job, we first check that time window
            # and system load are acceptable. Otherwise cron job is misconfigured.
            self.interrupt_if_necessary()

        for provider in self.job_providers.values():
            for job in provider:
                try:
                    self.interrupt_if_necessary()
                    provider.run_job(job, self.interrupt_if_necessary)
                except (TimeWindowExceeded, SystemLoadCritical) as exc:
                    transaction.abort()
                    message = self.format_early_abort_message(exc)
                    self.log_to_sentry(message)
                    return exc
                transaction.commit()

    def interrupt_if_necessary(self):
        now = datetime.now().time()
        if not self.check_in_time_window(now):
            raise TimeWindowExceeded(now, self.window_start, self.window_end)

        load = self.get_system_load()
        if self.check_system_overloaded(load):
            raise SystemLoadCritical(load, self.LOAD_LIMITS)

    def check_in_time_window(self, now):
        current_time = timedelta(hours=now.hour, minutes=now.minute)
        if current_time - self.window_start < timedelta():
            current_time += timedelta(hours=24)
        return self.window_start < current_time < self.window_end

    def _is_memory_full(self, load):
        return (load['virtual_memory_available'] < self.LOAD_LIMITS['virtual_memory_available']
                or load['virtual_memory_percent'] > self.LOAD_LIMITS['virtual_memory_percent'])

    def get_system_load(self):
        return {'virtual_memory_available': psutil.virtual_memory().available,
                'virtual_memory_percent': psutil.virtual_memory().percent}

    def check_system_overloaded(self, load):
        return self._is_memory_full(load)

    def format_early_abort_message(self, exc):
        info = "\n".join("{} executed {} out of {} jobs".format(
                            provider_name,
                            self.get_executed_jobs_count(provider_name),
                            self.get_initial_jobs_count(provider_name))
                         for provider_name, provider in self.job_providers.items())
        return "{}\n{}".format(repr(exc), info)

    def log_to_sentry(self, message):
        log_msg_to_sentry(message, request=getRequest())

    def get_initial_jobs_count(self, provider_name=None):
        if not provider_name:
            return sum(self.initial_jobs_count.values())
        return self.initial_jobs_count.get(provider_name)

    def get_remaining_jobs_count(self, provider_name=None):
        if not provider_name:
            return sum(len(provider) for provider in self.job_providers.values())
        return len(self.job_providers[provider_name])

    def get_executed_jobs_count(self, provider_name=None):
        return (self.get_initial_jobs_count(provider_name) -
                self.get_remaining_jobs_count(provider_name))
