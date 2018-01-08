from opengever.dossier.templatefolder.templatefolder import ITemplateFolder
from ftw.zipextract.interfaces import IFolderCreator
from ftw.zipextract.interfaces import ObjectCreatorBase
from zope.component import adapts
from zope.interface import implements

class FolderCreator(ObjectCreatorBase):
    implements(IFolderCreator)
    adapts(ITemplateFolder)
    portal_type = "opengever.dossier.templatefolder"
