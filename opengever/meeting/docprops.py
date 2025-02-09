from opengever.dossier.interfaces import IDocPropertyProvider
from opengever.meeting.proposal import IBaseProposal
from zope.component import adapter
from zope.i18n import translate
from zope.interface import implementer


@implementer(IDocPropertyProvider)
@adapter(IBaseProposal)
class ProposalDocPropertyProvider(object):

    def __init__(self, context):
        self.context = context

    def get_meeting_properties(self):
        proposal = self.context

        properties = {
            'decision_number': '',
            'agenda_item_number': '',
            'agenda_item_number_raw': '',
            'proposal_title': proposal.Title(),
            'proposal_description': proposal.Description(),
            'proposal_state': translate(proposal.get_state().title,
                                        context=self.context.REQUEST),
        }

        model = proposal.load_model()
        if not model:
            return properties

        agenda_item = model.agenda_item
        if not agenda_item:
            return properties

        properties['decision_number'] = agenda_item.get_decision_number()
        properties['agenda_item_number'] = agenda_item.formatted_number
        properties['agenda_item_number_raw'] = agenda_item.item_number
        return properties

    def get_properties(self):
        return {'ogg.meeting.' + key: value or ''
                for key, value
                in self.get_meeting_properties().items()}
