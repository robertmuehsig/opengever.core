from ftw.mail.interfaces import IEmailAddress
from opengever.api.serializer import GeverSerializeFolderToJson
from opengever.dossier.behaviors.dossier import IDossierMarker
from plone.restapi.interfaces import ISerializeToJson
from zope.component import adapter
from zope.interface import implementer
from zope.interface import Interface


@implementer(ISerializeToJson)
@adapter(IDossierMarker, Interface)
class SerializeDossierToJson(GeverSerializeFolderToJson):

    def __call__(self, *args, **kwargs):
        result = super(SerializeDossierToJson, self).__call__(*args, **kwargs)

        result[u"responsible_fullname"] = self.context.get_responsible_actor(
            ).get_label(with_principal=False)
        result[u'reference_number'] = self.context.get_reference_number()
        result[u'email'] = IEmailAddress(self.request).get_email_for_object(
            self.context)
        result[u'is_subdossier'] = self.context.is_subdossier()

        return result
