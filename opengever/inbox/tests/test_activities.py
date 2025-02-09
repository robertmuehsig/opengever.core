from ftw.builder import Builder
from ftw.builder import create
from ftw.testbrowser import browsing
from opengever.activity import notification_center
from opengever.activity.model import Activity
from opengever.core.testing import OPENGEVER_FUNCTIONAL_ACTIVITY_LAYER
from opengever.task.browser.accept.utils import accept_forwarding_with_successor
from opengever.testing import FunctionalTestCase
from opengever.testing import IntegrationTestCase
from opengever.testing import obj2brain
from plone.app.testing import TEST_USER_ID
import json


class TestForwardingActivites(FunctionalTestCase):

    layer = OPENGEVER_FUNCTIONAL_ACTIVITY_LAYER

    def setUp(self):
        super(TestForwardingActivites, self).setUp()
        self.center = notification_center()
        self.inbox = create(Builder('inbox').titled(u'Inbox'))
        self.document = create(Builder('document').titled(u'Document'))

        self.hugo = create(Builder('ogds_user')
                           .id('hugo.boss')
                           .assign_to_org_units([self.org_unit])
                           .having(firstname=u'Hugo', lastname=u'Boss'))

        create(Builder('ogds_user')
               .id('peter.mueller')
               .assign_to_org_units([self.org_unit])
               .in_group(self.org_unit.inbox_group)
               .having(firstname=u'Peter', lastname=u'M\xfcller'))

    @browsing
    def test_forwarding_added(self, browser):
        browser.login().open(
            self.inbox, view='++add++opengever.inbox.forwarding',
            data={'paths': ['/'.join(self.document.getPhysicalPath())]})

        browser.fill({'Title': u'Abkl\xe4rung Fall Meier',
                      'Deadline': '13.02.2015',
                      'Text': 'Lorem ipsum'})

        form = browser.find_form_by_field('Responsible')
        form.find_widget('Responsible').fill('org-unit-1:hugo.boss')

        browser.find('Save').click()

        activity = Activity.query.first()
        self.assertEquals('forwarding-added', activity.kind)
        self.assertEquals(u'Abkl\xe4rung Fall Meier', activity.title)
        self.assertEquals(u'New forwarding added by Test User',
                          activity.summary)

    @browsing
    def test_accepting_forwarding_with_successor_updated_responsibles(self, browser):
        inbox = create(Builder('inbox'))
        forwarding = create(Builder('forwarding')
                            .having(responsible=TEST_USER_ID,
                                    issuer='hugo.boss')
                            .within(inbox))

        successor = accept_forwarding_with_successor(
            self.portal, forwarding.oguid.id,
            'OK. That is something for me.', dossier=None)

        forwarding_resource = self.center.fetch_resource(forwarding)
        successor_resource = self.center.fetch_resource(successor)

        self.assertItemsEqual(
            [(u'hugo.boss', u'task_issuer')],
            [(subscription.watcher.actorid, subscription.role)
             for subscription in forwarding_resource.subscriptions])

        self.assertItemsEqual(
            [(u'test_user_1_', u'task_responsible'),
             (u'inbox:org-unit-1', u'task_issuer')],
            [(subscription.watcher.actorid, subscription.role) for subscription in successor_resource.subscriptions])

    @browsing
    def test_accepting_and_assign_forwarding_with_successor_and__updated_responsibles(self, browser):
        inbox = create(Builder('inbox'))
        dossier = create(Builder('dossier'))
        forwarding = create(Builder('forwarding')
                            .having(responsible=TEST_USER_ID,
                                    issuer='hugo.boss')
                            .within(inbox))
        self.center.add_task_responsible(forwarding, TEST_USER_ID)
        self.center.add_task_issuer(forwarding, 'hugo.boss')

        task = accept_forwarding_with_successor(
            self.portal, forwarding.oguid.id,
            'OK. That is something for me.', dossier=dossier)

        forwarding_resource = self.center.fetch_resource(forwarding)
        task_resource = self.center.fetch_resource(task)
        self.assertItemsEqual(
            ['hugo.boss'],
            [watcher.actorid for watcher in forwarding_resource.watchers])
        self.assertItemsEqual(
            [TEST_USER_ID],
            [watcher.actorid for watcher in task_resource.watchers])


class TestForwardingReassignActivity(FunctionalTestCase):

    layer = OPENGEVER_FUNCTIONAL_ACTIVITY_LAYER

    def setUp(self):
        super(TestForwardingReassignActivity, self).setUp()
        self.center = notification_center()
        self.inbox = create(Builder('inbox').titled(u'Inbox'))
        self.document = create(Builder('document')
                               .within(self.inbox)
                               .titled(u'Document'))

        self.hugo = create(Builder('ogds_user')
                           .id('hugo.boss')
                           .assign_to_org_units([self.org_unit])
                           .having(firstname=u'Hugo', lastname=u'Boss'))
        self.jon = create(Builder('ogds_user')
                          .id('jon.meier')
                          .assign_to_org_units([self.org_unit])
                          .having(firstname=u'Jon', lastname=u'Meier'))
        self.peter = create(Builder('ogds_user')
                            .id('peter.mueller')
                            .assign_to_org_units([self.org_unit])
                            .in_group(self.org_unit.inbox_group)
                            .having(firstname=u'Peter', lastname=u'M\xfcller'))

    def add_forwarding(self, browser):
        data = {'paths:list': ['/'.join(self.document.getPhysicalPath())]}
        browser.login().open(self.inbox, data,
                             view='++add++opengever.inbox.forwarding')
        browser.fill({'Title': u'Abkl\xe4rung Fall Meier'})
        form = browser.find_form_by_field('Responsible')
        form.find_widget('Responsible').fill('org-unit-1:jon.meier')
        form.find_widget('Issuer').fill(u'hugo.boss')

        browser.css('#form-buttons-save').first.click()
        return self.inbox.get('forwarding-1')

    def reassign(self, browser, forwarding, responsible):
        browser.login().open(forwarding)
        browser.find('forwarding-transition-reassign').click()
        browser.fill({'Response': u'Peter k\xf6nntest du das \xfcbernehmen.'})

        form = browser.find_form_by_field('Responsible')
        form.find_widget('Responsible').fill(responsible)

        browser.find('Assign').click()

    @browsing
    def test_reassing_forwarding_create_notifications_for_all_participants(self, browser):
        forwarding = self.add_forwarding(browser)
        self.reassign(browser, forwarding, responsible='peter.mueller')

        self.assertEquals(2, len(Activity.query.all()))
        self.assertEquals(u'forwarding-added',
                          Activity.query.all()[0].kind)
        self.assertEquals(u'forwarding-transition-reassign',
                          Activity.query.all()[1].kind)

    @browsing
    def test_notifies_old_and_new_responsible(self, browser):
        forwarding = self.add_forwarding(browser)
        self.reassign(browser, forwarding, responsible='peter.mueller')

        activities = Activity.query.all()
        reassign_activity = activities[-1]
        self.assertItemsEqual(
            [u'jon.meier', u'peter.mueller', u'hugo.boss'],
            [notes.userid for notes in reassign_activity.notifications])

    @browsing
    def test_removes_old_responsible_from_watchers_list(self, browser):
        forwarding = self.add_forwarding(browser)
        self.reassign(browser, forwarding, responsible='peter.mueller')

        resource = notification_center().fetch_resource(forwarding)
        self.assertItemsEqual(
            ['peter.mueller', u'hugo.boss'],
            [watcher.actorid for watcher in resource.watchers])


class TestForwardingActivitesIntegration(IntegrationTestCase):

    features = ('activity', )

    @browsing
    def test_assign_to_dossier_open_successor_task(self, browser):
        self.login(self.secretariat_user, browser=browser)

        url = '{}/@workflow/forwarding-transition-assign-to-dossier'.format(
            self.inbox_forwarding.absolute_url())

        dossier_uid = obj2brain(self.empty_dossier).UID
        data = {'dossier': dossier_uid}
        browser.open(url, method='POST',
                     data=json.dumps(data), headers=self.api_headers)

        task = self.empty_dossier.objectValues()[-1]

        resource = notification_center().fetch_resource(task)
        self.assertItemsEqual(
            [(self.regular_user.id, u'task_responsible'),
             (u'inbox:fa', u'task_issuer')],
            [(subscription.watcher.actorid, subscription.role)
             for subscription in resource.subscriptions])
