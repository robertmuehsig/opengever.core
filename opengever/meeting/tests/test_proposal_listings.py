from ftw.builder import Builder
from ftw.builder import create
from ftw.testbrowser import browsing
from opengever.testing import FunctionalTestCase


class ProposalListingTests(FunctionalTestCase):

    def setUp(self):
        super(ProposalListingTests, self).setUp()
        self.repository_root, self.repository_folder = create(
            Builder('repository_tree'))
        self.dossier = create(Builder('dossier')
                              .within(self.repository_folder)
                              .titled(u'Dossier A'))
        self.committee_container = create(Builder('committee_container'))
        self.committee = create(Builder('committee')
                                .within(self.committee_container)
                                .titled('My committee'))

        self.proposal = create(Builder('proposal')
                               .within(self.dossier)
                               .titled(u'My Proposal')
                               .having(committee=self.committee.load_model(),
                                       initial_position=u'My p\xf6sition is',
                                       proposed_action=u'My proposed acti\xf6n'))


class TestDossierProposalListing(ProposalListingTests):

    @browsing
    def test_listing(self, browser):
        browser.login().open(self.dossier, view='tabbedview_view-proposals')
        table = browser.css('table.listing').first

        # TODO: state should be translated
        self.assertEquals(
            [{'State': 'Pending',
              'Reference Number': '1',
              'Comittee': 'My committee',
              'Title': 'My Proposal',
              'Meeting': ''}],
            table.dicts())

    @browsing
    def test_proposals_are_linked_correctly(self, browser):
        browser.login().open(self.dossier, view='tabbedview_view-proposals')

        table = browser.css('table.listing').first
        link = table.rows[1].css('a').first

        self.assertEquals('My Proposal', link.text)

        self.assertEquals(
            'http://example.com/opengever-repository-repositoryroot/'
            'opengever-repository-repositoryfolder/dossier-1/proposal-1',
            link.get('href'))

    @browsing
    def test_proposals_are_linked_to_meeting_if_scheduled(self, browser):
        meeting_dossier = create(
            Builder('meeting_dossier').within(self.repository_folder))

        create(Builder('submitted_proposal').submitting(self.proposal))
        create(Builder('meeting')
               .having(committee=self.committee)
               .link_with(meeting_dossier)
               .scheduled_proposals([self.proposal, ]))

        browser.login().open(self.dossier, view='tabbedview_view-proposals')
        table = browser.css('table.listing').first

        self.assertEquals(
            [{'State': 'Scheduled',
              'Reference Number': '1',
              'Comittee': 'My committee',
              'Title': 'My Proposal',
              'Meeting': u'C\xf6mmunity meeting'}],
            table.dicts())


class TestSubmittedProposals(ProposalListingTests):

    def setUp(self):
        super(TestSubmittedProposals, self).setUp()

        self.submitted_proposal = create(Builder('submitted_proposal')
                                         .submitting(self.proposal))

    @browsing
    def test_listing(self, browser):
        browser.login().open(self.committee,
                             view='tabbedview_view-submittedproposals')
        table = browser.css('table.listing').first

        # TODO: state should be translated
        self.assertEquals(
            [{'State': 'Submitted',
              'Reference Number': '1',
              'Comittee': 'My committee',
              'Title': 'My Proposal',
              'Meeting': ''}],
            table.dicts())

    @browsing
    def test_proposals_are_linked_correctly_to_the_submitted_proposal(self, browser):
        browser.login().open(self.committee,
                             view='tabbedview_view-submittedproposals')

        table = browser.css('table.listing').first
        link = table.rows[1].css('a').first

        self.assertEquals('My Proposal', link.text)
        self.assertEquals(
            'http://example.com/opengever-meeting-committeecontainer/'
            'committee-1/submitted-proposal-1',
            link.get('href'))

    @browsing
    def test_submitted_proposals_are_linked_to_meeting_if_scheduled(self, browser):
        meeting_dossier = create(
            Builder('meeting_dossier').within(self.repository_folder))

        create(Builder('meeting')
               .having(committee=self.committee)
               .link_with(meeting_dossier)
               .scheduled_proposals([self.submitted_proposal, ]))

        browser.login().open(self.committee,
                             view='tabbedview_view-submittedproposals')
        table = browser.css('table.listing').first

        self.assertEquals(
            [{'State': 'Scheduled',
              'Reference Number': '1',
              'Comittee': 'My committee',
              'Title': 'My Proposal',
              'Meeting': u'C\xf6mmunity meeting'}],
            table.dicts())
