from ftw.testbrowser import browsing
from opengever.meeting.zipexport import MeetingZipExporter
from opengever.testing import IntegrationTestCase


class TestPollMeetingZip(IntegrationTestCase):

    features = ('meeting', 'bumblebee')

    @browsing
    def test_zip_polling_view_reports_converting(self, browser):
        self.login(self.meeting_user, browser)

        exporter = MeetingZipExporter(self.meeting.model)
        zip_job = exporter._prepare_zip_job_metadata()
        exporter._append_document_job_metadata(
            zip_job, self.document, 'converting')

        browser.open(
            self.meeting,
            view='poll_meeting_zip?job_id={}'.format(exporter.job_id))
        self.assertEqual(1, browser.json['converting'])

    @browsing
    def test_zip_polling_view_reports_finished(self, browser):
        self.login(self.meeting_user, browser)

        exporter = MeetingZipExporter(self.meeting.model)
        zip_job = exporter._prepare_zip_job_metadata()
        exporter._append_document_job_metadata(
            zip_job, self.document, 'finished')

        browser.open(
            self.meeting,
            view='poll_meeting_zip?job_id={}'.format(exporter.job_id))
        self.assertEqual(1, browser.json['finished'], browser.json)

    @browsing
    def test_zip_polling_view_reports_skipped(self, browser):
        self.login(self.meeting_user, browser)

        exporter = MeetingZipExporter(self.meeting.model)
        zip_job = exporter._prepare_zip_job_metadata()
        exporter._append_document_job_metadata(
            zip_job, self.document, 'skipped')

        browser.open(
            self.meeting,
            view='poll_meeting_zip?job_id={}'.format(exporter.job_id))
        self.assertEqual(1, browser.json['skipped'])


class TestDownloadMeetingZip(IntegrationTestCase):

    features = ('meeting', 'bumblebee')

    @browsing
    def test_download_meeting_zip(self, browser):
        self.login(self.meeting_user, browser)

        exporter = MeetingZipExporter(self.meeting.model)
        zip_job = exporter._prepare_zip_job_metadata()
        exporter._append_document_job_metadata(
            zip_job, self.document, 'converting')
        exporter.receive_pdf(exporter._get_doc_in_job_id(self.document),
                             'application/pdf',
                             'i am a apdf.')

        browser.open(
            self.meeting,
            view='download_meeting_zip?job_id={}'.format(exporter.job_id))
        self.assertEquals('application/zip', browser.contenttype)
