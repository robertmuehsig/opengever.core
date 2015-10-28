from datetime import timedelta
from ftw.builder import Builder
from ftw.builder import create
from ftw.testbrowser import browsing
from opengever.testing import add_languages
from opengever.testing import FunctionalTestCase


class TestCommitteeContainer(FunctionalTestCase):

    def setUp(self):
        super(TestCommitteeContainer, self).setUp()
        self.grant('Manager')
        add_languages(['de-ch', 'fr-ch'])
        self.template = create(
            Builder('sablontemplate')
            .without_default_title()
            .attach_file_containing("blub blub", name=u't\xf6st.txt'))

    @browsing
    def test_supports_translated_title(self, browser):
        browser.login().open(view='++add++opengever.meeting.committeecontainer')
        browser.fill({'Title (German)': u'Sitzungen',
                      'Title (French)': u's\xe9ance',
                      'Protocol template':self.template,
                      'Excerpt template': self.template})

        browser.find('Save').click()

        browser.find('FR').click()
        self.assertEquals(u's\xe9ance', browser.css('h1').first.text)

        browser.find('DE').click()
        self.assertEquals(u'Sitzungen', browser.css('h1').first.text)


class TestCommitteesTab(FunctionalTestCase):

    def setUp(self):
        super(TestCommitteesTab, self).setUp()

        self.container = create(Builder('committee_container'))
        self.committee = create(Builder('committee')
                                .within(self.container)
                                .titled(u'Kleiner Burgerrat'))
        self.committee_model = self.committee.load_model()

    @browsing
    def test_shows_albhabetically_sorted_committees_in_boxes(self, browser):
        create(Builder('committee')
               .within(self.container)
               .titled(u'Wirtschafts Kommission'))

        create(Builder('committee')
               .within(self.container)
               .titled(u'Gew\xe4sser Kommission'))

        browser.login().open(self.container, view='tabbedview_view-committees')

        self.assertEquals(
            [u'Gew\xe4sser Kommission', u'Kleiner Burgerrat', u'Wirtschafts Kommission'],
            browser.css('#committees_view .committee_box h2').text)

    @browsing
    def test_can_only_see_committees_for_corresponding_group(self, browser):
        user = create(Builder('user')
                      .with_userid('hugo.boss'))
        create(Builder('group')
               .with_groupid('kom_wirtschaft')
               .with_members(user))
        # make committee-container accessible
        self.container.manage_setLocalRoles('kom_wirtschaft', ['Reader'])

        create(Builder('committee')
               .within(self.container)
               .having(group_id='kom_wirtschaft')
               .titled(u'Wirtschafts Kommission'))
        create(Builder('committee')
               .within(self.container)
               .titled(u'Gew\xe4sser Kommission'))

        browser.login('hugo.boss').open(self.container,
                                        view='tabbedview_view-committees')
        self.assertEquals(
            [u'Wirtschafts Kommission'],
            browser.css('#committees_view .committee_box h2').text)

    @browsing
    def test_tabbedview_text_filter(self, browser):
        create(Builder('committee')
               .within(self.container)
               .titled(u'Wirtschafts Kommission'))

        create(Builder('committee')
               .within(self.container)
               .titled(u'Gew\xe4sser Kommission'))

        browser.login().open(self.container,
                             view='tabbedview_view-committees',
                             data={'searchable_text': 'Wirtschaf Komm'})

        self.assertEquals(
            [u'Wirtschafts Kommission'],
            browser.css('#committees_view .committee_box h2').text)

    @browsing
    def test_text_filter_ignores_trailing_asterisk(self, browser):
        create(Builder('committee')
               .within(self.container)
               .titled(u'Wirtschafts Kommission'))

        create(Builder('committee')
               .within(self.container)
               .titled(u'Gew\xe4sser Kommission'))

        browser.login().open(self.container,
                             view='tabbedview_view-committees',
                             data={'searchable_text': 'Wirtschaft*'})

        self.assertEquals(
            [u'Wirtschafts Kommission'],
            browser.css('#committees_view .committee_box h2').text)

    @browsing
    def test_commitee_is_linked_correctly(self, browser):
        browser.login().open(self.container, view='tabbedview_view-committees')
        title = browser.css('#committees_view .committee_box a').first

        self.assertEquals(u'Kleiner Burgerrat', title.text)
        self.assertEquals(
            'http://example.com/opengever-meeting-committeecontainer/committee-1',
            title.get('href'))

    @browsing
    def test_unscheduled_proposal_number(self, browser):
        dossier = create(Builder('dossier'))

        for i in range(0, 5):
            proposal_a = create(Builder('proposal')
                                .within(dossier)
                                .having(committee=self.committee_model))
            create(Builder('submitted_proposal').submitting(proposal_a))

        browser.login().open(self.container, view='tabbedview_view-committees')

        self.assertEquals(
            'New unschedulded proposals: 5',
            browser.css('#committees_view .unscheduled_proposals').first.text)

    @browsing
    def test_unscheduled_proposal_number_link(self, browser):
        dossier = create(Builder('dossier'))

        proposal_a = create(Builder('proposal')
                            .within(dossier)
                            .having(committee=self.committee_model))
        create(Builder('submitted_proposal').submitting(proposal_a))

        browser.login().open(self.container, view='tabbedview_view-committees')
        link = browser.css('#committees_view .unscheduled_proposals a').first

        self.assertEquals('1', link.text)
        self.assertEquals(
            'http://example.com/opengever-meeting-committeecontainer/committee-1#submittedproposals',
            link.get('href'))

    @browsing
    def test_unscheduled_proposal_number_class(self, browser):
        dossier = create(Builder('dossier'))
        proposal_a = create(Builder('proposal')
                            .within(dossier)
                            .having(committee=self.committee_model))
        create(Builder('submitted_proposal').submitting(proposal_a))

        create(Builder('committee').within(self.container)
               .titled(u'Xenophoben-Kommission'))

        browser.login().open(self.container, view='tabbedview_view-committees')
        links = browser.css('#committees_view .unscheduled_proposals a')

        self.assertEquals('1', links[0].text)
        self.assertEquals('number unscheduled_number', links[0].get('class'))
        self.assertEquals('0', links[1].text)
        self.assertEquals('number', links[1].get('class'))

    @browsing
    def test_meetings_display(self, browser):
        meeting1 = create(Builder('meeting')
                          .having(committee=self.committee_model,
                                  start=self.localized_datetime(2015, 01, 01)))

        meeting2 = create(Builder('meeting')
                          .having(committee=self.committee_model,
                                  start=self.localized_datetime() + timedelta(days=1)))

        browser.login().open(self.container, view='tabbedview_view-committees')

        self.assertEquals(
            ['Last Meeting: Jan 01, 2015',
             'Next Meeting: {}'.format(meeting2.get_date())],
            browser.css('#committees_view .meetings li').text)

        last_meeting = browser.css('#committees_view .meetings li a')[0]
        next_meeting = browser.css('#committees_view .meetings li a')[1]

        self.assertEquals(meeting1.get_url(), last_meeting.get('href'))
        self.assertEquals(meeting2.get_url(), next_meeting.get('href'))
