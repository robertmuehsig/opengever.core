from opengever.base.model import Base
from opengever.base.model import create_session
from opengever.base.oguid import Oguid
from opengever.globalindex.model import WORKFLOW_STATE_LENGTH
from opengever.meeting import _
from opengever.meeting.model import AgendaItem
from opengever.meeting.model import proposalhistory
from opengever.meeting.model.query import ProposalQuery
from opengever.meeting.workflow import State
from opengever.meeting.workflow import Transition
from opengever.meeting.workflow import Workflow
from opengever.ogds.base.utils import ogds_service
from opengever.ogds.models import UNIT_ID_LENGTH
from plone import api
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import backref
from sqlalchemy.orm import composite
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Sequence


class Submit(Transition):

    def execute(self, obj, model):
        super(Submit, self).execute(obj, model)
        assert obj, 'submitting requires a plone context object.'
        obj.submit()


class Proposal(Base):
    """Sql representation of a proposal."""

    query_cls = ProposalQuery

    __tablename__ = 'proposals'
    __table_args__ = (
        UniqueConstraint('admin_unit_id', 'int_id'),
        UniqueConstraint('submitted_admin_unit_id', 'submitted_int_id'),
        {})

    proposal_id = Column("id", Integer, Sequence("proposal_id_seq"),
                         primary_key=True)
    admin_unit_id = Column(String(UNIT_ID_LENGTH), nullable=False)
    int_id = Column(Integer, nullable=False)
    oguid = composite(Oguid, admin_unit_id, int_id)
    physical_path = Column(String(256), nullable=False)

    submitted_admin_unit_id = Column(String(UNIT_ID_LENGTH))
    submitted_int_id = Column(Integer)
    submitted_oguid = composite(
        Oguid, submitted_admin_unit_id, submitted_int_id)
    submitted_physical_path = Column(String(256))

    excerpt_document_id = Column(Integer, ForeignKey('generateddocuments.id'))
    excerpt_document = relationship(
        'GeneratedExcerpt', uselist=False,
        backref=backref('proposal', uselist=False),
        primaryjoin="GeneratedExcerpt.document_id==Proposal.excerpt_document_id")

    submitted_excerpt_document_id = Column(Integer,
                                           ForeignKey('generateddocuments.id'))
    submitted_excerpt_document = relationship(
        'GeneratedExcerpt', uselist=False,
        backref=backref('submitted_proposal', uselist=False),
        primaryjoin="GeneratedExcerpt.document_id==Proposal.submitted_excerpt_document_id")

    title = Column(String(256), nullable=False)
    workflow_state = Column(String(WORKFLOW_STATE_LENGTH), nullable=False)
    legal_basis = Column(Text)
    initial_position = Column(Text)
    proposed_action = Column(Text)

    considerations = Column(Text)

    committee_id = Column(Integer, ForeignKey('committees.id'))
    committee = relationship('Committee', backref='proposals')

    history_records = relationship('ProposalHistory',
                                   order_by="desc(ProposalHistory.created)")

    # workflow definition
    STATE_PENDING = State('pending', is_default=True,
                          title=_('pending', default='Pending'))
    STATE_SUBMITTED = State('submitted',
                            title=_('submitted', default='Submitted'))
    STATE_SCHEDULED = State('scheduled',
                            title=_('scheduled', default='Scheduled'))
    STATE_DECIDED = State('decided', title=_('decided', default='Decided'))

    workflow = Workflow([
        STATE_PENDING,
        STATE_SUBMITTED,
        STATE_SCHEDULED,
        STATE_DECIDED
        ], [
        Submit('pending', 'submitted',
               title=_('submit', default='Submit')),
        Transition('submitted', 'scheduled',
                   title=_('schedule', default='Schedule')),
        Transition('scheduled', 'submitted',
                   title=_('un-schedule', default='Remove from schedule')),
        Transition('scheduled', 'decided',
                   title=_('decide', default='Decide')),
        ])

    def __repr__(self):
        return "<Proposal {}@{}>".format(self.int_id, self.admin_unit_id)

    def get_state(self):
        return self.workflow.get_state(self.workflow_state)

    def execute_transition(self, name):
        self.workflow.execute_transition(None, self, name)

    def get_admin_unit(self):
        return ogds_service().fetch_admin_unit(self.admin_unit_id)

    def get_submitted_admin_unit(self):
        return ogds_service().fetch_admin_unit(self.submitted_admin_unit_id)

    @property
    def id(self):
        return self.proposal_id

    @property
    def css_class(self):
        return 'contenttype-opengever-meeting-proposal'

    def get_searchable_text(self):
        searchable = filter(None, [self.title, self.initial_position])
        return ' '.join([term.encode('utf-8') for term in searchable])

    def get_decision(self):
        if self.agenda_item:
            return self.agenda_item.decision
        return None

    def get_url(self):
        return self._get_url(self.get_admin_unit(), self.physical_path)

    def get_submitted_url(self):
        return self._get_url(self.get_submitted_admin_unit(),
                             self.submitted_physical_path)

    def _get_url(self, admin_unit, physical_path):
        if not (admin_unit and physical_path):
            return ''
        return '/'.join((admin_unit.public_url, physical_path))

    def get_link(self, include_icon=True):
        return self._get_link(self.get_url(), include_icon=include_icon)

    def get_submitted_link(self, include_icon=True):
        return self._get_link(self.get_submitted_url(),
                              include_icon=include_icon)

    def _get_link(self, url, include_icon=True):
        if include_icon:
            link = u'<a href="{0}" title="{1}" class="{2}">{1}</a>'.format(
                url, self.title, self.css_class)
        else:
            link = u'<a href="{0}" title="{1}">{1}</a>'.format(url, self.title)

        transformer = api.portal.get_tool('portal_transforms')
        return transformer.convertTo('text/x-html-safe', link).getData()

    def getPath(self):
        """This method is required by a tabbedview."""

        return self.physical_path

    def resolve_sumitted_proposal(self):
        return self.submitted_oguid.resolve_object()

    def resolve_submitted_documents(self):
        return [doc.resolve_submitted() for doc in self.submitted_documents]

    def has_submitted_documents(self):
        return self.submitted_documents or self.submitted_excerpt_document

    def resolve_excerpt_document(self):
        document = self.excerpt_document
        if document:
            return document.oguid.resolve_object()

    def has_submitted_excerpt_document(self):
        return self.submitted_excerpt_document is not None

    def resolve_submitted_excerpt_document(self):
        document = self.submitted_excerpt_document
        if document:
            return document.oguid.resolve_object()

    def can_be_scheduled(self):
        return self.get_state() == self.STATE_SUBMITTED

    def is_submit_additional_documents_allowed(self):
        return self.get_state() in [self.STATE_SUBMITTED, self.STATE_SCHEDULED]

    def is_editable_in_dossier(self):
        return self.get_state() == self.STATE_PENDING

    def is_editable_in_committee(self):
        return self.get_state() in [self.STATE_SUBMITTED, self.STATE_SCHEDULED]

    def schedule(self, meeting):
        assert self.can_be_scheduled()

        self.execute_transition('submitted-scheduled')
        session = create_session()
        meeting.agenda_items.append(AgendaItem(proposal=self))
        session.add(proposalhistory.Scheduled(proposal=self, meeting=meeting))

    def remove_scheduled(self, meeting):
        self.execute_transition('scheduled-submitted')
        session = create_session()
        session.add(
            proposalhistory.RemoveScheduled(proposal=self, meeting=meeting))

    def resolve_proposal(self):
        return self.oguid.resolve_object()
