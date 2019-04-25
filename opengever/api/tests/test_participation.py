from ftw.testbrowser import browsing
from opengever.testing import IntegrationTestCase
from opengever.workspace.participation.storage import IInvitationStorage
from zope.component import getUtility


def http_headers():
    return {'Accept': 'application/json',
            'Content-Type': 'application/json'}


def get_entry_by_token(entries, token):
    for entry in entries:
        if entry['token'] == token:
            return entry
    return None


class TestParticipationGet(IntegrationTestCase):

    @browsing
    def test_list_all_available_roles(self, browser):
        self.login(self.workspace_owner, browser)

        response = browser.open(
            self.workspace.absolute_url() + '/@participations',
            method='GET',
            headers=http_headers(),
        ).json

        self.assertItemsEqual(
            [
                {
                    u'managed': False,
                    u'id': u'WorkspaceOwner',
                    u'title': u'Owner'
                },
                {
                    u'managed': True,
                    u'id': u'WorkspaceAdmin',
                    u'title': u'Admin'
                },
                {
                    u'managed': True,
                    u'id': u'WorkspaceMember',
                    u'title': u'Member'
                },
                {
                    u'managed': True,
                    u'id': u'WorkspaceGuest',
                    u'title': u'Guest'
                }
            ], response.get('roles'))

    @browsing
    def test_list_all_current_participants_and_invitations(self, browser):
        self.login(self.workspace_owner, browser)

        iid = getUtility(IInvitationStorage).add_invitation(
            self.workspace,
            self.regular_user.getId(),
            self.workspace_owner.getId(),
            'WorkspaceGuest')

        response = browser.open(
            self.workspace.absolute_url() + '/@participations',
            method='GET',
            headers=http_headers(),
        ).json

        self.assertItemsEqual(
            [
                {
                    u'@id': u'http://nohost/plone/workspaces/workspace-1/@participations/users/beatrice.schrodinger',
                    u'@type': u'virtual.participations.user',
                    u'is_editable': True,
                    u'inviter_fullname': None,
                    u'participant_fullname': u'Schr\xf6dinger B\xe9atrice (beatrice.schrodinger)',
                    u'token': 'beatrice.schrodinger',
                    u'readable_role': u'Member',
                    u'role': u'WorkspaceMember',
                    u'participation_type': u'user',
                    u'readable_participation_type': u'User',
                },
                {
                    u'@id': u'http://nohost/plone/workspaces/workspace-1/@participations/users/fridolin.hugentobler',
                    u'@type': u'virtual.participations.user',
                    u'is_editable': True,
                    u'inviter_fullname': None,
                    u'participant_fullname': u'Hugentobler Fridolin (fridolin.hugentobler)',
                    u'token': 'fridolin.hugentobler',
                    u'readable_role': u'Admin',
                    u'role': u'WorkspaceAdmin',
                    u'participation_type': u'user',
                    u'readable_participation_type': u'User',
                },
                {
                    u'@id': u'http://nohost/plone/workspaces/workspace-1/@participations/users/gunther.frohlich',
                    u'@type': u'virtual.participations.user',
                    u'is_editable': False,
                    u'inviter_fullname': None,
                    u'participant_fullname': u'Fr\xf6hlich G\xfcnther (gunther.frohlich)',
                    u'token': 'gunther.frohlich',
                    u'readable_role': u'Owner',
                    u'role': u'WorkspaceOwner',
                    u'participation_type': u'user',
                    u'readable_participation_type': u'User',
                },
                {
                    u'@id': u'http://nohost/plone/workspaces/workspace-1/@participations/users/hans.peter',
                    u'@type': u'virtual.participations.user',
                    u'is_editable': True,
                    u'inviter_fullname': None,
                    u'participant_fullname': u'Peter Hans (hans.peter)',
                    u'token': 'hans.peter',
                    u'readable_role': u'Guest',
                    u'role': u'WorkspaceGuest',
                    u'participation_type': u'user',
                    u'readable_participation_type': u'User',
                },
                {
                    u'@id': u'http://nohost/plone/workspaces/workspace-1/@participations/invitations/{}'.format(iid),
                    u'@type': u'virtual.participations.invitation',
                    u'is_editable': True,
                    u'inviter_fullname': u'Fr\xf6hlich G\xfcnther (gunther.frohlich)',
                    u'participant_fullname': u'B\xe4rfuss K\xe4thi (kathi.barfuss)',
                    u'token': iid,
                    u'readable_role': u'Guest',
                    u'role': u'WorkspaceGuest',
                    u'participation_type': u'invitation',
                    u'readable_participation_type': u'Invitation',
                },
            ], response.get('items'))

    @browsing
    def test_owner_is_not_editable(self, browser):
        self.login(self.workspace_admin, browser)

        response = browser.open(
            self.workspace.absolute_url() + '/@participations',
            method='GET',
            headers=http_headers(),
        ).json

        items = response.get('items')

        self.assertFalse(
            get_entry_by_token(items, self.workspace_owner.id)['is_editable'],
            'The admin should not be able to manage himself')

    @browsing
    def test_current_logged_in_admin_cannot_edit_himself(self, browser):
        self.login(self.workspace_admin, browser)

        response = browser.open(
            self.workspace.absolute_url() + '/@participations',
            method='GET',
            headers=http_headers(),
        ).json

        items = response.get('items')

        self.assertFalse(
            get_entry_by_token(items, self.workspace_admin.id)['is_editable'],
            'The admin should not be able to manage himself')

        self.assertTrue(
            get_entry_by_token(items, 'hans.peter')['is_editable'],
            'The admin should be able to manage hans.peter')

    @browsing
    def test_an_admin_can_edit_other_members(self, browser):
        self.login(self.workspace_admin, browser)

        response = browser.open(
            self.workspace.absolute_url() + '/@participations',
            method='GET',
            headers=http_headers(),
        ).json

        items = response.get('items')

        self.assertTrue(
            get_entry_by_token(items, self.workspace_guest.id)['is_editable'],
            'The admin should be able to manage {}'.format(self.workspace_guest.id))

    @browsing
    def test_user_without_sharing_permission_cannot_manage(self, browser):
        self.login(self.workspace_member, browser)

        response = browser.open(
            self.workspace.absolute_url() + '/@participations',
            method='GET',
            headers=http_headers(),
        ).json

        self.assertFalse(
            any([item.get('is_editable') for item in response.get('items')]),
            'No entry should be editable because the user has no permission')
