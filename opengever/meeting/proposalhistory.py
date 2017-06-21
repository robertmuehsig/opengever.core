from BTrees.OOBTree import OOBTree
from opengever.base.date_time import utcnow_tz_aware
from opengever.meeting import _
from opengever.ogds.base.actor import Actor
from persistent.mapping import PersistentMapping
from plone import api
from uuid import uuid4
from zope.annotation.interfaces import IAnnotations


class ProposalHistory(object):
    """Adapter to keep track of a proposals history.

    Lists history records for an object and crates new ones. Records are stored
    in the objects annotations. Keeps a registry of supported history entries.

    History records are stored with their timestamp as key and their data
    as value.
    """
    record_classes = {}
    annotation_key = 'object_history'

    @classmethod
    def register(cls, clazz):
        assert clazz.name not in cls.record_classes
        cls.record_classes[clazz.name] = clazz

    def __init__(self, context):
        self.context = context

    def __iter__(self):
        # fallback, old history entries, will mess up order, will go away
        for record in self.context.load_model().history_records:
            yield record

        history = IAnnotations(self.context).get(self.annotation_key)
        if history is None:
            history = OOBTree()

        for key, val in history.items():
            name = val.get('name')
            if not name:
                continue
            clazz = self.record_classes.get(name)
            if not clazz:
                continue

            yield(clazz(self.context, timestamp=key, data=val))

    def append_record(self, name, timestamp=None):
        clazz = self.record_classes[name]

        history = IAnnotations(self.context).setdefault(
            self.annotation_key, OOBTree())
        entry = clazz(self.context, timestamp=timestamp)
        entry.append_to(history)

        return entry


class BaseHistoryRecord(object):
    """Basic implementation of a history record.

    Contains required data and abstract implementation.
    """
    name = None

    def __init__(self, context, timestamp=None, data=None):
        self.context = context

        if timestamp is None:
            timestamp = utcnow_tz_aware()
        self.timestamp = timestamp

        if data is None:
            data = self.init_data()
        self.data = data

    def init_data(self):
        return PersistentMapping(
            created=self.timestamp,
            userid=api.user.get_current().getId(),
            name=self.name,
            id=uuid4(),
        )

    def append_to(self, history):
        if self.timestamp in history:
            return  # XXX raise?

        history[self.timestamp] = self.data

    def message(self):
        raise NotImplementedError

    @property
    def css_class(self):
        return self.name

    @property
    def created(self):
        return self.data['created']

    @property
    def text(self):
        return self.data.get('text')

    def get_actor_link(self):
        return Actor.lookup(self.data['userid']).get_link()


class ProposalCreated(BaseHistoryRecord):
    """A Proposal has been created."""

    name = 'created'

    def message(self):
        return _(u'proposal_history_label_created',
                 u'Created by ${user}',
                 mapping={'user': self.get_actor_link()})

ProposalHistory.register(ProposalCreated)
