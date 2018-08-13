from ftw.testbrowser import browsing
from opengever.base.interfaces import IReferenceNumber
from opengever.base.interfaces import ISequenceNumber
from opengever.bumblebee.browser.overlay import BumblebeeBaseDocumentOverlay
from opengever.bumblebee.interfaces import IBumblebeeOverlay
from opengever.bumblebee.interfaces import IVersionedContextMarker
from opengever.testing import IntegrationTestCase
from plone.locking.interfaces import IRefreshableLockable
from plone.namedfile.file import NamedBlobFile
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.interface import alsoProvides
from zope.interface.verify import verifyClass


class TestAdapterRegisteredProperly(IntegrationTestCase):
    """Test bumblebee overlay adapter registrations."""

    features = (
        'bumblebee',
        )

    def test_get_overlay_adapter_for_documents(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        self.assertIsInstance(adapter, BumblebeeBaseDocumentOverlay)

    def test_verify_implemented_interfaces(self):
        verifyClass(IBumblebeeOverlay, BumblebeeBaseDocumentOverlay)


class TestGetPreviewPdfUrl(IntegrationTestCase):
    """Test generating a link to the bumblebee instance."""

    features = (
        'bumblebee',
        )

    def test_returns_preview_pdf_url_as_string(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.empty_document, self.request), IBumblebeeOverlay)
        self.assertEqual(
            'http://nohost/plone/++resource++opengever.bumblebee.resources/fallback_not_digitally_available.svg',
            adapter.get_preview_pdf_url(),
            )


class TestGetOpenAsPdfLink(IntegrationTestCase):
    """Test the integrity of generated bumblebee links."""

    features = (
        'bumblebee',
        )

    def test_returns_pdf_url_as_string(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        self.assertEqual(
            '{}/bumblebee-open-pdf?filename=Vertraegsentwurf.pdf'.format(self.document.absolute_url()),
            adapter.get_open_as_pdf_url(),
            )

    def test_returns_none_if_no_mimetype_is_available(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.empty_document, self.request), IBumblebeeOverlay)
        self.assertIsNone(adapter.get_open_as_pdf_url())

    def test_returns_none_if_mimetype_is_not_supported(self):
        self.login(self.regular_user)
        self.document.file = NamedBlobFile(
            data=u'T\xc3\xa4stfil\xc3\xa9',
            contentType='test/notsupported',
            filename=u'test.notsupported',
            )
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        self.assertIsNone(adapter.get_open_as_pdf_url())


class TestGetPdfFilename(IntegrationTestCase):
    """Test we generate bumblebee filenames correctly."""

    features = (
        'bumblebee',
        )

    def test_changes_filename_extension_to_pdf_and_returns_filename(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        self.assertEqual('Vertraegsentwurf.docx', self.document.file.filename)
        self.assertEqual('Vertraegsentwurf.pdf', adapter._get_pdf_filename())

    def test_returns_none_if_no_file_is_given(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.empty_document, self.request), IBumblebeeOverlay)
        self.assertIsNone(adapter._get_pdf_filename())


class TestGetFileSize(IntegrationTestCase):
    """Test we agree about filesize with bumblebee."""

    features = (
        'bumblebee',
        )

    def test_returns_file_size_in_kb_if_file_is_available(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        self.assertEqual(self.document.get_file().getSize() / 1024, adapter.get_file_size())

    def test_returns_none_if_no_file_is_available(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.empty_document, self.request), IBumblebeeOverlay)
        self.assertIsNone(adapter.get_file_size())


class TestGetCreator(IntegrationTestCase):
    """Test we correctly link to the document author."""

    features = (
        'bumblebee',
        )

    def test_returns_link_to_creator(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        creator_link = adapter.get_creator_link()
        self.assertIn('Ziegler Robert (robert.ziegler)', creator_link)
        self.assertIn('http://nohost/plone/@@user-details/robert.ziegler', creator_link)


class TestGetDocumentDate(IntegrationTestCase):
    """Test we correctly fetch the document date."""

    features = (
        'bumblebee',
        )

    def test_returns_localized_document_date(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        self.assertEqual(u'Jan 03, 2010', adapter.get_document_date())

    def test_returns_none_if_no_document_date_is_set(self):
        self.login(self.regular_user)
        self.document.document_date = ''
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        self.assertIsNone(adapter.get_document_date())


class TestGetContainingDossier(IntegrationTestCase):
    """Test we correctly fetch the immediate parent dossier."""

    features = (
        'bumblebee',
        )

    def test_returns_the_containing_dossier(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        self.assertEqual(self.dossier, adapter.get_containing_dossier())


class TestGetSequenceNumber(IntegrationTestCase):
    """Test we correctly fetch the document sequence number."""

    features = (
        'bumblebee',
        )

    def test_returns_sequence_number(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        self.assertEqual(getUtility(ISequenceNumber).get_number(self.document), adapter.get_sequence_number())


class TestGetReferenceNumber(IntegrationTestCase):
    """Test we correctly fetch the document reference number."""

    features = (
        'bumblebee',
        )

    def test_returns_reference_number(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        self.assertEqual(IReferenceNumber(self.document).get_number(), adapter.get_reference_number())


class TestGetCheckoutLink(IntegrationTestCase):
    """Test we correctly generate the document checkout link."""

    features = (
        'bumblebee',
        )

    def test_returns_checkout_and_edit_url(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        expected_url = '{}/editing_document?_authenticator='.format(self.document.absolute_url())
        self.assertTrue(adapter.get_checkout_url().startswith(expected_url))

    def test_returns_none_if_no_document_is_available_to_checkout(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.empty_document, self.request), IBumblebeeOverlay)
        self.assertIsNone(adapter.get_checkout_url())

    def test_returns_none_if_user_is_not_allowed_to_edit(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.proposaldocument, self.request), IBumblebeeOverlay)
        self.assertIsNone(adapter.get_checkout_url())


class TestGetDownloadCopyLink(IntegrationTestCase):
    """Test we correctly generate the document download link."""

    features = (
        'bumblebee',
        )

    @browsing
    def test_returns_download_copy_link_as_html_link(self, browser):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        browser.open_html(adapter.get_download_copy_link())
        self.assertEqual('Download copy', browser.css('a').first.text)

    def test_returns_none_if_no_document_is_available(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.empty_document, self.request), IBumblebeeOverlay)
        self.assertIsNone(adapter.get_download_copy_link())


class TestGetEditMetadataLink(IntegrationTestCase):
    """Test we correctly generate the document edit metadata link."""

    features = (
        'bumblebee',
        )

    def test_returns_edit_metadata_url(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        self.assertEqual('{}/edit'.format(self.document.absolute_url()), adapter.get_edit_metadata_url())

    def test_returns_none_if_user_is_not_allowed_to_edit(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.proposaldocument, self.request), IBumblebeeOverlay)
        self.assertIsNone(adapter.get_edit_metadata_url())


class TestHasFile(IntegrationTestCase):
    """Test we correctly detect if a document has a file."""

    features = (
        'bumblebee',
        )

    def test_returns_true_if_document_has_a_file(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        self.assertTrue(adapter.has_file())

    def test_returns_false_if_document_has_no_file(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.empty_document, self.request), IBumblebeeOverlay)
        self.assertFalse(adapter.has_file())


class TestGetFile(IntegrationTestCase):
    """Test we correctly fetch the file of the document."""

    features = (
        'bumblebee',
        )

    def test_returns_none_if_document_has_no_file(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.empty_document, self.request), IBumblebeeOverlay)
        self.assertIsNone(adapter.get_file())

    def test_returns_file_if_document_has_file(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        self.assertEqual(self.document.file, adapter.get_file())


class TestGetCheckinWithoutCommentUrl(IntegrationTestCase):
    """Test we correctly generate a checkin without comment link."""

    features = (
        'bumblebee',
        )

    def test_returns_none_when_document_is_not_checked_out(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        self.assertIsNone(adapter.get_checkin_without_comment_url())

    def test_returns_checkin_without_comment_url_as_string(self):
        self.login(self.regular_user)
        self.checkout_document(self.document)
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        expected_url = '{}/@@checkin_without_comment?_authenticator='.format(self.document.absolute_url())
        self.assertTrue(adapter.get_checkin_without_comment_url().startswith(expected_url))


class TestGetCheckinWithCommentUrl(IntegrationTestCase):
    """Test we correctly generate a checkin with comment link."""

    features = (
        'bumblebee',
        )

    def test_returns_none_when_document_is_not_checked_out(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        self.assertIsNone(adapter.get_checkin_with_comment_url())

    def test_returns_checkin_with_comment_url_as_string(self):
        self.login(self.regular_user)
        self.checkout_document(self.document)
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        expected_url = '{}/@@checkin_document?_authenticator='.format(self.document.absolute_url())
        self.assertTrue(adapter.get_checkin_with_comment_url().startswith(expected_url))


class TestRenderLockInfoViewlet(IntegrationTestCase):
    """Test we correctly render the document locking status."""

    features = (
        'bumblebee',
        )

    @browsing
    def test_returns_empty_html_if_not_locked(self, browser):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        browser.open_html(adapter.render_lock_info_viewlet())
        self.assertEqual(0, len(browser.css('.portalMessage')))

    @browsing
    def test_returns_lock_info_viewlet_if_locked(self, browser):
        self.login(self.regular_user)
        IRefreshableLockable(self.document).lock()
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        browser.open_html(adapter.render_lock_info_viewlet())
        self.assertEqual(1, len(browser.css('.portalMessage')))


class TestRenderCheckedOutViewlet(IntegrationTestCase):
    """Test we correctly render the document checkout info viewlet."""

    features = (
        'bumblebee',
        )

    @browsing
    def test_returns_empty_html_if_not_checked_out(self, browser):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        self.assertEqual(u'\n', adapter.render_checked_out_viewlet())

    @browsing
    def test_returns_lock_info_viewlet_if_checked_out(self, browser):
        self.login(self.regular_user)
        self.checkout_document(self.document)
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        browser.open_html(adapter.render_checked_out_viewlet())
        self.assertEqual(1, len(browser.css('.portalMessage')))


class TestIsVersionedContext(IntegrationTestCase):
    """Test if we correctly detect if we're on a versioned document or not."""

    features = (
        'bumblebee',
        )

    def test_returns_false_if_no_version_id_is_given(self):
        self.login(self.regular_user)
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        self.assertFalse(adapter.is_versioned())

    def test_returns_true_if_version_id_is_a_string(self):
        self.login(self.regular_user)
        self.request['version_id'] = '0'
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        self.assertTrue(adapter.is_versioned())

    def test_returns_true_if_version_id_is_a_number(self):
        self.login(self.regular_user)
        self.request['version_id'] = 123
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        self.assertTrue(adapter.is_versioned())


class TestGetRevertUrl(IntegrationTestCase):
    """Test we generate proper document version revert links."""

    features = (
        'bumblebee',
        )

    def test_returns_revert_url_as_string(self):
        self.login(self.regular_user)
        alsoProvides(self.request, IVersionedContextMarker)
        # We need to do both in order to fake a real request here
        self.request['version_id'] = 3
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        adapter.version_id = 3
        self.assertIn('revert-file-to-version?version_id=3', adapter.get_revert_link())

    def test_returns_none_if_context_is_not_a_versioned_context(self):
        self.login(self.regular_user)
        alsoProvides(self.request, IVersionedContextMarker)
        adapter = getMultiAdapter((self.document, self.request), IBumblebeeOverlay)
        self.assertIsNone(adapter.get_revert_link())
