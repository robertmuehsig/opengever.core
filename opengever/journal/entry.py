from ftw.journal.events.events import JournalEntryEvent
from opengever.base.oguid import Oguid
from opengever.journal import _
from persistent.dict import PersistentDict
from persistent.list import PersistentList
from plone import api
from zope.component import getUtility
from zope.event import notify
from zope.globalrequest import getRequest
from zope.i18n import translate
from zope.schema.interfaces import IVocabularyFactory


MANUAL_JOURNAL_ENTRY = 'manually-journal-entry'


class ManualJournalEntry(object):
    """Object to create and add a journal entry to a context.
    Its used by the ManualJournalEntry form.
    """

    def __init__(self, context, category, comment, contacts, documents):
        self.context = context
        self.request = getRequest()
        self.category = category
        self.comment = comment
        self.contacts = contacts
        self.documents = documents

    def save(self):
        entry = {'obj': self.context,
                 'action': PersistentDict({
                     'type': MANUAL_JOURNAL_ENTRY,
                     'title': self.get_title(),
                     'visible': True,
                     'documents': self.serialize_documents(),
                     'contacts': self.serialize_contacts()}),
                 'actor': api.user.get_current().getId(),
                 'comment': self.comment.encode('utf-8')}

        notify(JournalEntryEvent(**entry))

    def serialize_documents(self):
        """Returns a persistent list of dicts with the following data for for
        all documents:

        id: oguid
        title: document title
        """
        value = PersistentList()
        for doc in self.documents:
            value.append(PersistentDict(
                {'id': Oguid.for_object(doc).id, 'title': doc.title}))

        return value

    def serialize_contacts(self):
        """Returns a persistent list of dicts for all contacts.
        """
        value = PersistentList()
        for item in self.contacts:
            value.append(
                PersistentDict({'id': item.get_contact_id(),
                                'title': item.get_title()}))

        return value

    def get_title(self):
        msg = _(u'label_manual_journal_entry',
                default=u'Manual entry: ${category}',
                mapping={'category': self.get_category_title()})

        return translate(msg, context=getRequest())

    def get_category_title(self):
        voca_factory = getUtility(
            IVocabularyFactory,
            name='opengever.journal.manual_entry_categories')

        return voca_factory(self.context).getTerm(self.category).title
