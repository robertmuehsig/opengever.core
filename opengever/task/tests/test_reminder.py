from datetime import date
from datetime import datetime
from datetime import timedelta
from ftw.testbrowser import browsing
from ftw.testing import freeze
from opengever.activity.dispatcher import NotificationDispatcher
from opengever.activity.model import Activity
from opengever.activity.model import Notification
from opengever.activity.roles import TASK_REMINDER_WATCHER_ROLE
from opengever.base.interfaces import IDataCollector
from opengever.task.activities import TaskReminderActivity
from opengever.task.reminder import ReminderOneDayBefore
from opengever.task.reminder import ReminderOneWeekBefore
from opengever.task.reminder import ReminderSameDay
from opengever.task.reminder.reminder import TaskReminder
from opengever.testing import IntegrationTestCase
from zope.component import getAdapter
import json
import pytz


class TestTaskReminder(IntegrationTestCase):

    features = ('activity', )

    def test_set_reminder_stores_reminder_for_current_user(self):
        self.login(self.regular_user)
        task_reminder = TaskReminder()
        task_reminder.set_reminder(self.task, ReminderOneDayBefore())

        self.assertEqual(
            ReminderOneDayBefore(),
            task_reminder.get_reminder(self.task))

        self.assertIsNone(task_reminder.get_reminder(
            self.task, user_id=self.dossier_responsible.getId()))

    def test_set_reminder_updates_existing_reminder(self):
        self.login(self.regular_user)
        task_reminder = TaskReminder()
        task_reminder.set_reminder(self.task, ReminderOneDayBefore())
        task_reminder.set_reminder(self.task, ReminderOneWeekBefore())

        self.assertEqual(
            ReminderOneWeekBefore(),
            task_reminder.get_reminder(self.task))

    def test_clear_reminder_removes_existing_reminder(self):
        self.login(self.regular_user)
        task_reminder = TaskReminder()

        task_reminder.set_reminder(self.task, ReminderOneDayBefore())
        task_reminder.set_reminder(
            self.task, ReminderOneDayBefore(),
            user_id=self.dossier_responsible.getId())

        task_reminder.clear_reminder(self.task)
        self.assertIsNone(task_reminder.get_reminder(self.task))

        self.assertEqual(
            ReminderOneDayBefore(),
            task_reminder.get_reminder(
                self.task, user_id=self.dossier_responsible.getId()))

    def test_create_reminder_notifications_does_nothing_if_there_are_no_reminders(self):
        self.login(self.regular_user)

        TaskReminder().create_reminder_notifications()

        self.assertEqual(0, Activity.query.count())
        self.assertEqual(0, Notification.query.count())

    def test_create_reminder_notifications_adds_notifications_for_each_reminder_if_reaching_remind_day(self):
        self.login(self.administrator)
        today = date.today()

        self.task.responsible = self.dossier_responsible.getId()
        self.task.issuer = self.regular_user.getId()
        self.task.deadline = today

        self.subtask.responsible = self.dossier_responsible.getId()
        self.subtask.issuer = self.regular_user.getId()
        self.subtask.deadline = today + timedelta(days=1)
        self.set_workflow_state('task-state-open', self.subtask)

        self.sequential_task.responsible = self.dossier_responsible.getId()
        self.sequential_task.issuer = self.regular_user.getId()
        self.sequential_task.deadline = today + timedelta(days=5)

        task_reminder = TaskReminder()

        with self.login(self.regular_user):
            task_reminder.set_reminder(self.task, ReminderSameDay())
            self.task.sync()

            task_reminder.set_reminder(self.sequential_task, ReminderSameDay())
            self.sequential_task.sync()

        with self.login(self.dossier_responsible):
            task_reminder.set_reminder(self.subtask, ReminderOneDayBefore())
            self.subtask.sync()

        with freeze(pytz.UTC.localize(datetime.combine(today, datetime.min.time()))):
            task_reminder.create_reminder_notifications()

        task_reminder_activities = Activity.query.filter(
            Activity.kind == TaskReminderActivity.kind)

        self.assertEqual(2, task_reminder_activities.count())

        notifications = []
        [notifications.extend(activity.notifications) for activity in task_reminder_activities]

        self.assertEqual(2, len(notifications))
        self.assertItemsEqual(
            [self.regular_user.getId(), self.dossier_responsible.getId()],
            [notification.userid for notification in notifications])

    def test_do_not_create_reminder_activity_if_task_is_finished(self):
        self.login(self.administrator)
        today = date.today()

        self.task.responsible = self.dossier_responsible.getId()
        self.task.issuer = self.regular_user.getId()
        self.task.deadline = today

        task_reminder = TaskReminder()

        with self.login(self.regular_user):
            task_reminder.set_reminder(self.task, ReminderSameDay())
            self.task.sync()

        def create_reminders_for_task_in_state(task, state):
            self.set_workflow_state(state, task)

            with freeze(pytz.UTC.localize(datetime.combine(today, datetime.min.time()))):
                task_reminder.create_reminder_notifications()

        create_reminders_for_task_in_state(self.task, 'task-state-tested-and-closed')
        create_reminders_for_task_in_state(self.task, 'task-state-resolved')

        task_reminder_activities = Activity.query.filter(
            Activity.kind == TaskReminderActivity.kind)

        self.assertEqual(0, task_reminder_activities.count())

        # Test if it's working at all
        create_reminders_for_task_in_state(self.task, 'task-state-open')

        task_reminder_activities = Activity.query.filter(
            Activity.kind == TaskReminderActivity.kind)

        self.assertEqual(1, task_reminder_activities.count())

    def test_reminder_notifications_respects_user_notification_settings(self):
        self.login(self.administrator)

        # Validate, that the user wants to get badge-notifications for task
        # reminders. This is essential for this test.
        user_settings = NotificationDispatcher().get_setting(
            'task-reminder', self.regular_user.getId())
        self.assertIn(TASK_REMINDER_WATCHER_ROLE,
                      user_settings.badge_notification_roles)

        today = date.today()

        self.task.responsible = self.dossier_responsible.getId()
        self.task.issuer = self.regular_user.getId()
        self.task.deadline = today

        task_reminder = TaskReminder()

        with self.login(self.regular_user):
            task_reminder.set_reminder(self.task, ReminderSameDay())
            self.task.sync()

        with freeze(pytz.UTC.localize(datetime.combine(today, datetime.min.time()))):
            task_reminder.create_reminder_notifications()

        notifications = Notification.query.by_user(self.regular_user.getId())
        self.assertEqual(1, notifications.count())

        notification = notifications.first()
        self.assertTrue(notification.is_badge)


class TestTaskReminderSelector(IntegrationTestCase):

    features = ('activity', )

    @browsing
    def test_displayed_on_in_progress_task(self, browser):
        self.login(self.regular_user, browser=browser)
        browser.open(self.task, view='tabbedview_view-overview')
        self.assertTrue(browser.css('#task-reminder-selector'))

    @browsing
    def test_not_displayed_on_resolved_task(self, browser):
        self.login(self.regular_user, browser=browser)
        browser.open(self.expired_task, view='tabbedview_view-overview')
        self.assertFalse(browser.css('#task-reminder-selector'))

    @browsing
    def test_init_state_keys(self, browser):
        self.login(self.regular_user, browser=browser)

        browser.visit(self.task, view='tabbedview_view-overview')
        init_state = self._get_init_state(browser)

        self.assertEqual(
            ['endpoint', 'reminder_options', 'error_msg'],
            init_state.keys())

    @browsing
    def test_init_state_endpoint(self, browser):
        self.login(self.regular_user, browser=browser)

        browser.visit(self.task, view='tabbedview_view-overview')
        init_state = self._get_init_state(browser)

        self.assertEqual(
            init_state.get('endpoint'),
            self.task.absolute_url() + '/@reminder')

    @browsing
    def test_init_state_selected_option(self, browser):
        self.login(self.regular_user, browser=browser)
        task_reminder = TaskReminder()

        browser.visit(self.task, view='tabbedview_view-overview')
        init_state = self._get_init_state(browser)
        selected_option = filter(lambda x: x.get('selected'),
                                 init_state.get('reminder_options'))

        self.assertEqual(1, len(selected_option))
        self.assertEqual(
            'no-reminder',
            selected_option[0].get('option_type'))

        task_reminder.set_reminder(self.task, ReminderOneDayBefore())
        browser.visit(self.task, view='tabbedview_view-overview')
        init_state = self._get_init_state(browser)
        selected_option = filter(lambda x: x.get('selected'),
                                 init_state.get('reminder_options'))

        self.assertEqual(1, len(selected_option))
        self.assertEqual(
            ReminderOneDayBefore.option_type,
            selected_option[0].get('option_type'))

    def _get_init_state(self, browser):
        return json.loads(
            browser.css('#task-reminder-selector').first.get('data-state'))


class TestTaskReminderTransport(IntegrationTestCase):

    def test_extract_all_task_reminders_for_all_responsible_representatives(self):
        self.login(self.regular_user)

        task_reminder = TaskReminder()
        task_reminder.set_reminder(
            self.task, ReminderOneDayBefore(), user_id=self.regular_user.id)
        task_reminder.set_reminder(
            self.task, ReminderOneDayBefore(), user_id=self.dossier_responsible.id)
        task_reminder.set_reminder(
            self.task, ReminderOneDayBefore(), user_id=self.secretariat_user.id)

        # single user
        collector = getAdapter(self.task, IDataCollector, name='task-reminders')
        self.assertEqual(
            {self.regular_user.id: {
                'option_type': ReminderOneDayBefore.option_type,
                'params': {}}},
            collector.extract())

        # inbox group
        self.task.responsible = 'inbox:fa'
        collector = getAdapter(self.task, IDataCollector, name='task-reminders')
        self.assertEqual(
            {self.secretariat_user.id: {
                'option_type': ReminderOneDayBefore.option_type,
                'params': {}}},
            collector.extract())

    def test_transport_reminders(self):
        self.login(self.regular_user)

        task_reminder = TaskReminder()
        task_reminder.set_reminder(
            self.task, ReminderOneDayBefore(), user_id=self.regular_user.id)

        collector = getAdapter(self.task, IDataCollector, name='task-reminders')
        data = collector.extract()

        self.assertEqual({}, TaskReminder().get_reminders(self.subtask))
        collector = getAdapter(self.subtask, IDataCollector, name='task-reminders')
        collector.insert(data)
        self.assertEqual(
            {self.regular_user.id: ReminderOneDayBefore()},
            TaskReminder().get_reminders(self.subtask))
