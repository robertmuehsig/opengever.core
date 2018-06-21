from datetime import date
from ftw.builder import Builder
from ftw.builder import create
from ftw.testbrowser import browsing
from opengever.activity.model.activity import Activity
from opengever.base.oguid import Oguid
from opengever.tasktemplates.interfaces import IFromSequentialTasktemplate
from opengever.testing import IntegrationTestCase
from plone import api
from zope.interface import alsoProvides


class TestSequentialTaskProcess(IntegrationTestCase):

    features = ('activity', )

    def test_starts_next_task_when_task_gets_resolved(self):
        self.login(self.regular_user)

        # create subtask
        subtask2 = create(Builder('task')
                          .within(self.task)
                          .having(responsible_client='fa',
                                  responsible=self.regular_user.getId(),
                                  issuer=self.dossier_responsible.getId(),
                                  task_type='correction',
                                  deadline=date(2016, 11, 1))
                          .in_state('task-state-planned'))

        self.set_workflow_state('task-state-in-progress', self.subtask)
        alsoProvides(self.subtask, IFromSequentialTasktemplate)
        alsoProvides(subtask2, IFromSequentialTasktemplate)
        self.task.set_tasktemplate_order([self.subtask, subtask2])

        api.content.transition(
            obj=self.subtask, transition='task-transition-in-progress-resolved')

        self.assertEquals(
            'task-state-resolved', api.content.get_state(self.subtask))
        self.assertEquals(
            'task-state-open', api.content.get_state(subtask2))

    def test_starts_next_task_when_task_gets_closed(self):
        self.login(self.regular_user)

        # create subtask
        subtask2 = create(Builder('task')
                          .within(self.task)
                          .having(responsible_client='fa',
                                  responsible=self.regular_user.getId(),
                                  issuer=self.dossier_responsible.getId(),
                                  task_type='correction',
                                  deadline=date(2016, 11, 1))
                          .in_state('task-state-planned'))

        self.set_workflow_state('task-state-in-progress', self.subtask)
        alsoProvides(self.subtask, IFromSequentialTasktemplate)
        alsoProvides(subtask2, IFromSequentialTasktemplate)
        self.task.set_tasktemplate_order([self.subtask, subtask2])
        self.subtask.task_type = 'direct-execution'
        api.content.transition(
            obj=self.subtask, transition='task-transition-in-progress-tested-and-closed')

        self.assertEquals(
            'task-state-tested-and-closed', api.content.get_state(self.subtask))
        self.assertEquals(
            'task-state-open', api.content.get_state(subtask2))

    def test_starts_next_task_when_task_gets_skipped(self):
        self.login(self.dossier_responsible)

        # create subtask
        subtask2 = create(Builder('task')
                          .within(self.task)
                          .having(responsible_client='fa',
                                  responsible=self.regular_user.getId(),
                                  issuer=self.dossier_responsible.getId(),
                                  task_type='correction',
                                  deadline=date(2016, 11, 1))
                          .in_state('task-state-planned'))

        self.set_workflow_state('task-state-planned', self.subtask)
        alsoProvides(self.subtask, IFromSequentialTasktemplate)
        alsoProvides(subtask2, IFromSequentialTasktemplate)
        self.task.set_tasktemplate_order([self.subtask, subtask2])

        api.content.transition(
            obj=self.subtask, transition='task-transition-planned-skipped')

        self.assertEquals(
            'task-state-skipped', api.content.get_state(self.subtask))
        self.assertEquals(
            'task-state-open', api.content.get_state(subtask2))

        self.set_workflow_state('task-state-rejected', self.subtask)
        self.set_workflow_state('task-state-planned', subtask2)
        api.content.transition(
            obj=self.subtask, transition='task-transition-rejected-skipped')

        self.assertEquals(
            'task-state-skipped', api.content.get_state(self.subtask))
        self.assertEquals(
            'task-state-open', api.content.get_state(subtask2))

    def test_handles_already_opened_tasks(self):
        self.login(self.regular_user)

        # create subtask
        subtask2 = create(Builder('task')
                          .within(self.task)
                          .having(responsible_client='fa',
                                  responsible=self.regular_user.getId(),
                                  issuer=self.dossier_responsible.getId(),
                                  task_type='correction',
                                  deadline=date(2016, 11, 1))
                          .in_state('task-state-open'))

        self.set_workflow_state('task-state-in-progress', self.subtask)
        alsoProvides(self.subtask, IFromSequentialTasktemplate)
        alsoProvides(subtask2, IFromSequentialTasktemplate)
        self.task.set_tasktemplate_order([self.subtask, subtask2])

        api.content.transition(
            obj=self.subtask, transition='task-transition-in-progress-resolved')

        self.assertEquals(
            'task-state-resolved', api.content.get_state(self.subtask))
        self.assertEquals(
            'task-state-open', api.content.get_state(subtask2))

    def test_record_activity_when_open_next_task(self):
        self.login(self.regular_user)

        # create subtask
        subtask2 = create(Builder('task')
                          .within(self.task)
                          .having(responsible_client='fa',
                                  responsible=self.regular_user.getId(),
                                  issuer=self.dossier_responsible.getId(),
                                  task_type='correction',
                                  deadline=date(2016, 11, 1))
                          .in_state('task-state-planned'))

        self.set_workflow_state('task-state-in-progress', self.subtask)
        alsoProvides(self.subtask, IFromSequentialTasktemplate)
        alsoProvides(subtask2, IFromSequentialTasktemplate)
        self.task.set_tasktemplate_order([self.subtask, subtask2])

        api.content.transition(
            obj=self.subtask, transition='task-transition-in-progress-resolved')

        self.assertEquals(
            'task-state-resolved', api.content.get_state(self.subtask))
        self.assertEquals(
            'task-state-open', api.content.get_state(subtask2))

        activity = Activity.query.all()[-1]
        self.assertEquals('task-added', activity.kind)
        self.assertEquals('Task opened', activity.label)
        self.assertEquals(u'New task opened by B\xe4rfuss K\xe4thi',
                          activity.summary)
        self.assertEquals(Oguid.for_object(subtask2), activity.resource.oguid)


class TestInitialStateForSubtasks(IntegrationTestCase):

    @browsing
    def test_is_open_for_regular_subtasks(self, browser):
        self.login(self.regular_user, browser=browser)

        with self.observe_children(self.task) as children:
            browser.open(self.task, view='++add++opengever.task.task')
            browser.fill({'Title': 'Subtas', 'Task Type': 'comment'})
            form = browser.find_form_by_field('Responsible')
            form.find_widget('Responsible').fill(
                'fa:{}'.format(self.secretariat_user.getId()))
            browser.click_on('Save')

        subtask = children['added'].pop()
        self.assertEquals('task-state-open', api.content.get_state(subtask))

    @browsing
    def test_is_planned_for_sequence_process_subtasks(self, browser):
        self.login(self.regular_user, browser=browser)
        alsoProvides(self.task, IFromSequentialTasktemplate)
        self.task.set_tasktemplate_order([self.subtask])

        with self.observe_children(self.task) as children:
            browser.open(self.task, view='++add++opengever.task.task')
            browser.fill({'Title': 'Subtas', 'Task Type': 'comment'})
            form = browser.find_form_by_field('Responsible')
            form.find_widget('Responsible').fill(
                'fa:{}'.format(self.secretariat_user.getId()))
            browser.click_on('Save')

        subtask = children['added'].pop()
        self.assertEquals('task-state-planned', api.content.get_state(subtask))
