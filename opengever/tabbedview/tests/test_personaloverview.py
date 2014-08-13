from ftw.builder import Builder
from ftw.builder import create
from ftw.testbrowser import browsing
from opengever.testing import FunctionalTestCase
from opengever.testing import task2sqltask
from plone.app.testing import TEST_USER_ID


class TestGlobalTaskListings(FunctionalTestCase):

    def setUp(self):
        super(TestGlobalTaskListings, self).setUp()

        self.hugo = create(Builder('fixture').with_hugo_boss())

        self.task1 = create(Builder('task')
                            .having(responsible_client='client1',
                                    responsible=TEST_USER_ID,
                                    issuer=TEST_USER_ID))
        self.task2 = create(Builder('task')
                            .having(responsible_client='client1',
                                    responsible='hugo.boss',
                                    issuer=TEST_USER_ID))
        self.task3 = create(Builder('task')
                            .having(responsible_client='client1',
                                    responsible=TEST_USER_ID,
                                    issuer='hugo.boss'))

    @browsing
    def test_personal_overview_displays_username_in_title(self, browser):
        browser.login().open(view='personal_overview')
        self.assertEquals(u'Personal Overview: Test User',
                          browser.css('h1.documentFirstHeading').first.text)

    def test_my_tasks(self):
        view = self.portal.unrestrictedTraverse(
            'tabbedview_view-mytasks')
        view.update()

        self.assertEquals(
            [task2sqltask(self.task1), task2sqltask(self.task3)],
            view.contents)

    def test_my_issued_tasks(self):
        view = self.portal.unrestrictedTraverse(
            'tabbedview_view-myissuedtasks')
        view.update()

        self.assertEquals(
            [task2sqltask(self.task1), task2sqltask(self.task2)],
            view.contents)

    def test_all_tasks(self):
        view = self.portal.unrestrictedTraverse(
            'tabbedview_view-alltasks')
        view.update()

        expected = [self.task1, self.task2, self.task3]
        self.assertEquals(
            [task2sqltask(task) for task in expected],
            view.contents)

    def test_all_issued_tasks(self):
        view = self.portal.unrestrictedTraverse(
            'tabbedview_view-allissuedtasks')
        view.update()

        expected = [self.task1, self.task2, self.task3]
        self.assertEquals(
            [task2sqltask(task) for task in expected],
            view.contents)
