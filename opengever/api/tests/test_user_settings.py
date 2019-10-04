from ftw.testbrowser import browsing
from opengever.base.model import create_session
from opengever.ogds.models.user_settings import UserSettings
from opengever.testing import IntegrationTestCase
from zExceptions import Unauthorized
import json


class TestUsersSettingsGet(IntegrationTestCase):

    @browsing
    def test_returns_default_settings_for_users_without_personal_settings(self, browser):
        self.login(self.regular_user, browser)
        browser.open('{}/@user-settings'.format(self.portal.absolute_url()),
                     headers=self.api_headers)

        self.assertEquals(
            {"notify_inbox_actions": True,
             "seen_tours": [],
             "notify_own_actions": False},
            browser.json)

    @browsing
    def test_returns_personal_settings(self, browser):
        self.login(self.regular_user, browser)
        setting = UserSettings(
            userid=self.regular_user.id,
            notify_own_actions=True,
            notify_inbox_actions=True,
            _seen_tours=json.dumps(
                ['gever.introduction', 'gever.release-2019.3']))
        create_session().add(setting)

        browser.open('{}/@user-settings'.format(self.portal.absolute_url()),
                     headers=self.api_headers)

        self.assertEquals(
            {u'notify_inbox_actions': True,
             u'seen_tours': [u'gever.introduction', u'gever.release-2019.3'],
             u'notify_own_actions': True},
            browser.json)


class TestUsersSettingsPatch(IntegrationTestCase):

    @browsing
    def test_creates_settings_if_not_exists(self, browser):
        self.login(self.regular_user, browser)

        self.assertEquals(
            0, UserSettings.query.filter_by(userid=self.regular_user.id).count())

        data = json.dumps(
            {'seen_tours': ['gever.introduction', 'gever.release_2019.3']})
        browser.open('{}/@user-settings'.format(self.portal.absolute_url()),
                     data=data, method='PATCH', headers=self.api_headers)

        self.assertEquals(204, browser.status_code)

        setting = UserSettings.query.filter_by(userid=self.regular_user.id).one()
        self.assertEquals(
            json.dumps(['gever.introduction', 'gever.release_2019.3']),
            setting._seen_tours)

    @browsing
    def test_respects_prefer_header(self, browser):
        self.login(self.regular_user, browser)

        headers = self.api_headers
        headers.update({'Prefer': 'return=representation'})

        data = json.dumps(
            {'seen_tours': ['gever.introduction', 'gever.release-2019.3']})
        browser.open('{}/@user-settings'.format(self.portal.absolute_url()),
                     data=data, method='PATCH', headers=headers)

        self.assertEquals(200, browser.status_code)
        self.assertEquals(
            {"notify_inbox_actions": True,
             "seen_tours": ['gever.introduction', 'gever.release-2019.3'],
             "notify_own_actions": False},
            browser.json)
