from opengever.testing import IntegrationTestCase
from ftw.testbrowser import browsing


class TestAddPeriodXXX(IntegrationTestCase):

    features = ('meeting',)

    @browsing
    def test_add_period_in_browser(self, browser):
        self.login(self.committee_responsible, browser)

        browser.open(self.committee, view='++add++opengever.meeting.period')
