from ftw.testbrowser import browsing
from opengever.testing import IntegrationTestCase
from os.path import join as pjoin
from plone.restapi.serializer.converters import json_compatible


class TestProposalSerialization(IntegrationTestCase):

    @browsing
    def test_proposal_contains_a_list_of_responses(self, browser):
        self.login(self.regular_user, browser=browser)
        browser.open(self.proposal, method="GET", headers=self.api_headers)
        self.maxDiff = None
        responses = browser.json['responses']

        self.assertEquals(3, len(responses))

        response_id = 1472645373000000
        expected_path = pjoin(self.proposal.absolute_url(),
                              '@responses',
                              str(response_id))
        self.assertEquals(
            {u'@id': expected_path,
             u'additional_data': {},
             u'changes': [],
             u'created': json_compatible(self.proposal.created().utcdatetime()),
             u'creator': {u'title': u'Ziegler Robert', u'token': u'robert.ziegler'},
             u'response_id': response_id,
             u'response_type': u'created',
             u'text': u''},
            responses[0])
