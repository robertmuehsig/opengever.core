from ftw.testbrowser import browsing
from opengever.testing import IntegrationTestCase


class FileActionsTestBase(IntegrationTestCase):

    features = ('bumblebee',)
    maxDiff = None

    def get_file_actions(self, browser, context):
        browser.open(context.absolute_url() + '/@actions',
                     method='GET', headers=self.api_headers)
        return browser.json['file_actions']


class TestFileActionsGetForMails(FileActionsTestBase):

    @browsing
    def test_available_file_actions(self, browser):
        self.login(self.regular_user, browser)
        expected_file_actions = [
            {u'id': u'download_copy',
             u'title': u'Download copy',
             u'icon': u''},
            {u'id': u'attach_to_email',
             u'title': u'Attach to email',
             u'icon': u''},
            {u'id': u'open_as_pdf',
             u'title': u'Open as PDF',
             u'icon': u''},
            ]

        self.assertEqual(expected_file_actions,
                         self.get_file_actions(browser, self.mail_eml))


class TestFileActionsGetForDocuments(FileActionsTestBase):

    @browsing
    def test_available_file_actions(self, browser):
        self.login(self.regular_user, browser)
        expected_file_actions = [
            {u'id': u'oc_direct_checkout',
             u'title': u'Checkout and edit',
             u'icon': u''},
            {u'id': u'download_copy',
             u'title': u'Download copy',
             u'icon': u''},
            {u'id': u'attach_to_email',
             u'title': u'Attach to email',
             u'icon': u''},
            {u'id': u'open_as_pdf',
             u'title': u'Open as PDF',
             u'icon': u''},
            ]
        self.assertEqual(expected_file_actions,
                         self.get_file_actions(browser, self.document))

    @browsing
    def test_oc_zem_checkout_available_if_oc_checkout_deactivated(self, browser):
        self.deactivate_feature('officeconnector-checkout')
        self.login(self.regular_user, browser)
        expected_file_actions = [
            {u'id': u'oc_zem_checkout',
             u'title': u'Checkout and edit',
             u'icon': u''},
            {u'id': u'download_copy',
             u'title': u'Download copy',
             u'icon': u''},
            {u'id': u'attach_to_email',
             u'title': u'Attach to email',
             u'icon': u''},
            {u'id': u'open_as_pdf',
             u'title': u'Open as PDF',
             u'icon': u''},
            ]
        self.assertEqual(expected_file_actions,
                         self.get_file_actions(browser, self.document))

    @browsing
    def test_oc_unsupported_file_checkout_available_if_file_not_oc_editable(self, browser):
        self.login(self.regular_user, browser)
        self.document.file.contentType = u'foo/bar'
        expected_file_actions = [
            {u'id': u'oc_unsupported_file_checkout',
             u'title': u'Checkout',
             u'icon': u''},
            {u'id': u'download_copy',
             u'title': u'Download copy',
             u'icon': u''},
            {u'id': u'attach_to_email',
             u'title': u'Attach to email',
             u'icon': u''},
            ]
        self.assertEqual(expected_file_actions,
                         self.get_file_actions(browser, self.document))

    @browsing
    def test_checkin_available_if_checked_out_by_current_user(self, browser):
        self.login(self.regular_user, browser)
        self.checkout_document(self.document)

        expected_file_actions = [
            {u'id': u'oc_direct_edit',
             u'title': u'Edit',
             u'icon': u''},
            {u'id': u'checkin_without_comment',
             u'title': u'Checkin without comment',
             u'icon': u''},
            {u'id': u'checkin_with_comment',
             u'title': u'Checkin with comment',
             u'icon': u''},
            {u'id': u'cancel_checkout',
             u'title': u'Cancel checkout',
             u'icon': u''},
            {u'id': u'download_copy',
             u'title': u'Download copy',
             u'icon': u''},
            {u'id': u'attach_to_email',
             u'title': u'Attach to email',
             u'icon': u''},
            {u'id': u'open_as_pdf',
             u'title': u'Open as PDF',
             u'icon': u''},
            ]

        self.assertEqual(expected_file_actions,
                         self.get_file_actions(browser, self.document))

    @browsing
    def test_checkin_available_if_checked_out_by_current_user_oc_checkout_deactivated(self, browser):
        self.login(self.regular_user, browser)
        self.checkout_document(self.document)

        expected_file_actions = [
            {u'id': u'oc_direct_edit',
             u'title': u'Edit',
             u'icon': u''},
            {u'id': u'checkin_without_comment',
             u'title': u'Checkin without comment',
             u'icon': u''},
            {u'id': u'checkin_with_comment',
             u'title': u'Checkin with comment',
             u'icon': u''},
            {u'id': u'cancel_checkout',
             u'title': u'Cancel checkout',
             u'icon': u''},
            {u'id': u'download_copy',
             u'title': u'Download copy',
             u'icon': u''},
            {u'id': u'attach_to_email',
             u'title': u'Attach to email',
             u'icon': u''},
            {u'id': u'open_as_pdf',
             u'title': u'Open as PDF',
             u'icon': u''},
            ]

        self.assertEqual(expected_file_actions,
                         self.get_file_actions(browser, self.document))

    @browsing
    def test_checkin_only_available_for_managers_if_checked_out_by_other_user(self, browser):
        self.login(self.regular_user, browser)
        self.checkout_document(self.document)

        self.login(self.manager, browser)
        expected_manager_file_actions = [
            {u'id': u'checkin_without_comment',
             u'title': u'Checkin without comment',
             u'icon': u''},
            {u'id': u'checkin_with_comment',
             u'title': u'Checkin with comment',
             u'icon': u''},
            {u'id': u'cancel_checkout',
             u'title': u'Cancel checkout',
             u'icon': u''},
            {u'id': u'open_as_pdf',
             u'title': u'Open as PDF',
             u'icon': u''},
            ]
        self.assertEqual(expected_manager_file_actions,
                         self.get_file_actions(browser, self.document))

        self.login(self.dossier_manager, browser)
        expected_dossier_manager_file_actions = [
            {u'id': u'open_as_pdf',
             u'title': u'Open as PDF',
             u'icon': u''},
            ]
        self.assertEqual(expected_dossier_manager_file_actions,
                         self.get_file_actions(browser, self.document))

    @browsing
    def test_attach_not_available_if_feature_disabled(self, browser):
        self.deactivate_feature('officeconnector-attach')
        self.login(self.regular_user, browser)
        expected_file_actions = [
            {u'id': u'oc_direct_checkout',
             u'title': u'Checkout and edit',
             u'icon': u''},
            {u'id': u'download_copy',
             u'title': u'Download copy',
             u'icon': u''},
            {u'id': u'open_as_pdf',
             u'title': u'Open as PDF',
             u'icon': u''},
            ]
        self.assertEqual(expected_file_actions,
                         self.get_file_actions(browser, self.document))

    @browsing
    def test_oneoffixx_retry_available_for_shadow_documents(self, browser):
        self.activate_feature('oneoffixx')
        self.login(self.manager, browser)
        expected_file_actions = [
            {u'id': u'oneoffixx_retry',
             u'title': u'Oneoffixx retry',
             u'icon': u''},
            ]
        self.assertEqual(expected_file_actions,
                         self.get_file_actions(browser, self.shadow_document))

    @browsing
    def test_open_as_pdf_not_available_if_bumblebee_disabled(self, browser):
        self.deactivate_feature('bumblebee')
        self.login(self.regular_user, browser)
        expected_file_actions = [
            {u'id': u'oc_direct_checkout',
             u'title': u'Checkout and edit',
             u'icon': u''},
            {u'id': u'download_copy',
             u'title': u'Download copy',
             u'icon': u''},
            {u'id': u'attach_to_email',
             u'title': u'Attach to email',
             u'icon': u''},
            ]
        self.assertEqual(expected_file_actions,
                         self.get_file_actions(browser, self.document))
