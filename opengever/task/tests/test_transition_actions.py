from ftw.builder import Builder
from ftw.builder import create
from ftw.testbrowser import browsing
from opengever.testing import FunctionalTestCase
from opengever.testing import IntegrationTestCase
import re


URL_WIHOUT_TOKEN_RE = re.compile(r'(.*)([\?, &]_authenticator=.*)')


class BaseTransitionActionTestMixin(object):

    def assert_action(self, browser, expected):
        url = URL_WIHOUT_TOKEN_RE.match(browser.url).groups()[0]
        self.assertEquals(expected, url)


class BaseTransitionActionIntegrationTest(IntegrationTestCase, BaseTransitionActionTestMixin):

    def do_transition(self, browser, task, transition):
        browser.open(task)
        browser.css('#workflow-transition-{}'.format(transition)).first.click()


class BaseTransitionActionFunctionalTest(FunctionalTestCase, BaseTransitionActionTestMixin):

    def do_transition(self, browser, task):
        browser.login().open(task)
        browser.css('#workflow-transition-{}'.format(self.transition)).first.click()


class TestTaskTransitionActionsForInProgress(BaseTransitionActionIntegrationTest):

    @browsing
    def test_delegation(self, browser):
        self.login(self.regular_user, browser)
        self.do_transition(browser, self.task, 'task-transition-delegate')
        expected_transition_action = '@@delegate_recipients'
        self.assert_action(browser, '/'.join((self.task.absolute_url(), expected_transition_action, )))
        self.assertEquals('Delegate task', browser.css('.documentFirstHeading').first.text)

    @browsing
    def test_deadline_modification(self, browser):
        self.login(self.dossier_responsible, browser)
        self.do_transition(browser, self.task, 'task-transition-modify-deadline')
        expected_transition_action = '@@modify_deadline?form.widgets.transition=task-transition-modify-deadline'
        self.assert_action(browser, '/'.join((self.task.absolute_url(), expected_transition_action, )))
        self.assertEquals('Modify deadline', browser.css('.documentFirstHeading').first.text)

    @browsing
    def test_reassigning(self, browser):
        self.login(self.regular_user, browser)
        self.do_transition(browser, self.task, 'task-transition-reassign')
        expected_transition_action = '@@assign-task?form.widgets.transition=task-transition-reassign'
        self.assert_action(browser, '/'.join((self.task.absolute_url(), expected_transition_action, )))


class TestTaskTransitionActionsForResolved(BaseTransitionActionIntegrationTest):
    """This class is taking advantage of self.subtask being resolved."""

    @browsing
    def test_reworking(self, browser):
        self.login(self.regular_user, browser)
        self.do_transition(browser, self.subtask, 'task-transition-resolved-in-progress')
        expected_transition_action = 'addresponse?form.widgets.transition=task-transition-resolved-in-progress'
        self.assert_action(browser, '/'.join((self.subtask.absolute_url(), expected_transition_action, )))


class TestTaskTransitionActionsForCancelled(BaseTransitionActionIntegrationTest):

    def setUp(self):
        super(TestTaskTransitionActionsForCancelled, self).setUp()
        with self.login(self.regular_user):
            self.set_workflow_state('task-state-cancelled', self.task)

    @browsing
    def test_reopening_task(self, browser):
        self.login(self.dossier_responsible, browser)
        self.do_transition(browser, self.task, 'task-transition-cancelled-open')
        expected_transition_action = 'addresponse?form.widgets.transition=task-transition-cancelled-open'
        self.assert_action(browser, '/'.join((self.task.absolute_url(), expected_transition_action, )))


class TestTaskTransitionActionsForOpen(BaseTransitionActionIntegrationTest):

    def setUp(self):
        super(TestTaskTransitionActionsForOpen, self).setUp()
        with self.login(self.regular_user):
            self.set_workflow_state('task-state-open', self.task)

    @browsing
    def test_cancelling(self, browser):
        self.login(self.dossier_responsible, browser)
        self.do_transition(browser, self.task, 'task-transition-open-cancelled')
        expected_transition_action = 'addresponse?form.widgets.transition=task-transition-open-cancelled'
        self.assert_action(browser, '/'.join((self.task.absolute_url(), expected_transition_action, )))

    @browsing
    def test_rejecting(self, browser):
        self.login(self.regular_user, browser)
        self.do_transition(browser, self.task, 'task-transition-open-rejected')
        expected_transition_action = 'addresponse?form.widgets.transition=task-transition-open-rejected'
        self.assert_action(browser, '/'.join((self.task.absolute_url(), expected_transition_action, )))

    @browsing
    def test_resolving(self, browser):
        self.login(self.dossier_responsible, browser)
        self.do_transition(browser, self.task, 'task-transition-open-cancelled')
        expected_transition_action = 'addresponse?form.widgets.transition=task-transition-open-cancelled'
        self.assert_action(browser, '/'.join((self.task.absolute_url(), expected_transition_action, )))


class TestInProgressResolveAction(BaseTransitionActionFunctionalTest):
    transition = 'task-transition-in-progress-resolved'

    @browsing
    def test_is_responseform_for_unidirectional_tasks(self, browser):
        task = create(Builder('task')
                      .having(task_type='information')
                      .in_state('task-state-in-progress'))
        self.do_transition(browser, task)
        self.assert_action(
            browser,
            'http://nohost/plone/task-1/addresponse?form.widgets.transition=task-transition-in-progress-resolved',
            )

    @browsing
    def test_is_responseform_for_bidirectional_orgunit_intern_tasks(self, browser):
        task = create(Builder('task')
                      .in_state('task-state-in-progress'))
        self.do_transition(browser, task)
        self.assert_action(
            browser,
            'http://nohost/plone/task-1/addresponse?form.widgets.transition=task-transition-in-progress-resolved',
            )

    @browsing
    def test_is_complete_successor_form_for_successors(self, browser):
        predecessor = create(Builder('task'))
        dossier = create(Builder('dossier'))
        task = create(Builder('task')
                      .within(dossier)
                      .having(task_type='comment')
                      .in_state('task-state-in-progress')
                      .successor_from(predecessor))
        self.do_transition(browser, task)
        self.assert_action(
            browser,
            'http://nohost/plone/dossier-1/task-2/@@complete_successor_task?transition=task-transition-in-progress-resolved',
            )

    @browsing
    def test_is_responseform_for_forwarding_successors(self, browser):
        forwarding = create(Builder('forwarding'))
        task = create(Builder('task')
                      .in_state('task-state-in-progress')
                      .successor_from(forwarding))
        self.do_transition(browser, task)
        self.assert_action(
            browser,
            'http://nohost/plone/task-1/addresponse?form.widgets.transition=task-transition-in-progress-resolved',
            )


class TestInProgressTestedAndClosedAction(BaseTransitionActionFunctionalTest):

    transition = 'task-transition-in-progress-tested-and-closed'
    task_type = 'direct-execution'

    @browsing
    def test_is_responseform_for_non_successor(self, browser):
        task = create(Builder('task')
                      .having(task_type=self.task_type)
                      .in_state('task-state-in-progress'))
        self.do_transition(browser, task)
        self.assert_action(
            browser,
            'http://nohost/plone/task-1/addresponse?form.widgets.transition=task-transition-in-progress-tested-and-closed',
            )

    @browsing
    def test_is_complete_successor_form_for_successors(self, browser):
        predecessor = create(Builder('task'))
        dossier = create(Builder('dossier'))
        task = create(Builder('task')
                      .within(dossier)
                      .having(task_type=self.task_type)
                      .in_state('task-state-in-progress')
                      .successor_from(predecessor))
        self.do_transition(browser, task)
        self.assert_action(
            browser,
            'http://nohost/plone/dossier-1/task-2/@@complete_successor_task'
            '?transition=task-transition-in-progress-tested-and-closed',
            )

    @browsing
    def test_is_responseform_for_forwarding_successors(self, browser):
        forwarding = create(Builder('forwarding'))
        task = create(Builder('task')
                      .having(task_type=self.task_type)
                      .in_state('task-state-in-progress')
                      .successor_from(forwarding))
        self.do_transition(browser, task)
        self.assert_action(
            browser,
            'http://nohost/plone/task-1/addresponse?form.widgets.transition=task-transition-in-progress-tested-and-closed',
            )


class TestAccept(BaseTransitionActionFunctionalTest):

    transition = 'task-transition-open-in-progress'

    def setUp(self):
        super(TestAccept, self).setUp()
        additional = create(Builder('admin_unit').id(u'additional'))
        create(Builder('org_unit')
               .id(u'additional')
               .having(admin_unit=additional)
               .with_default_groups()
               .assign_users([self.user], to_inbox=False))

    @browsing
    def test_is_responseform_for_adminunit_intern_tasks(self, browser):
        task = create(Builder('task')
                      .having(responsible_client='client1'))
        self.do_transition(browser, task)
        self.assert_action(
            browser,
            'http://nohost/plone/task-1/addresponse?form.widgets.transition=task-transition-open-in-progress',
            )

    @browsing
    def test_is_accept_wizzard_for_task_assigned_to_foreign_adminunit(self, browser):
        task = create(Builder('task')
                      .having(responsible_client='additional'))
        self.do_transition(browser, task)

        self.assert_action(
            browser,
            'http://nohost/plone/task-1/@@accept_choose_method',
            )


class TestOpenToClose(BaseTransitionActionFunctionalTest):

    transition = 'task-transition-open-tested-and-closed'

    def setUp(self):
        super(TestOpenToClose, self).setUp()
        additional = create(Builder('admin_unit').id(u'additional'))
        create(Builder('org_unit')
               .id(u'additional')
               .having(admin_unit=additional)
               .with_default_groups()
               .assign_users([self.user], to_inbox=False))

    @browsing
    def test_is_addform_for_bidirectional_tasks(self, browser):
        task = create(Builder('task')
                      .having(task_type='comment'))
        self.do_transition(browser, task)
        self.assert_action(
            browser,
            'http://nohost/plone/task-1/addresponse?form.widgets.transition=task-transition-open-tested-and-closed',
            )

    @browsing
    def test_is_addform_for_unidirectional_adminunit_intern_tasks(self, browser):
        task = create(Builder('task')
                      .having(task_type='information'))
        self.do_transition(browser, task)
        self.assert_action(
            browser,
            'http://nohost/plone/task-1/addresponse?form.widgets.transition=task-transition-open-tested-and-closed',
            )

    @browsing
    def test_is_responseform_for_unidirectional_tasks_on_foreign_admin_unit_without_documents(self, browser):
        task = create(Builder('task')
                      .having(task_type='information',
                              responsible_client='additional'))
        self.do_transition(browser, task)

        self.assert_action(
            browser,
            'http://nohost/plone/task-1/addresponse?form.widgets.transition=task-transition-open-tested-and-closed',
            )

    @browsing
    def test_is_closetask_wizard_for_unidirectional_tasks_on_foreign_admin_unit_with_documents(self, browser):
        task = create(Builder('task')
                      .having(task_type='information',
                              responsible_client='additional'))
        create(Builder('document').within(task))
        self.do_transition(browser, task)
        self.assert_action(
            browser,
            'http://nohost/plone/task-1/@@close-task-wizard_select-documents',
            )
