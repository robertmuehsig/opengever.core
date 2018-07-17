from ftw.builder import Builder
from ftw.builder import create
from ftw.testbrowser import browsing
from opengever.base.role_assignments import RoleAssignmentManager
from opengever.base.role_assignments import SharingRoleAssignment
from opengever.testing import IntegrationTestCase
from plone import api
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent


class TestLocalRolesSetter(IntegrationTestCase):

    def test_responsible_has_local_editor_role_on_task_when_is_added(self):
        self.login(self.regular_user)

        self.assertEquals(
            ('Editor', ),
            self.task.get_local_roles_for_userid(self.regular_user.id))

    def test_new_responsible_has_local_editor_role_on_task_when_is_changed(self):
        self.login(self.regular_user)

        self.task.responsible = self.secretariat_user.id
        notify(ObjectModifiedEvent(self.task))

        self.assertEquals(
            ('Editor', ),
            self.task.get_local_roles_for_userid(self.secretariat_user.id))

    def test_dont_remove_editor_role_when_responsible_is_changed(self):
        self.login(self.regular_user)

        self.task.responsible = self.secretariat_user.id
        notify(ObjectModifiedEvent(self.task))

        self.assertEquals(
            ('Editor', ),
            self.task.get_local_roles_for_userid(self.regular_user.id))

    def test_responsible_has_reader_role_on_related_items_when_task_is_added(self):
        self.login(self.regular_user)

        # inactive_task is unidirectional by value
        self.assertEquals(
            ('Reader', ),
            self.inactive_document.get_local_roles_for_userid(self.regular_user.id))

    def test_responsible_has_reader_role_on_related_items_when_responsible_is_changed(self):
        self.login(self.regular_user)

        self.inactive_task.responsible = self.secretariat_user.id
        notify(ObjectModifiedEvent(self.inactive_task))

        roles = self.inactive_document.get_local_roles_for_userid(
            self.secretariat_user.id)
        self.assertEquals(('Reader', ), roles)

    def test_responsible_of_a_bidirectional_by_ref_task_has_reader_and_editor_role_on_related_items(self):
        self.login(self.regular_user)

        # task is bidirectional by value
        self.assertEquals(
            ('Editor', 'Reader', ),
            self.document.get_local_roles_for_userid(self.regular_user.id))

    def test_responsible_has_contributor_role_on_distinct_parent_when_task_is_added(self):
        self.login(self.regular_user)
        self.assertEquals(
            ('Contributor', ),
            self.dossier.get_local_roles_for_userid(self.regular_user.id))

    def test_responsible_has_contributor_role_on_distinct_parent_when_task_is_updated(self):
        self.login(self.regular_user)

        self.inactive_task.responsible = self.secretariat_user.id
        notify(ObjectModifiedEvent(self.inactive_task))

        self.assertEquals(
            ('Contributor', ),
            self.inactive_dossier.get_local_roles_for_userid(self.secretariat_user.id))

    def test_inbox_group_of_the_responsible_client_has_the_same_localroles_as_the_responsible_in_a_multiclient_setup(self):
        self.login(self.regular_user)

        self.add_additional_org_unit()

        dossier = create(Builder('dossier'))
        document = create(Builder('document'))
        task = create(Builder('task')
                      .within(dossier)
                      .relate_to(document)
                      .having(responsible=self.regular_user.id,
                              responsible_client='fa'))

        self.assertEquals(
            ('Editor', ),
            task.get_local_roles_for_userid('fa_inbox_users'))
        self.assertEquals(
            ('Reader', ),
            document.get_local_roles_for_userid('fa_inbox_users'))
        self.assertEquals(
            ('Contributor', ),
            dossier.get_local_roles_for_userid('fa_inbox_users'))

    def test_inbox_group_has_no_additional_localroles_in_a_oneclient_setup(self):
        self.login(self.regular_user)

        self.assertEquals(
            (),
            self.task.get_local_roles_for_userid('fa_inbox_users'))
        self.assertEquals(
            (),
            self.document.get_local_roles_for_userid('fa_inbox_users'))
        self.assertEquals(
            (),
            self.dossier.get_local_roles_for_userid('fa_inbox_users'))

    def test_use_inbox_group_when_inbox_is_responsible(self):
        self.login(self.regular_user)

        task = create(Builder('task')
                      .within(self.dossier)
                      .having(responsible='inbox:fa'))

        self.assertEquals(
            ('Editor', ),
            task.get_local_roles_for_userid('fa_inbox_users'))

        self.assertEquals(
            ('Contributor', ),
            self.dossier.get_local_roles_for_userid('fa_inbox_users'))

        self.assertEquals(
            (), task.get_local_roles_for_userid('inbox:client1'))

    @browsing
    def test_responsible_can_edit_related_documents_that_are_inside_a_task(self, browser):
        self.login(self.administrator, browser=browser)
        api.content.disable_roles_acquisition(obj=self.dossier)

        RoleAssignmentManager(self.dossier).add_or_update_assignment(
            SharingRoleAssignment(self.administrator.getId(),
                                  ['Reader', 'Contributor', 'Editor']))

        self.task.responsible = self.secretariat_user.id
        notify(ObjectModifiedEvent(self.task))

        self.login(self.secretariat_user, browser=browser)
        browser.open(self.taskdocument, view='edit')
