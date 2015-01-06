from five import grok
from opengever.meeting.form import MeetingModelAddForm
from opengever.meeting.form import MeetingModelEditForm
from opengever.meeting.proposal import IProposal
from opengever.meeting.proposal import ISubmittedProposal
from opengever.meeting.proposal import Proposal
from opengever.meeting.proposal import SubmittedProposal
from plone.directives import dexterity
from z3c.form import field


class ProposalEditForm(MeetingModelEditForm, dexterity.EditForm):

    grok.context(IProposal)
    fields = field.Fields(Proposal.model_schema, ignoreContext=True)
    content_type = Proposal


class SubmittedProposalEditForm(MeetingModelEditForm, dexterity.EditForm):

    grok.context(ISubmittedProposal)
    fields = field.Fields(SubmittedProposal.model_schema, ignoreContext=True)
    content_type = Proposal


class AddForm(MeetingModelAddForm, dexterity.AddForm):

    grok.name('opengever.meeting.proposal')
    content_type = Proposal
    fields = field.Fields(Proposal.model_schema)
