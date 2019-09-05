from datetime import datetime
from ftw.testbrowser import browsing
from ftw.testing import freeze
from opengever.base.response import IResponseContainer
from opengever.testing import IntegrationTestCase
from plone.restapi.serializer.converters import json_compatible
import json


class TestTaskSerialization(IntegrationTestCase):

    @browsing
    def test_task_contains_a_list_of_responses(self, browser):
        self.login(self.regular_user, browser=browser)
        browser.open(self.task, method="GET", headers=self.api_headers)
        self.maxDiff = None
        responses = browser.json['responses']
        self.assertEquals(2, len(responses))
        self.assertEquals(
            {u'@id': u'http://nohost/plone/ordnungssystem/fuhrung/vertrage-und-vereinbarungen/dossier-1/task-1/@responses/1472652213000000',
             u'added_objects': [
                 {u'@id': self.subtask.absolute_url(),
                  u'@type': u'opengever.task.task',
                  u'description': u'',
                  u'review_state': u'task-state-resolved',
                  u'title': self.subtask.title}
             ],
             u'changes': [],
             u'created': json_compatible(self.subtask.created().utcdatetime()),
             u'creator': {u'title': u'Ziegler Robert', u'token': u'robert.ziegler'},
             u'mimetype': u'',
             u'related_items': [],
             u'rendered_text': u'',
             u'response_id': 1472652213000000,
             u'response_type': u'default',
             u'successor_oguid': u'',
             u'text': u'',
             u'transition': u'transition-add-subtask'},
            responses[0])

    @browsing
    def test_task_response_contains_changes(self, browser):
        # Modify deadline to have a response containing field changes
        self.login(self.dossier_responsible, browser=browser)
        browser.open(self.task)
        browser.click_on('task-transition-modify-deadline')
        browser.fill({'Response': 'Nicht mehr dringend',
                      'New Deadline': '1.1.2023'})
        browser.click_on('Save')

        self.login(self.regular_user, browser=browser)
        browser.open(self.task, method="GET", headers=self.api_headers)

        response = browser.json['responses'][-1]
        self.assertEquals(
            self.dossier_responsible.id, response['creator'].get('token'))
        self.assertEquals(
            u'task-transition-modify-deadline', response['transition'])
        self.assertEquals(
            [{u'field_id': u'deadline', u'field_title': u'Deadline',
              u'after': u'2023-01-01', u'before': u'2016-11-01'}],
            response['changes'])

    @browsing
    def test_response_key_contains_empty_list_for_task_without_responses(self, browser):
        self.login(self.regular_user, browser=browser)

        browser.open(self.inbox_task, method="GET", headers=self.api_headers)
        self.assertEquals([], browser.json['responses'])

    @browsing
    def test_fowardings_contains_a_list_of_responses(self, browser):
        self.login(self.secretariat_user, browser=browser)

        browser.open(
            self.inbox_forwarding, method="GET", headers=self.api_headers)
        self.assertEquals(
            [{u'@id': u'http://nohost/plone/eingangskorb/forwarding-1/@responses/1472630853000000',
              u'response_id': 1472630853000000,
              u'response_type': u'default',
              u'added_objects': [{
                u'@id': u'http://nohost/plone/eingangskorb/forwarding-1/document-13',
                u'@type': u'opengever.document.document',
                u'description': u'',
                u'review_state': u'document-state-draft',
                u'title': u'Dokument im Eingangsk\xf6rbliweiterleitung'}],
              u'changes': [],
              u'creator': {
                  u'token': u'nicole.kohler',
                  u'title': u'Kohler Nicole'},
              u'created': u'2016-08-31T10:07:33',
              u'related_items': [],
              u'text': u'',
              u'mimetype': u'',
              u'successor_oguid': u'',
              u'rendered_text': u'',
              u'transition': u'transition-add-document'}],
            browser.json['responses'])

    @browsing
    def test_adding_a_response_sucessful(self, browser):
        self.login(self.regular_user, browser=browser)

        current_responses_count = len(IResponseContainer(self.task))

        with freeze(datetime(2016, 12, 9, 9, 40)):
            url = '{}/@responses'.format(self.task.absolute_url())
            browser.open(url, method="POST", headers=self.api_headers,
                         data=json.dumps({'text': u'Angebot \xfcberpr\xfcft'}))

        self.assertEquals(current_responses_count + 1,
                          len(IResponseContainer(self.task)))

        self.assertEquals(201, browser.status_code)
        self.maxDiff = None
        self.assertEquals(
            {u'@id': '{}/@responses/1481272800000000'.format(self.task.absolute_url()),
             'response_id': 1481272800000000,
             'response_type': 'comment',
             u'created': u'2016-12-09T09:40:00',
             u'changes': [],
             u'creator': {
                 u'token': self.regular_user.id,
                 u'title': u'B\xe4rfuss K\xe4thi'},
             u'text': u'Angebot \xfcberpr\xfcft',
             u'transition': u'',
             u'successor_oguid': u'',
             u'rendered_text': u'',
             u'related_items': [],
             u'mimetype': u'',
             u'added_objects': []},
            browser.json)
