from ftw.builder import Builder
from ftw.builder import create
from ftw.testbrowser import browsing
from opengever.activity.hooks import DEFAULT_SETTINGS
from opengever.activity.model.settings import NotificationSetting
from opengever.activity.roles import TASK_ISSUER_ROLE
from opengever.activity.roles import TASK_RESPONSIBLE_ROLE
from opengever.ogds.models.user_settings import UserSettings
from opengever.testing import IntegrationTestCase
import json

DEFAULT_CONFIGURATIONS = [{"id": "notify_own_actions", "value": False},
                          {"id": "notify_inbox_actions", "value": True}]


class TestListSettings(IntegrationTestCase):

    features = ('activity', )

    @browsing
    def test_list_all_settings_except_aliased_objects(self, browser):
        self.login(self.regular_user, browser=browser)
        browser.open(self.portal, view='notification-settings/list')

        activities = browser.json.get('activities')

        aliased = ['task-transition-open-tested-and-closed',
                   'task-transition-resolved-tested-and-closed',
                   'task-transition-open-resolved',
                   'task-transition-rejected-open',
                   'task-transition-skipped-open',
                   'task-transition-planned-skipped',
                   'disposition-transition-appraised-to-closed']

        self.assertItemsEqual(
            [item.get('kind') for item in activities],
            [item.get('kind') for item in DEFAULT_SETTINGS
             if item.get('kind') not in aliased])

        task_added = [item for item in activities if item.get('kind') == 'task-added'][0]
        self.assertEquals({u'task_issuer': False, u'task_responsible': True},
                          task_added['mail'])
        self.assertEquals({u'task_issuer': True, u'task_responsible': True},
                          task_added['badge'])
        self.assertEquals('default', task_added['setting_type'])

    @browsing
    def test_list_returns_personal_setting_if_exists(self, browser):
        create(Builder('notification_setting')
               .having(kind='task-transition-open-in-progress',
                       userid=self.regular_user.getId(),
                       mail_notification_roles=[TASK_RESPONSIBLE_ROLE],
                       badge_notification_roles=[TASK_ISSUER_ROLE,
                                                 TASK_RESPONSIBLE_ROLE],
                       digest_notification_roles=[TASK_ISSUER_ROLE]))

        self.login(self.regular_user, browser=browser)
        browser.open(self.portal, view='notification-settings/list')

        activities = browser.json.get('activities')
        accept = [
            item for item in activities
            if item.get('kind') == 'task-transition-open-in-progress'][0]

        self.assertEquals({u'task_issuer': False, u'task_responsible': True},
                          accept['mail'])
        self.assertEquals({u'task_issuer': True, u'task_responsible': True},
                          accept['badge'])
        self.assertEquals({u'task_issuer': True, u'task_responsible': False},
                          accept['digest'])
        self.assertEquals('personal', accept['setting_type'])

    @browsing
    def test_list_all_configurations(self, browser):
        self.login(self.regular_user, browser=browser)
        browser.open(self.portal, view='notification-settings/list')

        configurations = browser.json.get('configurations')

        self.assertItemsEqual(
            [item.get('id') for item in configurations],
            [item.get('id') for item in DEFAULT_CONFIGURATIONS])

        configurations.sort(key=lambda item: item['id'])
        DEFAULT_CONFIGURATIONS.sort(key=lambda item: item['id'])

        for default, config in zip(DEFAULT_CONFIGURATIONS, configurations):
            self.assertEqual(default.get('value'), config.get('value'))
            self.assertEqual('default', config.get('setting_type'))


class TestSaveSettings(IntegrationTestCase):

    features = ('activity', )

    data = {'kind': 'task-added',
            'mail': json.dumps([TASK_RESPONSIBLE_ROLE, TASK_ISSUER_ROLE]),
            'badge': json.dumps([TASK_ISSUER_ROLE]),
            'digest': json.dumps([TASK_RESPONSIBLE_ROLE])}

    @browsing
    def test_save_setting_raises_keyerror_when_parameter_is_missing(self, browser):
        self.login(self.regular_user, browser=browser)

        with browser.expect_http_error(503):
            browser.open(
                self.portal, view='notification-settings/save',
                data={key: self.data[key] for key in self.data if key != 'kind'})

        with browser.expect_http_error(503):
            browser.open(
                self.portal, view='notification-settings/save',
                data={key: self.data[key] for key in self.data if key != 'mail'})

        with browser.expect_http_error(503):
            browser.open(
                self.portal, view='notification-settings/save',
                data={key: self.data[key] for key in self.data if key != 'badge'})

        with browser.expect_http_error(503):
            browser.open(
                self.portal, view='notification-settings/save',
                data={key: self.data[key] for key in self.data if key != 'digest'})

    @browsing
    def test_save_setting_adds_personal_setting(self, browser):
        self.login(self.regular_user, browser=browser)

        browser.open(self.portal, view='notification-settings/save', data=self.data)

        settings = NotificationSetting.query.filter_by(userid=self.regular_user.getId()).all()
        self.assertEquals(1, len(settings))

        self.assertEquals('task-added', settings[0].kind)
        self.assertEquals(frozenset([TASK_RESPONSIBLE_ROLE, TASK_ISSUER_ROLE]),
                          settings[0].mail_notification_roles)
        self.assertEquals(frozenset([TASK_ISSUER_ROLE]),
                          settings[0].badge_notification_roles)
        self.assertEquals(frozenset([TASK_RESPONSIBLE_ROLE]),
                          settings[0].digest_notification_roles)

    @browsing
    def test_save_adds_personal_setting_also_for_aliased_kinds(self, browser):
        self.login(self.regular_user, browser=browser)

        data = self.data.copy()
        data['kind'] = 'task-transition-in-progress-tested-and-closed'

        browser.open(self.portal, view='notification-settings/save', data=data)

        settings = NotificationSetting.query.filter_by(
            userid=self.regular_user.getId()).all()

        self.assertEquals(3, len(settings))
        self.assertEquals(
            [u'task-transition-in-progress-tested-and-closed',
             u'task-transition-open-tested-and-closed',
             u'task-transition-resolved-tested-and-closed'],
            [setting.kind for setting in settings])

        self.assertEquals(frozenset([TASK_RESPONSIBLE_ROLE, TASK_ISSUER_ROLE]),
                          settings[1].mail_notification_roles)
        self.assertEquals(frozenset([TASK_ISSUER_ROLE]),
                          settings[1].badge_notification_roles)

    @browsing
    def test_save_updates_personal_setting_when_exists(self, browser):
        create(Builder('notification_setting')
               .having(kind='task-added',
                       userid=self.regular_user.getId(),
                       mail_notification_roles=[],
                       badge_notification_roles=[],
                       digest_notification_roles=[]))

        self.login(self.regular_user, browser=browser)
        browser.open(self.portal, view='notification-settings/save', data=self.data)

        settings = NotificationSetting.query.filter_by(userid=self.regular_user.getId()).all()
        self.assertEquals(1, len(settings))

        self.assertEquals('task-added', settings[0].kind)
        self.assertEquals(frozenset([TASK_RESPONSIBLE_ROLE, TASK_ISSUER_ROLE]),
                          settings[0].mail_notification_roles)
        self.assertEquals(frozenset([TASK_ISSUER_ROLE]),
                          settings[0].badge_notification_roles)
        self.assertEquals(frozenset([TASK_RESPONSIBLE_ROLE]),
                          settings[0].digest_notification_roles)


class TestResetSetting(IntegrationTestCase):

    features = ('activity', )

    @browsing
    def test_reset_removes_personal_setting_when_exists(self, browser):
        create(Builder('notification_setting')
               .having(kind='task-added',
                       userid=self.regular_user.getId(),
                       mail_notification_roles=[],
                       badge_notification_roles=[],
                       digest_notification_roles=[]))

        query = NotificationSetting.query.filter_by(userid=self.regular_user.getId())
        self.assertEquals(1, query.count())

        self.login(self.regular_user, browser=browser)
        browser.open(self.portal, view='notification-settings/reset',
                     data={'kind': 'task-added'})

        self.assertEquals(0, query.count())

    @browsing
    def test_reset_removes_also_aliased_settings_when_exists(self, browser):
        for kind in ['task-transition-in-progress-tested-and-closed',
                     'task-transition-open-tested-and-closed',
                     'task-transition-resolved-tested-and-closed']:
            create(Builder('notification_setting')
                   .having(kind=kind,
                           userid=self.regular_user.getId(),
                           mail_notification_roles=[],
                           badge_notification_roles=[]))

        query = NotificationSetting.query.filter_by(userid=self.regular_user.getId())
        self.assertEquals(3, query.count())

        self.login(self.regular_user, browser=browser)
        browser.open(self.portal, view='notification-settings/reset',
                     data={'kind': 'task-transition-in-progress-tested-and-closed'})

        self.assertEquals(0, query.count())


class TestSaveUserSetting(IntegrationTestCase):

    features = ('activity', )

    @browsing
    def test_save_notify_own_action_user_setting(self, browser):
        self.login(self.regular_user, browser=browser)

        config = UserSettings.get_setting_for_user(
            self.regular_user.id, 'notify_own_actions')
        self.assertFalse(config)

        browser.open(self.portal,
                     view='notification-settings/save_user_setting',
                     data={'config_name': 'notify_own_actions', 'value': 'true'})

        config = UserSettings.get_setting_for_user(
            self.regular_user.id, 'notify_own_actions')
        self.assertTrue(config)

    @browsing
    def test_save_notify_inbox_action_user_setting(self, browser):
        self.login(self.regular_user, browser=browser)

        config = UserSettings.get_setting_for_user(
            self.regular_user.id, 'notify_inbox_actions')
        self.assertTrue(config)

        browser.open(self.portal,
                     view='notification-settings/save_user_setting',
                     data={'config_name': 'notify_inbox_actions', 'value': 'false'})

        config = UserSettings.get_setting_for_user(
            self.regular_user.id, 'notify_inbox_actions')
        self.assertFalse(config)


class TestResetUserSetting(IntegrationTestCase):

    features = ('activity', )

    @browsing
    def test_reset_notify_own_action_user_setting(self, browser):
        self.login(self.regular_user, browser=browser)

        UserSettings.save_setting_for_user(
            self.regular_user.id, 'notify_own_actions', True)

        self.assertTrue(UserSettings.get_setting_for_user(
            self.regular_user.id, 'notify_own_actions'))

        browser.open(self.portal,
                     view='notification-settings/reset_user_setting',
                     data={'config_name': 'notify_own_actions'})

        self.assertFalse(UserSettings.get_setting_for_user(
            self.regular_user.id, 'notify_own_actions'))

    @browsing
    def test_reset_notify_inbox_action_user_setting(self, browser):
        self.login(self.regular_user, browser=browser)

        UserSettings.save_setting_for_user(
            self.regular_user.id, 'notify_inbox_actions', False)

        self.assertFalse(UserSettings.get_setting_for_user(
            self.regular_user.id, 'notify_inbox_actions'))

        browser.open(self.portal,
                     view='notification-settings/reset_user_setting',
                     data={'config_name': 'notify_inbox_actions'})

        self.assertTrue(UserSettings.get_setting_for_user(
            self.regular_user.id, 'notify_inbox_actions'))
