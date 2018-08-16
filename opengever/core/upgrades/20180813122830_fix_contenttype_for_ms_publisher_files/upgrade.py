from ftw.upgrade import UpgradeStep
from ftw.upgrade.progresslogger import ProgressLogger
from opengever.document.document import IDocumentSchema
from os.path import splitext
from plone import api


MS_PUBLISHER_EXTENSION = '.pub'
MS_PUBLISHER_MIMETYPE = 'application/x-mspublisher'


class FixContenttypeForMSPublisherFiles(UpgradeStep):
    """Fix contenttype for MS Publisher files.
    """

    def __call__(self):
        self.install_upgrade_profile()

        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog.unrestrictedSearchResults(
            {'object_provides': IDocumentSchema.__identifier__})

        for brain in ProgressLogger('Fix contettype for MS Publisher files',
                                    brains):
            if brain.getContentType == 'application/octet-stream':
                obj = brain.getObject()
                if not obj.file:
                    continue

                filename, ext = splitext(obj.file.filename)
                if ext == MS_PUBLISHER_EXTENSION:
                    obj.file.contentType = MS_PUBLISHER_MIMETYPE
                    obj.reindexObject()
