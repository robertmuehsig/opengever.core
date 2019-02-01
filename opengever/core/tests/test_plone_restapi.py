from ftw.testbrowser import browsing
from opengever.testing import IntegrationTestCase
from Products.CMFCore.utils import getToolByName
from plone import api

GEVER_TYPES = ['ftw.mail.mail',
               'opengever.contact.contact',
               'opengever.contact.contactfolder',
               'opengever.disposition.disposition',
               'opengever.document.document',
               'opengever.dossier.businesscasedossier',
               'opengever.dossier.dossiertemplate',
               'opengever.dossier.templatefolder',
               'opengever.inbox.container',
               'opengever.inbox.forwarding',
               'opengever.inbox.inbox',
               'opengever.inbox.yearfolder',
               'opengever.meeting.committee',
               'opengever.meeting.committeecontainer',
               'opengever.meeting.meetingdossier',
               'opengever.meeting.meetingtemplate',
               'opengever.meeting.paragraphtemplate',
               'opengever.meeting.proposal',
               'opengever.meeting.proposaltemplate',
               'opengever.meeting.sablontemplate',
               'opengever.meeting.submittedproposal',
               'opengever.private.dossier',
               'opengever.private.folder',
               'opengever.private.root',
               'opengever.repository.repositoryfolder',
               'opengever.repository.repositoryroot',
               'opengever.task.task',
               'opengever.tasktemplates.tasktemplate',
               'opengever.tasktemplates.tasktemplatefolder',
               'opengever.workspace.folder',
               'opengever.workspace.root',
               'opengever.workspace.workspace',
               'Plone_Site']


class TestPloneRestAPI(IntegrationTestCase):

    @browsing
    def test_rest_api_bla(self, browser):
        self.login(self.regular_user, browser)
        for content_type in GEVER_TYPES:
            try:
                browser.open(self.portal.absolute_url() + '/@types/{}'.format(content_type),
                             method='GET', headers={'Accept': 'application/json'})
                print("ok for", content_type)
            except:
                print("error for", content_type)
                continue
