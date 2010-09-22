"""
The transporter module defines functionality for adding a document
from any context of a foreign client into a existing task.
"""

from Products.statusmessages.interfaces import IStatusMessage
from five import grok
from opengever.ogds.base.interfaces import IContactInformation
from opengever.ogds.base.interfaces import ITransporter
from opengever.task import _
from opengever.task.task import ITask
from plone.directives import form
from plone.z3cform import layout
from z3c.form.interfaces import HIDDEN_MODE
from zope import schema
from zope.component import getUtility
import os
import urllib
import z3c.form


class NoItemsSelected(Exception):
    pass


# ------------------- CHOSE DOSSIER --------------------------

class IChooseDossierSchema(form.Schema):
    """ Form for choosing a source dossier on my home client
    """

    source_dossier = schema.Choice(
        title=_(u'label_source_dossier', default=u'Dossier'),
        description=_(u'help_source_dossier',
                      default=u'Select a source dossier'),
        vocabulary=u'opengever.ogds.base.HomeDossiersVocabulary',
        required=True,
        )


class ChooseDossierForm(z3c.form.form.Form):
    fields = z3c.form.field.Fields(IChooseDossierSchema)
    label = _(u'title_attach_document_form', u'Attach document')
    ignoreContext = True

    @z3c.form.button.buttonAndHandler(_(u'button_cancel', default=u'Cancel'))
    def handle_cancel(self, action):
        return self.request.RESPONSE.redirect(self.context.absolute_url())

    @z3c.form.button.buttonAndHandler(_(u'button_continue',
                                        default=u'Continue'))
    def handle_continue(self, action):
        data, errors = self.extractData()
        if not errors:
            data = urllib.urlencode({'source_dossier' :
                                         data['source_dossier']})
            target = self.context.absolute_url() + \
                '/@@choose_source_document?' + data
            return self.request.RESPONSE.redirect(target)


class ChooseDossierView(layout.FormWrapper, grok.CodeView):
    grok.context(ITask)
    grok.name('choose_source_dossier')
    form = ChooseDossierForm

    def __init__(self, *args, **kwargs):
        layout.FormWrapper.__init__(self, *args, **kwargs)
        grok.CodeView.__init__(self, *args, **kwargs)

    __call__ = layout.FormWrapper.__call__



# ------------------- CHOSE DOCUMENT --------------------------


class IChooseDocumentSchema(IChooseDossierSchema):
    """ Select a document from the previously selected dossier
    """

    source_document = schema.Choice(
        title=_(u'label_source_document', default=u'Document'),
        description=_(u'help_source_document', default=u'Select a document'),
        vocabulary=u'opengever.ogds.base.DocumentInSelectedDossierVocabulary',
        required=True,
        )



class ChooseDocumentForm(z3c.form.form.Form):
    fields = z3c.form.field.Fields(IChooseDocumentSchema)
    label = _(u'title_attach_document_form', u'Attach document')
    ignoreContext = True

    def update(self):
        # try to get the dossier ath from different locations
        field_name = 'form.widgets.source_dossier'
        dossier = self.request.get(
            field_name, self.request.get(
                'source_dossier', self.request.get('dossier_path'), None))
        if isinstance(dossier, list):
            dossier = str(dossier[0])
        if dossier:
            # set the dossier path for later user in the
            # DocumentInSelectedDossierVocabularyFactory
            self.request.set('dossier_path', dossier)
            # set the dossier path for the widget
            self.request.set(field_name, dossier)
        return super(ChooseDocumentForm, self).update()

    def updateWidgets(self):
        super(ChooseDocumentForm, self).updateWidgets()
        self.widgets['source_dossier'].mode = HIDDEN_MODE

    @z3c.form.button.buttonAndHandler(_(u'button_cancel', default=u'Cancel'))
    def handle_cancel(self, action):
        return self.request.RESPONSE.redirect(self.context.absolute_url())

    @z3c.form.button.buttonAndHandler(_(u'button_back', default=u'Back'))
    def handle_back(self, action):
        url = os.path.join(self.context.absolute_url(),
                           '@@choose_source_dossier')
        return self.request.RESPONSE.redirect(url)


    @z3c.form.button.buttonAndHandler(_(u'button_attach', default=u'Attach'))
    def handle_attach(self, action):
        data, errors = self.extractData()
        if not errors:
            document = data.get('source_document')

            # XXX: implement multiple clients support with additional
            # wizard view
            IStatusMessage(self.request).addStatusMessage(
                'DEBUG NOTICE: No multiple clients support implemented yet!',
                type='warning')

            info = getUtility(IContactInformation)
            home_clients = info.get_assigned_clients()
            # XXX
            client = home_clients[0]
            cid = client.client_id

            trans = getUtility(ITransporter)
            trans.transport_from(self.context, cid, document)
            url = self.context.absolute_url()
            return self.request.RESPONSE.redirect(url)



class ChooseDocumentView(layout.FormWrapper, grok.CodeView):
    grok.context(ITask)
    grok.name('choose_source_document')
    form = ChooseDocumentForm

    def __init__(self, *args, **kwargs):
        layout.FormWrapper.__init__(self, *args, **kwargs)
        grok.CodeView.__init__(self, *args, **kwargs)

    __call__ = layout.FormWrapper.__call__


