from opengever.base.role_assignments import RoleAssignmentManager
from plone.restapi.interfaces import ISerializeToJson
from plone.restapi.services.content.sharing import SharingGet as APISharingGet
from zExceptions import BadRequest
from zope.component import queryMultiAdapter
from zope.interface import implements
from zope.publisher.interfaces import IPublishTraverse


class SharingGet(APISharingGet):
    """Returns a serialized content object.
    """

    def reply(self):
        """Disable `plone.DelegateRoles` permission check.
        """

        serializer = queryMultiAdapter((self.context, self.request),
                                       interface=ISerializeToJson,
                                       name='local_roles')
        if serializer is None:
            self.request.response.setStatus(501)
            return dict(error=dict(message='No serializer available.'))

        return serializer(search=self.request.form.get('search'))


class RoleAssignmentsGet(APISharingGet):
    """API Endpoint which returns a list of all role assignments for a
    particular user.

    GET /@role-assignments/principal_id HTTP/1.1
    """

    implements(IPublishTraverse)

    def __init__(self, context, request):
        super(RoleAssignmentsGet, self).__init__(context, request)
        self.params = []

    def publishTraverse(self, request, name):
        # Consume any path segments after /@role-assignments as parameters
        self.params.append(name)
        return self

    def reply(self):
        principal_id = self.read_params()

        manager = RoleAssignmentManager(self.context)
        assignments = manager.get_assignments_chain(principal_id)

        return [assignment.serialize() for assignment in assignments]

    def read_params(self):
        """Returns principal_id passed in via traversal parameters.
        """
        if len(self.params) != 1:
            raise BadRequest(
                "Must supply principal ID as URL path parameter.")

        return self.params[0]
