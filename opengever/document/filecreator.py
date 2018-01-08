from opengever.document.document import IDocumentSchema
from ftw.zipextract.interfaces import ObjectCreatorBase
from ftw.zipextract.interfaces import IFileCreator
from zope.component import adapts
from zope.interface import implements


class FileCreator(ObjectCreatorBase):
    implements(IFileCreator)
    adapts(IDocumentSchema)
    portal_type = "opengever.document.document"
