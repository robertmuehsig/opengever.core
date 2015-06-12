from datetime import datetime
from datetime import timedelta
from ftw.builder import Builder
from ftw.builder import create
from ftw.testbrowser import browsing
from opengever.testing import FunctionalTestCase


class TestCommitteeTabs(FunctionalTestCase):

    def setUp(self):
        super(TestCommitteeTabs, self).setUp()

        self.maxDiff = None
        self.container = create(Builder('committee_container'))
        self.committee = create(Builder('committee')
                                .within(self.container)
                                .titled(u'Kleiner Burgerrat'))
        self.committee_model = self.committee.load_model()

        create(Builder('meeting')
               .having(committee=self.committee_model,
                       location='Bern',
                       start=datetime(2015, 01, 01, 12, 00),
                       end=datetime(2015, 01, 03, 18, 00)))

        create(Builder('meeting')
               .having(committee=self.committee_model,
                       location='Bern',
                       start=datetime(2015, 06, 13, 9, 30)))

    @browsing
    def test_meeting_listing(self, browser):
        browser.login().open(self.committee, view='tabbedview_view-meetings')

        table = browser.css('.listing').first
        self.assertEquals([
            {'Title': 'Bern, Jan 01, 2015',
             'Date': 'Jan 01, 2015',
             'Location': 'Bern',
             'From': '12:00 PM',
             'To': '06:00 PM'},
            {'Title': 'Bern, Jun 13, 2015',
             'Date': 'Jun 13, 2015',
             'Location': 'Bern',
             'From': '09:30 AM',
             'To': ''}
        ], table.dicts())
