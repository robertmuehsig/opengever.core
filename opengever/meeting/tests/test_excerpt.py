from ftw.builder import Builder
from ftw.builder import create
from ftw.testbrowser import browsing
from opengever.base.security import elevated_privileges
from opengever.document.interfaces import ICheckinCheckoutManager
from opengever.meeting.model import Excerpt
from opengever.testing import IntegrationTestCase
from opengever.trash.remover import Remover
from opengever.trash.trash import ITrashable
from opengever.trash.trash import TrashError
from operator import attrgetter
from zope.component import getMultiAdapter
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent
from z3c.relationfield.event import _relations


class TestTrashReturnedExcerpt(IntegrationTestCase):

    @browsing
    def test_trash_excerpt_is_forbidden_when_it_has_been_returned_to_proposal(self, browser):
        self.login(self.committee_responsible, browser)
        agenda_item = self.schedule_proposal(self.meeting, self.submitted_proposal)
        agenda_item.decide()
        excerpt1 = agenda_item.generate_excerpt('excerpt 1')

        ITrashable(excerpt1).trash()

        ITrashable(excerpt1).untrash()
        agenda_item.return_excerpt(excerpt1)

        with self.assertRaises(TrashError):
            ITrashable(excerpt1).trash()


class TestRemoveTrashedExcerpt(IntegrationTestCase):

    @browsing
    def test_remove_excerpt_for_adhoc_agendaitem_removes_entry_from_sql_database(self, browser):
        self.login(self.committee_responsible, browser)
        agenda_item = self.schedule_ad_hoc(self.meeting, 'Foo')
        agenda_item.decide()
        excerpt1 = agenda_item.generate_excerpt('excerpt 1')
        agenda_item.generate_excerpt('excerpt 2')

        self.assertEqual(2, len(agenda_item.get_excerpt_documents(include_trashed=True)))
        excerpts = Excerpt.query.filter(Excerpt.agenda_item_id == agenda_item.agenda_item_id).all()
        self.assertEqual(2, len(excerpts))

        ITrashable(excerpt1).trash()
        with elevated_privileges():
            Remover([excerpt1]).remove()

        self.assertEqual(1, len(agenda_item.get_excerpt_documents(include_trashed=True)))
        excerpts = Excerpt.query.filter(Excerpt.agenda_item_id == agenda_item.agenda_item_id).all()
        self.assertEqual(1, len(excerpts))

    @browsing
    def test_remove_excerpt_for_agendaitem_removes_relation_in_submitted_proposal(self, browser):
        self.login(self.committee_responsible, browser)
        agenda_item = self.schedule_proposal(self.meeting, self.submitted_proposal)
        agenda_item.decide()
        excerpt1 = agenda_item.generate_excerpt('excerpt 1')
        agenda_item.generate_excerpt('excerpt 2')

        self.assertEqual(2, len(self.submitted_proposal.excerpts))
        self.assertEqual(2, len(self.submitted_proposal.get_excerpts(include_trashed=True)))
        self.assertEqual(2, len(agenda_item.get_excerpt_documents(include_trashed=True)))
        self.assertEqual(2, len(list(_relations(self.submitted_proposal))))

        ITrashable(excerpt1).trash()
        with elevated_privileges():
            Remover([excerpt1]).remove()

        self.assertEqual(1, len(self.submitted_proposal.excerpts))
        self.assertEqual(1, len(self.submitted_proposal.get_excerpts(include_trashed=True)))
        self.assertEqual(1, len(agenda_item.get_excerpt_documents(include_trashed=True)))
        self.assertEqual(1, len(list(_relations(self.submitted_proposal))))


class TestSyncExcerpt(IntegrationTestCase):

    features = ('meeting',)

    def setUp(self):
        super(TestSyncExcerpt, self).setUp()

        # XXX OMG - this should be in the fixture somehow, or at least be
        # build-able in fewer lines.
        self.login(self.committee_responsible)

        self.document_in_dossier = self.document
        self.excerpt_in_dossier = create(
            Builder('generated_excerpt')
            .for_document(self.document_in_dossier))
        self.submitted_proposal.load_model().excerpt_document = self.excerpt_in_dossier

        self.document_in_proposal = create(
            Builder('document')
            .with_dummy_content()
            .within(self.submitted_proposal))
        self.excerpt_in_proposal = create(
            Builder('generated_excerpt')
            .for_document(self.document_in_proposal))
        self.submitted_proposal.load_model().submitted_excerpt_document = self.excerpt_in_proposal

    def test_updates_excerpt_in_dossier_after_checkin(self):
        self.assertEqual(None, self.document_in_proposal.get_current_version_id())
        self.assertEqual(None, self.document_in_dossier.get_current_version_id())
        manager = getMultiAdapter((self.document_in_proposal,
                                   self.portal.REQUEST),
                                  ICheckinCheckoutManager)
        manager.checkout()
        self.document_in_proposal.update_file(
            'foo bar',
            content_type='text/plain',
            filename=u'example.docx')
        manager.checkin()

        self.assertEqual(1, self.document_in_proposal.get_current_version_id())
        self.assertEqual(1, self.document_in_dossier.get_current_version_id())

    def test_updates_excerpt_in_dossier_after_revert(self):
        self.assertEqual(None, self.document_in_proposal.get_current_version_id())
        self.assertEqual(None, self.document_in_dossier.get_current_version_id())
        manager = getMultiAdapter((self.document_in_proposal,
                                   self.portal.REQUEST),
                                  ICheckinCheckoutManager)
        manager.checkout()
        self.document_in_proposal.update_file(
            'foo bar',
            content_type='text/plain',
            filename=u'example.docx')
        manager.checkin()

        manager.revert_to_version(0)
        self.assertEqual(2, self.document_in_proposal.get_current_version_id())
        self.assertEqual(2, self.document_in_dossier.get_current_version_id())

    def test_updates_excerpt_in_dossier_after_modification(self):
        self.assertEqual(None, self.document_in_dossier.get_current_version_id())
        self.document_in_proposal.update_file(
            'foo bar',
            filename=u'example.docx',
            content_type='text/plain')
        notify(ObjectModifiedEvent(self.document_in_proposal))

        self.assertEqual(1, self.document_in_dossier.get_current_version_id())


class TestExcerptOverview(IntegrationTestCase):

    features = ('meeting',)
    maxDiff = None

    @browsing
    def test_excerpt_overview_displays_link_to_proposal(self, browser):
        self.login(self.committee_responsible, browser)
        agenda_item = self.schedule_proposal(self.meeting, self.submitted_proposal)
        agenda_item.decide()
        excerpt1 = agenda_item.generate_excerpt('excerpt 1')
        agenda_item.return_excerpt(excerpt1)

        expected_fields = [
            'Title',
            'Document Date',
            'Document Type',
            'Author',
            'creator',
            'Description',
            'Foreign Reference',
            'Keywords',
            'Checked out',
            'File',
            'Digital Available',
            'Preserved as paper',
            'Date of receipt',
            'Date of delivery',
            'Related Documents',
            'Classification',
            'Privacy layer',
            'Public Trial',
            'Public trial statement',
            'Submitted with',
            'Created',
            'Modified',
            'Proposal',
            'Meeting'
        ]
        browser.open(excerpt1, view='tabbedview_view-overview')
        fields = dict(zip(
            browser.css('.documentMetadata th').text,
            map(attrgetter('innerHTML'), browser.css('.documentMetadata td')),
        ))
        self.assertItemsEqual(expected_fields, fields.keys())

        self.assertEquals(
            u'<a href="http://nohost/plone/opengever-meeting-committeecontainer'
            u'/committee-1/meeting-1/view" title="9. Sitzung der '
            u'Rechnungspr\xfcfungskommission" class="'
            u'contenttype-opengever-meeting-meeting">9. Sitzung der '
            u'Rechnungspr\xfcfungskommission</a>',
            fields['Meeting'],
            )
        self.assertEquals(
            u'<a href="http://nohost/plone/ordnungssystem/fuhrung/'
            u'vertrage-und-vereinbarungen/dossier-1/proposal-1" title="Vertr\xe4ge"'
            u' class="contenttype-opengever-meeting-proposal">Vertr\xe4ge</a>',
            fields['Proposal'])

    @browsing
    def test_excerpt_overview_hides_link_to_proposal_when_insufficient_privileges(self, browser):
        self.login(self.committee_responsible, browser)
        agenda_item = self.schedule_proposal(self.meeting, self.submitted_proposal)
        agenda_item.decide()
        excerpt1 = agenda_item.generate_excerpt('excerpt 1')
        agenda_item.return_excerpt(excerpt1)

        expected_fields = [
            'Title',
            'Document Date',
            'Document Type',
            'Author',
            'creator',
            'Description',
            'Foreign Reference',
            'Keywords',
            'Checked out',
            'File',
            'Digital Available',
            'Preserved as paper',
            'Date of receipt',
            'Date of delivery',
            'Related Documents',
            'Classification',
            'Privacy layer',
            'Public Trial',
            'Public trial statement',
            'Submitted with',
            'Created',
            'Modified'
        ]
        self.login(self.regular_user, browser)
        browser.open(excerpt1, view='tabbedview_view-overview')
        fields = dict(zip(
            browser.css('.documentMetadata th').text,
            map(attrgetter('innerHTML'), browser.css('.documentMetadata td')),
        ))
        self.assertItemsEqual(expected_fields, fields.keys())
