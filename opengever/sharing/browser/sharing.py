from AccessControl.SecurityManagement import getSecurityManager
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import setSecurityManager
from opengever.sharing import _
from opengever.sharing.behaviors import IDossier, IStandard
from opengever.sharing.events import LocalRolesAcquisitionActivated
from opengever.sharing.events import LocalRolesAcquisitionBlocked
from opengever.sharing.events import LocalRolesModified
from plone.app.workflow.browser.sharing import SharingView
from plone.app.workflow.interfaces import ISharingPageRole
from plone.memoize.instance import memoize
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.component import getUtilitiesFor
from zope.event import notify


ROLE_MAPPING = (
    (IDossier, (
            (u'Reader', _('sharing_dossier_reader')),
            (u'Contributor', _('sharing_dossier_contributor')),
            (u'Editor', _('sharing_dossier_editor')),
            (u'Reviewer', _('sharing_dossier_reviewer')),
            (u'Publisher', _('sharing_dossier_publisher')),
            (u'Administrator', _('sharing_dossier_administrator')),
            )),

    (IStandard, (
            (u'Reader', _('sharing_reader')),
            (u'Contributor', _('sharing_contributor')),
            (u'Editor', _('sharing_editor')),
            (u'Role Manager', _('sharing_role_manager')),
            )),
    )


class OpengeverSharingView(SharingView):
    """Special Opengever Sharing View, which display different roles
    depending on the sharing behavior which is context"""

    template = ViewPageTemplateFile('sharing.pt')

    @memoize
    def roles(self, check_permission=True):
        """Get a list of roles that can be managed.

        Returns a list of dicts with keys:

        - id
        - title
        """
        context = self.context
        portal_membership = getToolByName(context, 'portal_membership')

        pairs = []
        for name, utility in getUtilitiesFor(ISharingPageRole):
            permission = utility.required_permission
            if not check_permission or permission is None or \
                    portal_membership.checkPermission(permission, context):
                pairs.append(dict(id=name, title=utility.title))

        pairs.sort(key=lambda x: x["id"])
        return pairs

    def available_roles(self):
        result = []
        for key, value in ROLE_MAPPING:
            if key.providedBy(self.context) or key is IStandard:
                for id, title in value:
                    roles = [r.get('id') for r in self.roles()]
                    if id in roles:
                        result.append(
                            {'id': id,
                             'title': title, })
                return result

        return self.roles()

    def role_settings(self):
        """ The standard role_settings method,
        but pop the AuthenticatedUsers group for not managers. """
        results = super(OpengeverSharingView, self).role_settings()

        member = self.context.portal_membership.getAuthenticatedMember()

        if member:
            if 'Manager' in member.getRolesInContext(self.context):
                return results

        # remove the group AuthenticatedUsers
        results.pop([r.get('id') for r in results].index('AuthenticatedUsers'))

        return results

    def update_inherit(self, status=True, reindex=True):
        """Method Wrapper for the super method, to allow notify a
        corresponding event. Needed for adding a Journalentry after a
        change of the inheritance"""

        # Modifying local roles needs the "Sharing page: Delegate roles"
        # permission as well as "Modify portal content". However, we don't
        # want to give the "Role Manager" Role "Modify portal content",
        # so we circumvent the permission check here by temporarily assuming
        # the owner's roles. [lgraf]
        old_sm = getSecurityManager()
        owner = self.context.getWrappedOwner()
        newSecurityManager(self.context, owner)

        changed = super(
            OpengeverSharingView, self).update_inherit(
                status=status, reindex=reindex)

        # Restore the old security manager
        setSecurityManager(old_sm)

        if changed:
            # notify the correspondig event
            if status:
                notify(LocalRolesAcquisitionActivated(self.context))
            else:
                notify(LocalRolesAcquisitionBlocked(self.context))

    def update_role_settings(self, new_settings, reindex):
        """"Method Wrapper for the super method, to allow notify a
        LocalRolesModified event. Needed for adding a Journalentry after a
        role_settings change"""

        old_local_roles = dict(self.context.get_local_roles())
        changed = super(OpengeverSharingView, self).update_role_settings(
            new_settings, reindex)

        if changed:
            notify(LocalRolesModified(
                    self.context,
                    old_local_roles,
                    self.context.get_local_roles()))


class SharingTab(OpengeverSharingView):
    """The sharing tab view, which show the standard sharin view,
    but wihtout the form."""

    template = ViewPageTemplateFile('sharing_tab.pt')

    @memoize
    def roles(self):
        return super(SharingTab, self).roles(check_permission=False)

    def get_css_classes(self):
        return ['searchform-hidden']
