from ftw.builder import Builder
from ftw.builder import create
from opengever.ogds.base.Extensions.plugins import activate_request_layer
from opengever.ogds.base.interfaces import IInternalOpengeverRequestLayer
from opengever.task.adapters import IResponseContainer
from opengever.task.interfaces import ICommentResponseSyncerSender
from opengever.task.interfaces import IResponseSyncerSender
from opengever.task.syncer import BaseResponseSyncerReceiver
from opengever.task.syncer import BaseResponseSyncerSender
from opengever.task.syncer import CommentResponseSyncerSender
from opengever.task.syncer import ResponseSyncerSenderException
from opengever.testing import FunctionalTestCase
from zExceptions import Forbidden
from zope.component import getMultiAdapter
from zope.interface.verify import verifyClass


class MockDispatchRequest(object):

    def __init__(self, response):
        self.requests = []
        self.response = response

    def __call__(self, target_admin_unit_id, viewname, path, data):
        self.requests.append({
            'target_admin_unit_id': target_admin_unit_id,
            'viewname': viewname,
            'path': path,
            'data': data,
        })

        return self

    def read(self):
        return self.response


class TestBaseResponseSyncerSender(FunctionalTestCase):

    def _mock_dispatch_request(self, sender, response):
        mock = MockDispatchRequest(response=response)
        sender._dispatch_request = mock
        return mock

    def test_verify_interfaces(self):
        verifyClass(IResponseSyncerSender, BaseResponseSyncerSender)

    def test_sync_related_tasks_raises_an_exception_if_syncing_failed(self):
        predecessor = create(Builder('task').in_state('task-state-resolved'))
        create(Builder('task').successor_from(predecessor))

        sender = BaseResponseSyncerSender(predecessor, self.request)
        sender.TARGET_SYNC_VIEW_NAME = "NOT_EXISTING_VIEW"

        self._mock_dispatch_request(sender, 'NOT_FOUND')

        with self.assertRaises(ResponseSyncerSenderException):
            sender.sync_related_tasks('', '')

    def test_sync_related_tasks_performs_a_request_for_each_successor(self):
        predecessor = create(Builder('task').in_state('task-state-resolved'))
        create(Builder('task').successor_from(predecessor))
        create(Builder('task').successor_from(predecessor))

        sender = BaseResponseSyncerSender(predecessor, self.request)
        sender.TARGET_SYNC_VIEW_NAME = "SYNC_TASK"
        mock_request = self._mock_dispatch_request(sender, 'OK')

        sender.sync_related_tasks('test-transition', u't\xe4st')

        self.assertEqual(
            2, len(mock_request.requests),
            "The syncer should have made two requests. One for each successor")

        self.assertItemsEqual(
            [
                {'data': {'text': 't\xc3\xa4st', 'transition': 'test-transition'},
                 'path': u'task-2',
                 'target_admin_unit_id': u'client1',
                 'viewname': 'SYNC_TASK'},
                {'data': {'text': 't\xc3\xa4st', 'transition': 'test-transition'},
                 'path': u'task-3',
                 'target_admin_unit_id': u'client1',
                 'viewname': 'SYNC_TASK'}
            ],
            mock_request.requests
        )

    def test_sync_related_task_raises_an_exception_if_syncing_failed(self):
        predecessor = create(Builder('task').in_state('task-state-resolved'))
        create(Builder('task').successor_from(predecessor))

        sender = BaseResponseSyncerSender(predecessor, self.request)
        sender.TARGET_SYNC_VIEW_NAME = "NOT_EXISTING_VIEW"

        self._mock_dispatch_request(sender, 'NOT_FOUND')

        task = sender.get_related_tasks_to_sync()[0]
        with self.assertRaises(ResponseSyncerSenderException):
            sender.sync_related_task(task, '', '')

    def test_sync_related_task_performs_a_request_to_the_target_sync_view_name(self):
        predecessor = create(Builder('task').in_state('task-state-resolved'))
        create(Builder('task').successor_from(predecessor))

        sender = BaseResponseSyncerSender(predecessor, self.request)
        sender.TARGET_SYNC_VIEW_NAME = "SYNC_TASK"
        mock_request = self._mock_dispatch_request(sender, 'OK')

        task = sender.get_related_tasks_to_sync()[0]
        sender.sync_related_task(task, 'test-transition', u't\xe4st', firstname='james')

        self.assertItemsEqual(
            [
                {'data': {'text': 't\xc3\xa4st',
                          'transition': 'test-transition',
                          'firstname': 'james'},
                 'path': u'task-2',
                 'target_admin_unit_id': u'client1',
                 'viewname': 'SYNC_TASK'},
            ],
            mock_request.requests
        )

    def test_get_related_tasks_to_sync_returns_empty_list_if_there_are_no_successors_or_predecessors(self):
        predecessor = create(Builder('task').in_state('task-state-resolved'))

        sender = BaseResponseSyncerSender(predecessor, self.request)

        self.assertEqual([], sender.get_related_tasks_to_sync())

    def test_get_related_tasks_to_sync_returns_all_successors_in_a_list(self):
        predecessor = create(Builder('task').in_state('task-state-resolved'))
        successor_1 = create(Builder('task').successor_from(predecessor))
        successor_2 = create(Builder('task').successor_from(predecessor))

        sender = BaseResponseSyncerSender(predecessor, self.request)

        tasks = sender.get_related_tasks_to_sync()

        self.assertItemsEqual([
            successor_1.get_sql_object(), successor_2.get_sql_object()],
            tasks)

    def test_get_related_tasks_to_sync_returns_predecessor_in_a_list(self):
        predecessor = create(Builder('task').in_state('task-state-resolved'))
        successor_1 = create(Builder('task').successor_from(predecessor))

        sender = BaseResponseSyncerSender(successor_1, self.request)

        tasks = sender.get_related_tasks_to_sync()

        self.assertEqual([predecessor.get_sql_object()], tasks)

    def test_extend_payload_updates_payload_with_kwargs(self):
        sender = BaseResponseSyncerSender(object(), self.request)

        payload = {'text': 'My text'}
        sender.extend_payload(payload, object(), firstname="james", lastname="bond")

        self.assertEqual({
            'text': 'My text',
            'firstname': 'james',
            'lastname': 'bond'},
            payload)

    def test_raise_sync_exception_raises_an_exception(self):
        sender = BaseResponseSyncerSender(object(), self.request)

        with self.assertRaises(ResponseSyncerSenderException):
            sender.raise_sync_exception(object(), '', '')


class TestCommentResponseSyncerSender(FunctionalTestCase):

    def test_verify_interfaces(self):
        verifyClass(ICommentResponseSyncerSender, CommentResponseSyncerSender)

    def test_raises_sync_exception_raises_comment_specific_exception_message(self):
        predecessor = create(Builder('task').in_state('task-state-resolved'))

        sender = CommentResponseSyncerSender(object(), self.request)

        with self.assertRaises(ResponseSyncerSenderException) as exception:
            sender.raise_sync_exception(
                predecessor.get_sql_object(),
                'comment-transition', 'some text')

        self.assertEqual(
            'Could not add comment on task on remote admin unit client1 (task-1)',
            str(exception.exception))


class TestBaseResponseSyncerReceiver(FunctionalTestCase):

    def prepare_request(self, task, **kwargs):
        for key, value in kwargs.items():
            task.REQUEST.set(key, value)

        activate_request_layer(task.REQUEST, IInternalOpengeverRequestLayer)

    def test_receive_view_raise_forbidden_for_none_internal_requests(self):
        task = create(Builder('task'))

        with self.assertRaises(Forbidden):
            BaseResponseSyncerReceiver(task, self.request)()

    def test_adds_a_response_to_the_given_context(self):
        task = create(Builder('task'))

        self.prepare_request(task, text=u'Response text',
                             transition='base-response')

        BaseResponseSyncerReceiver(task, self.request)()

        response_container = IResponseContainer(task)
        self.assertEqual(1, len(response_container))

        response = response_container[0]

        self.assertEqual('Response text', response.text)
        self.assertEqual('base-response', response.transition)

    def test_do_not_add_the_same_response_twice_but_return_ok_anyway(self):
        task = create(Builder('task').in_state('task-state-in-progress'))

        self.prepare_request(task, text=u'Response text!',
                             transition='base-response')

        receiver = BaseResponseSyncerReceiver(task, self.request)

        self.assertEquals('OK', receiver())
        self.assertEquals('OK', receiver())

        response_container = IResponseContainer(task)
        self.assertEqual(
            1, len(response_container),
            "Should not add the same response twice")


class TestCommentSyncer(FunctionalTestCase):

    def setUp(self):
        super(TestCommentSyncer, self).setUp()
        activate_request_layer(self.portal.REQUEST,
                               IInternalOpengeverRequestLayer)

    def test_sync_comment_on_successor_to_predecessor(self):
        predecessor = create(Builder('task'))
        successor = create(Builder('task').successor_from(predecessor))

        sender = getMultiAdapter((successor, successor.REQUEST),
                                 ICommentResponseSyncerSender)

        sender.sync_related_tasks('task-commented', text=u'We need more stuff!')

        response_container = IResponseContainer(predecessor)
        self.assertEqual(1, len(response_container))

        response = response_container[0]

        self.assertEqual('We need more stuff!', response.text)
        self.assertEqual('task-commented', response.transition)

    def test_sync_comment_on_predecessor_to_successor(self):
        predecessor = create(Builder('task'))
        successor = create(Builder('task')
                           .successor_from(predecessor))

        sender = getMultiAdapter((predecessor, predecessor.REQUEST),
                                 ICommentResponseSyncerSender)

        sender.sync_related_tasks('task-commented', text=u'We need more stuff!')

        response_container = IResponseContainer(successor)
        self.assertEqual(1, len(response_container))

        response = response_container[0]

        self.assertEqual('We need more stuff!', response.text)
        self.assertEqual('task-commented', response.transition)
