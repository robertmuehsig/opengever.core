from five import grok
from ftw.datepicker.widget import DatePickerFieldWidget
from opengever.base.browser.helper import get_css_class
from opengever.base.browser.wizard import BaseWizardStepForm
from opengever.base.browser.wizard.interfaces import IWizardDataStorage
from opengever.base.form import WizzardWrappedAddForm
from opengever.base.handlebars import prepare_handlebars_template
from opengever.base.model import create_session
from opengever.base.oguid import Oguid
from opengever.base.schema import UTCDatetime
from opengever.meeting import _
from opengever.meeting import is_word_meeting_implementation_enabled
from opengever.meeting.browser.meetings.agendaitem_list import GenerateAgendaItemList
from opengever.meeting.browser.meetings.agendaitem_list import UpdateAgendaItemList
from opengever.meeting.browser.meetings.transitions import MeetingTransitionController
from opengever.meeting.browser.protocol import GenerateProtocol
from opengever.meeting.browser.protocol import MergeDocxProtocol
from opengever.meeting.browser.protocol import UpdateProtocol
from opengever.meeting.committee import ICommittee
from opengever.meeting.model import Meeting
from opengever.meeting.proposal import ISubmittedProposal
from path import Path
from plone import api
from plone.app.contentlisting.interfaces import IContentListing
from plone.app.contentlisting.interfaces import IContentListingObject
from plone.dexterity.i18n import MessageFactory as pd_mf
from plone.supermodel import model
from plone.z3cform.layout import FormWrapper
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from z3c.form.button import buttonAndHandler
from z3c.form.field import Fields
from z3c.form.form import Form
from z3c.form.interfaces import HIDDEN_MODE
from zope import schema
from zope.component import getUtility
from zope.globalrequest import getRequest
from zope.i18n import translate
from zope.interface import provider
from zope.schema.interfaces import IContextAwareDefaultFactory
import json


@provider(IContextAwareDefaultFactory)
def default_title(context):
    return context.Title().decode('utf-8')


class IMeetingModel(model.Schema):
    """Meeting model schema interface."""

    title = schema.TextLine(
        title=_(u"label_title", default=u"Title"),
        defaultFactory=default_title,
        required=True)

    committee = schema.Choice(
        title=_('label_committee', default=u'Committee'),
        source='opengever.meeting.CommitteeVocabulary',
        required=True)

    location = schema.TextLine(
        title=_(u"label_location", default=u"Location"),
        max_length=256,
        required=False)

    start = UTCDatetime(
        title=_('label_start', default=u"Start"),
        required=True)

    end = UTCDatetime(
        title=_('label_end', default=u"End"),
        required=False)


ADD_MEETING_STEPS = (
    ('add-meeting', _(u'Add Meeting')),
    ('add-meeting-dossier', _(u'Add Dossier for Meeting'))
)

TEMPLATES_DIR = Path(__file__).joinpath('..', 'templates').abspath()


def get_dm_key(committee_oguid=None):
    """Return the key used to store meeting-data in the wizard-storage."""
    committee_oguid = committee_oguid or get_committee_oguid()
    return 'create_meeting:{}'.format(committee_oguid)


def get_committee_oguid():
    return Oguid.parse(getRequest().get('committee-oguid'))


class AddMeetingWizardStep(BaseWizardStepForm, Form):
    step_name = 'add-meeting'
    label = _('Add Meeting')
    steps = ADD_MEETING_STEPS

    fields = Fields(IMeetingModel)

    fields['start'].widgetFactory = DatePickerFieldWidget
    fields['end'].widgetFactory = DatePickerFieldWidget

    @buttonAndHandler(_(u'button_continue', default=u'Continue'), name='save')
    def handle_continue(self, action):
        data, errors = self.extractData()
        if errors:
            return

        committee_oguid = Oguid.for_object(self.context)

        dm = getUtility(IWizardDataStorage)
        dm.update(get_dm_key(committee_oguid), data)

        repository_folder = self.context.repository_folder.to_object
        return self.request.RESPONSE.redirect(
            '{}/add-meeting-dossier?committee-oguid={}'.format(
                repository_folder.absolute_url(), committee_oguid))

    @buttonAndHandler(_(u'button_cancel', default=u'Cancel'))
    def handle_cancel(self, action):
        return self.request.RESPONSE.redirect(self.context.absolute_url())

    def updateWidgets(self):
        super(AddMeetingWizardStep, self).updateWidgets()

        committee_id = self.context.load_model().committee_id
        self.widgets['committee'].mode = HIDDEN_MODE
        self.widgets['committee'].value = (str(committee_id), )

    def nextURL(self):
        return self._created_object.get_url()


class AddMeetingWizardStepView(FormWrapper, grok.View):
    grok.context(ICommittee)
    grok.name('add-meeting')
    grok.require('zope2.View')
    form = AddMeetingWizardStep

    def __init__(self, *args, **kwargs):
        FormWrapper.__init__(self, *args, **kwargs)
        grok.View.__init__(self, *args, **kwargs)


class AddMeetingDossierView(WizzardWrappedAddForm):

    typename = 'opengever.meeting.meetingdossier'

    def _create_form_class(self, parent_form_class, steptitle):
        class WrappedForm(BaseWizardStepForm, parent_form_class):
            step_name = 'add-meeting-dossier'
            step_title = steptitle
            steps = ADD_MEETING_STEPS
            label = _(u'Add Dossier for Meeting')

            passed_data = ['committee-oguid']

            @buttonAndHandler(pd_mf(u'Save'), name='save')
            def handleAdd(self, action):
                # create the dossier
                data, errors = self.extractData()
                if errors:
                    self.status = self.formErrorsMessage
                    return

                committee_oguid = get_committee_oguid()
                dossier = self.create_meeting_dossier(data)
                self.create_meeting(dossier, committee_oguid)

                api.portal.show_message(
                    _(u"The meeting and its dossier were created successfully"),
                    request=self.request,
                    type="info")

                committee = committee_oguid.resolve_object()
                return self.request.RESPONSE.redirect(
                    '{}#meetings'.format(committee.absolute_url()))

            @buttonAndHandler(pd_mf(u'Cancel'), name='cancel')
            def handleCancel(self, action):
                committee_oguid = get_committee_oguid()

                dm = getUtility(IWizardDataStorage)
                dm.drop_data(get_dm_key(committee_oguid))

                committee = committee_oguid.resolve_object()
                return self.request.RESPONSE.redirect(committee.absolute_url())

            def create_meeting_dossier(self, data):
                obj = self.createAndAdd(data)
                if obj is not None:
                    # mark only as finished if we get the new object
                    self._finishedAdd = True
                return obj

            def create_meeting(self, dossier, committee_oguid):
                dm = getUtility(IWizardDataStorage)
                data = dm.get_data(get_dm_key())
                data['dossier_oguid'] = Oguid.for_object(dossier)
                meeting = Meeting(**data)
                meeting.initialize_participants()
                session = create_session()
                session.add(meeting)
                session.flush()  # required to create an autoincremented id

                dm.drop_data(get_dm_key())
                return meeting

        return WrappedForm

    def __call__(self):
        title_key = 'form.widgets.IOpenGeverBase.title'

        if title_key not in self.request.form:
            dm = getUtility(IWizardDataStorage)
            data = dm.get_data(get_dm_key())

            start_date = api.portal.get_localized_time(datetime=data['start'])
            default_title = _(u'Meeting on ${date}',
                              mapping={'date': start_date})
            self.request.set(title_key, default_title)

        return super(AddMeetingDossierView, self).__call__()


class MeetingView(BrowserView):

    noword_template = ViewPageTemplateFile('templates/meeting-noword.pt')
    word_template = ViewPageTemplateFile('templates/meeting-word.pt')

    def __init__(self, context, request):
        super(MeetingView, self).__init__(context, request)
        self.model = self.context.model

    def __call__(self):
        if is_word_meeting_implementation_enabled():
            return self.word_template()
        else:
            return self.noword_template()

    def get_css_class(self, document):
        """Provide CSS classes for icons."""
        return get_css_class(document)

    def transition_url(self, transition):
        return MeetingTransitionController.url_for(
            self.context, self.model, transition.name)

    def unscheduled_proposals(self):
        return self.context.get_unscheduled_proposals()

    def get_protocol_document(self):
        if self.model.protocol_document:
            return IContentListingObject(
                self.model.protocol_document.resolve_document())

    def get_agendaitem_list_document(self):
        if self.model.agendaitem_list_document:
            return IContentListingObject(
                self.model.agendaitem_list_document.resolve_document())

    def url_protocol(self):
        return self.model.get_url(view='protocol')

    def url_generate_protocol(self):
        if is_word_meeting_implementation_enabled():
            return self.url_merge_docx_protocol()

        if not self.model.has_protocol_document():
            return GenerateProtocol.url_for(self.model)
        else:
            return UpdateProtocol.url_for(self.model)

    def url_merge_docx_protocol(self):
        return MergeDocxProtocol.url_for(self.model)

    def has_agendaitem_list_document(self):
        return self.model.has_agendaitem_list_document()

    def has_protocol_document(self):
        return self.model.has_protocol_document()

    def url_download_protocol(self):
        if self.has_protocol_document:
            return self.model.protocol_document.get_download_url()

    def will_closing_regenerate_protocol(self):
        """This method can tell whether we will regenerate the protocol when
        closing the meething.

        The protocol will be generated while it is locked or not yet existing.
        When the user reopens the meeting the document will be left unlocked
        because the user may have made changes at this point.
        The protocol is no longer regenerated automatically when it
        may have been changed.
        """
        if not self.has_protocol_document():
            return True
        return self.model.protocol_document.is_locked()

    def url_download_agendaitem_list(self):
        if self.has_agendaitem_list_document:
            return self.model.agendaitem_list_document.get_download_url()

    def url_generate_agendaitem_list(self):
        if not self.model.has_agendaitem_list_document():
            return GenerateAgendaItemList.url_for(self.model)
        else:
            return UpdateAgendaItemList.url_for(self.model)

    def url_agendaitem_list(self):
        return self.model.get_url(view='agenda_item_list')

    def url_zipexport(self):
        return self.model.get_url(view='export-meeting-zip')

    def url_manually_generate_excerpt(self):
        return self.model.get_url(view='generate_excerpt')

    def transitions(self):
        return self.model.get_state().get_transitions()

    def agenda_items(self):
        return self.model.agenda_items

    def manually_generated_excerpts(self):
        docs = [excerpt.resolve_document()
                for excerpt in self.model.excerpt_documents]

        return IContentListing(docs)

    def render_handlebars_agendaitems_template(self):
        if is_word_meeting_implementation_enabled():
            return self.render_handlebars_agendaitems_template_word()
        else:
            return self.render_handlebars_agendaitems_template_noword()

    def render_handlebars_agendaitems_template_noword(self):
        return prepare_handlebars_template(
            TEMPLATES_DIR.joinpath('agendaitems-noword.html'),
            translations=(
                _('label_edit_cancel', default='Cancel'),
                _('label_edit_save', default='Save'),
                _('label_edit_action', default='edit title'),
                _('label_delete_action', default='remove this agenda item'),
                _('label_decide_action', default='Decide this agenda item'),
                _('label_reopen_action', default='Reopen this agenda item'),
                _('label_revise_action', default='Revise this agenda item'),
            ),
            max_proposal_title_length=ISubmittedProposal['title'].max_length)

    def render_handlebars_agendaitems_template_word(self):
        return prepare_handlebars_template(
            TEMPLATES_DIR.joinpath('agendaitems-word.html'),
            translations=(
                _('label_edit_cancel', default='Cancel'),
                _('label_edit_save', default='Save'),
                _('label_edit_action', default='edit title'),
                _('label_edit_document_action',
                  default='Checkout and edit word document.'),
                _('label_generate_excerpt', default='Generate an excerpt.'),
                _('label_delete_action', default='remove this agenda item'),
                _('label_ad_hoc_delete_action', default='delete this agenda item'),
                _('label_decide_action', default='Decide this agenda item'),
                _('label_reopen_action', default='Reopen this agenda item'),
                _('label_revise_action', default='Revise this agenda item'),
                _('label_attachments', default='Attachments'),
                _('label_excerpts', default='Excerpts'),
                _('label_return_action', default='Return excerpt to proposer'),
                _('label_toggle_attachments', default='Toggle attachments'),
                _('label_agenda_item_number', default='Agenda item number'),
                _('label_decision_number', default=u'Decision number'),
                _('label_returned_excerpt',
                  default='This excerpt was returned to the dossier'),
            ),
            max_proposal_title_length=ISubmittedProposal['title'].max_length)

    def render_handlebars_proposals_template(self):
        return prepare_handlebars_template(
            TEMPLATES_DIR.joinpath('proposals.html'),
            translations=(
                _('label_schedule', default='Schedule'),
                _('label_no_proposals', default='No proposals submitted')))

    def json_is_editable(self):
        return json.dumps(self.model.is_editable())

    def json_is_agendalist_editable(self):
        return json.dumps(self.model.is_agendalist_editable())

    @property
    def url_update_agenda_item_order(self):
        return '{}/agenda_items/update_order'.format(self.context.absolute_url())

    @property
    def url_list_agenda_items(self):
        return '{}/agenda_items/list'.format(self.context.absolute_url())

    @property
    def url_schedule_text(self):
        return '{}/agenda_items/schedule_text'.format(self.context.absolute_url())

    @property
    def url_schedule_paragraph(self):
        return '{}/agenda_items/schedule_paragraph'.format(self.context.absolute_url())

    @property
    def url_list_unscheduled_proposals(self):
        return '{}/unscheduled_proposals'.format(self.context.absolute_url())

    @property
    def msg_unexpected_error(self):
        return translate(_('An unexpected error has occurred',
                           default='An unexpected error has occurred'),
                         context=self.request)
