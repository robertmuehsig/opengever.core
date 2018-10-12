from BTrees.OOBTree import OOBTree
from datetime import timedelta
from ftw.bumblebee import get_service_v3
from ftw.bumblebee.config import PROCESSING_QUEUE
from ftw.bumblebee.interfaces import IBumblebeeDocument
from ftw.zipexport.generation import ZipGenerator
from ftw.zipexport.utils import normalize_path
from opengever.base.date_time import utcnow_tz_aware
from opengever.base.security import elevated_privileges
from opengever.meeting import _
from opengever.meeting.traverser import MeetingTraverser
from plone import api
from plone.namedfile.file import NamedBlobFile
from plone.uuid.interfaces import IUUID
from Products.CMFPlone.utils import safe_unicode
from StringIO import StringIO
from tzlocal import get_localzone
from zope.annotation import IAnnotations
from zope.globalrequest import getRequest
from zope.i18n import translate
import json
import os
import uuid


ZIP_JOBS_KEY = 'opengever.meeting.zipexporter'
ZIP_EXPIRATION_DAYS = 2


def format_modified(modified):
    return safe_unicode(
        get_localzone().localize(
            modified.asdatetime().replace(tzinfo=None)
        ).isoformat())


class MeetingDocumentZipper(MeetingTraverser):

    def __init__(self, meeting, generator):
        super(MeetingDocumentZipper, self).__init__(meeting)
        self.generator = generator
        self.json_serializer = MeetingJSONSerializer(self.meeting, self)

    def get_zip_file(self):
        self.traverse()
        self.generator.add_file('meeting.json', self.get_meeting_json_file())
        return self.generator.generate()

    def get_filename(self, document):
        return document.get_filename()

    def get_file(self, document):
        return document.get_file()

    def get_agenda_item_filename(self, document, agenda_item_number):
        return normalize_path(u'{}/{}'.format(
            translate(
                _(u'title_agenda_item', default=u'Agenda item ${agenda_item_number}',
                  mapping={u'number': agenda_item_number}),
                context=getRequest(),
                ),
            safe_unicode(self.get_filename(document)))
        )

    def traverse_protocol_document(self, document):
        self.generator.add_file(
            self.get_filename(document), self.get_file(document).open()
        )

    def traverse_agenda_item_list_document(self, document):
        self.generator.add_file(
            self.get_filename(document), self.get_file(document).open()
        )

    def traverse_agenda_item_document(self, document, agenda_item):
        self.generator.add_file(
            self.get_agenda_item_filename(document, agenda_item.number),
            self.get_file(document).open()
        )

    def traverse_agenda_item_attachment(self, document, agenda_item):
        self.generator.add_file(
            self.get_agenda_item_filename(document, agenda_item.number),
            self.get_file(document).open()
        )

    def get_meeting_json_file(self):
        return StringIO(self.json_serializer.get_json())


class MeetingPDFDocumentZipper(MeetingDocumentZipper):
    """Zip a meetings documents, but replace documents with a PDF if available.

    if no PDF is available the original document will be used as a replacement.
    """
    def __init__(self, meeting, pdfs, generator):
        super(MeetingPDFDocumentZipper, self).__init__(meeting, generator)
        self.pdfs = pdfs

    def get_filename(self, document):
        document_id = IUUID(document)
        filename = super(MeetingPDFDocumentZipper, self).get_filename(document)
        if document_id not in self.pdfs:
            return filename

        return u'{}.pdf'.format(os.path.splitext(filename)[0])

    def get_file(self, document):
        document_id = IUUID(document)
        if document_id not in self.pdfs:
            return super(MeetingPDFDocumentZipper, self).get_file(document)

        return self.pdfs[document_id]


class MeetingJSONSerializer(MeetingTraverser):
    """Represents a JSON file with which grimlock can import the meeting."""

    def __init__(self, meeting, zipper):
        super(MeetingJSONSerializer, self).__init__(meeting)
        self.zipper = zipper
        self.data = {
            'opengever_id': meeting.meeting_id,
            'title': safe_unicode(meeting.title),
            'start': safe_unicode(meeting.start.isoformat()),
            'end': safe_unicode(meeting.end.isoformat() if meeting.end else ''),
            'location': safe_unicode(meeting.location),
            'committee': {
                'oguid': safe_unicode(meeting.committee.oguid.id),
                'title': safe_unicode(meeting.committee.title),
            },
            'agenda_items': [],
        }

    def get_json(self):
        self.traverse()

        json_data = {
            'version': '1.0.0',
            'meetings': [self.data],
        }
        return json.dumps(json_data, sort_keys=True, indent=4)

    def traverse_protocol_document(self, document):
        self.data['protocol'] = {
            'checksum': IBumblebeeDocument(document).get_checksum(),
            'file': self.zipper.get_filename(document),
            'modified': format_modified(document.modified()),
        }

    def traverse_agenda_item(self, agenda_item):
        self.current_agenda_item_data = {
            'opengever_id': agenda_item.agenda_item_id,
            'title': safe_unicode(agenda_item.get_title()),
            'sort_order': agenda_item.sort_order,
        }

        super(MeetingJSONSerializer, self).traverse_agenda_item(agenda_item)

        self.data['agenda_items'].append(self.current_agenda_item_data)
        self.current_agenda_item_data = None

    def traverse_agenda_item_document(self, document, agenda_item):
        self.current_agenda_item_data['number'] = agenda_item.number
        self.current_agenda_item_data['proposal'] = {
            'checksum': IBumblebeeDocument(document).get_checksum(),
            'file': self.zipper.get_agenda_item_filename(document, agenda_item.number),
            'modified': format_modified(document.modified()),
        }

    def traverse_agenda_item_attachment(self, document, agenda_item):
        attachment_data = self.current_agenda_item_data.setdefault(
            'attachments', [])

        attachment_data.append({
            'checksum': IBumblebeeDocument(document).get_checksum(),
            'file': self.zipper.get_agenda_item_filename(document, agenda_item.number),
            'modified': format_modified(document.modified()),
            'title': safe_unicode(document.Title()),
        })


class ZipExportDocumentCollector(MeetingTraverser):
    """Collect all documents that will be exported in a zip."""

    def __init__(self, meeting):
        super(ZipExportDocumentCollector, self).__init__(meeting)
        self._documents = []

    def traverse_protocol_document(self, document):
        self._collect(document)

    def traverse_agenda_item_list_document(self, document):
        self._collect(document)

    def traverse_agenda_item_document(self, document, agenda_item):
        self._collect(document)

    def traverse_agenda_item_attachment(self, document, agenda_item):
        self._collect(document)

    def get_documents(self):
        self.traverse()
        return tuple(self._documents)

    def _collect(self, document):
        if not IBumblebeeDocument(document).has_file_data():
            return

        self._documents.append(document)


class MeetingZipExporter(object):
    """Exports a meeting's documents as PDF in a zip file.

    Requests pdfs from bumblebee, if available. Falls back to original file
    if no pdf can be supplied or pdf conversion was skipped/erroneous.
    """
    @classmethod
    def exists(cls, meeting, job_id):
        committee = meeting.committee.oguid.resolve_object()
        zip_jobs = IAnnotations(committee).get(ZIP_JOBS_KEY, {})
        return job_id in zip_jobs

    def __init__(self, meeting, doc_in_job_id=None, job_id=None):
        self.meeting = meeting
        self.committee = meeting.committee.oguid.resolve_object()

        # prepare annotations of committee
        annotations = IAnnotations(self.committee)
        if ZIP_JOBS_KEY not in annotations:
            annotations[ZIP_JOBS_KEY] = OOBTree()
        self.zip_jobs = annotations[ZIP_JOBS_KEY]

        # Get or create job_id
        if doc_in_job_id:
            self.job_id = self._doc_in_job_id_to_job_id(doc_in_job_id)
            self.zip_job = self.zip_jobs[self.job_id]
        elif job_id:
            self.zip_job = self.zip_jobs[job_id]
            self.job_id = job_id
        else:
            self.job_id = str(uuid.uuid4())
            self.zip_job = None

    def demand_pdfs(self):
        """Demand pdfs for all zip documents from bumlebee."""

        self._cleanup_old_jobs()
        self._prepare_zip_job_metadata()

        for document in self._collect_meeting_documents():
            status = self._queue_demand_job(document)
            self._append_document_job_metadata(
                self.zip_job, document, status)

        return self.job_id

    def get_document(self, doc_in_job_id):
        document_id = self._doc_in_job_id_to_document_id(doc_in_job_id)
        assert document_id in self.zip_job['documents']
        catalog = api.portal.get_tool('portal_catalog')
        brain = catalog.unrestrictedSearchResults(UID=document_id)[0]
        document = brain._unrestrictedGetObject()
        return document

    def receive_pdf(self, doc_in_job_id, mimetype, data):
        document_id = self._doc_in_job_id_to_document_id(doc_in_job_id)
        self._update_job_with_pdf(document_id, mimetype, data)

        if self.is_finished_converting():
            self._generate_zipfile()

    def _update_job_with_pdf(self, document_id, mimetype, data):
        document_job = self.zip_job['documents'][document_id]
        # we're using NamedBlobFile here to re-use an IStorage adapter, the
        # filename is not relevant
        blob_file = NamedBlobFile(data=data, contentType=mimetype)

        document_job['status'] = 'finished'
        document_job['blob'] = blob_file

    def _generate_zipfile(self):
        pdfs = {}
        for document_id, document_job in self.zip_job['documents'].items():
            if document_job['status'] == 'finished':
                pdfs[document_id] = document_job.pop('blob')
                document_job['status'] = 'zipped'

        with ZipGenerator() as generator, elevated_privileges():
            zipper = MeetingPDFDocumentZipper(
                self.meeting, pdfs, generator)

            zip_blob_file = NamedBlobFile(data=zipper.get_zip_file(),
                                          contentType='application/zip')
            self.zip_job['zip_file'] = zip_blob_file

    def get_zipfile(self):
        return self.zip_job['zip_file']

    def mark_as_skipped(self, doc_in_job_id):
        document_id = self._doc_in_job_id_to_document_id(doc_in_job_id)
        document_job = self.zip_job['documents'][document_id]
        document_job['status'] = 'skipped'

    def is_finished_converting(self):
        return self.get_status()['converting'] == 0

    def get_status(self):
        status = {
            'skipped': 0,
            'finished': 0,
            'converting': 0,
            'zipped': 0,
            'is_finished': self.is_finished(),
        }
        for document_info in self.zip_job['documents'].values():
            status[document_info['status']] += 1
        return status

    def is_finished(self):
        return 'zip_file' in self.zip_job

    def _cleanup_old_jobs(self):
        """Remove expired zip jobs.

        The zip jobs are only kept for a relatively short amount of time as
        they are a temporary thing.
        """
        to_remove = set()
        now = utcnow_tz_aware()
        expiration_delta = timedelta(days=ZIP_EXPIRATION_DAYS)

        for zip_job in self.zip_jobs.values():
            delta = now - zip_job['timestamp']
            if delta > expiration_delta:
                to_remove.add(zip_job['job_id'])

        for id_ in to_remove:
            del self.zip_jobs[id_]

    def _prepare_zip_job_metadata(self):
        zip_job = OOBTree()
        zip_job['job_id'] = self.job_id
        zip_job['timestamp'] = utcnow_tz_aware()
        zip_job['documents'] = OOBTree()
        self.zip_jobs[self.job_id] = zip_job

        self.zip_job = zip_job
        return zip_job

    def _append_document_job_metadata(self, zip_job, document, status):
        document_info = OOBTree()
        document_info['status'] = status

        document_id = IUUID(document)
        zip_job['documents'][document_id] = document_info

        return document_info

    def _queue_demand_job(self, document):
        callback_url = self.meeting.get_url(view='receive_meeting_zip_pdf')
        doc_in_job_id = self._get_doc_in_job_id(document)

        if get_service_v3().queue_demand(
                document, PROCESSING_QUEUE, callback_url,
                opaque_id=doc_in_job_id):
            return 'converting'
        else:
            return 'skipped'

    def _get_doc_in_job_id(self, document):
        return '{}:{}'.format(self.job_id, IUUID(document))

    def _doc_in_job_id_to_job_id(self, doc_in_job_id):
        return doc_in_job_id.split(':')[0]

    def _doc_in_job_id_to_document_id(self, doc_in_job_id):
        return doc_in_job_id.split(':')[1]

    def _collect_meeting_documents(self):
        return ZipExportDocumentCollector(self.meeting).get_documents()
