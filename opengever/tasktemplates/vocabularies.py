from five import grok
from opengever.base.browser.wizard.interfaces import IWizardDataStorage
from opengever.ogds.base.vocabularies import OrgUnitsVocabularyFactory
from opengever.tasktemplates import _
from opengever.tasktemplates.browser.trigger import get_datamanger_key
from plone import api
from zope.component import getUtility
from zope.globalrequest import getRequest
from zope.i18n import translate
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


class ResponsibleOrgUnitVocabularyFactory(OrgUnitsVocabularyFactory):
    """Vocabulary of all orgunits extend by the "interactive users"
    unit.
    """

    grok.provides(IVocabularyFactory)
    grok.name('opengever.tasktemplates.ResponsibleOrgUnitVocabulary')

    def key_value_provider(self):
        yield ('interactive_users',
               translate(_(u'client_interactive_users',
                           default=u'Interactive users'),
                         context=getRequest()))
        for item in super(ResponsibleOrgUnitVocabularyFactory, self).key_value_provider():
            yield item


class ActiveTasktemplatefoldersVocabulary(grok.GlobalUtility):
    grok.provides(IVocabularyFactory)
    grok.name('opengever.tasktemplates.active_tasktemplatefolders')

    def __call__(self, context):
        terms = []
        for templatefolder in self.get_tasktemplatefolder():
            terms.append(SimpleTerm(value=templatefolder.UID,
                                    token=templatefolder.UID,
                                    title=templatefolder.Title))

        return SimpleVocabulary(terms)

    def get_tasktemplatefolder(self):
        return api.content.find(
            portal_type='opengever.tasktemplates.tasktemplatefolder',
            review_state='tasktemplatefolder-state-activ')


class TasktemplatesVocabulary(grok.GlobalUtility):
    grok.provides(IVocabularyFactory)
    grok.name('opengever.tasktemplates.tasktemplates')

    def __call__(self, context):
        terms = []
        tasktemplatefolder = self.get_selected_tasktemplatefolder(context)
        assert tasktemplatefolder, 'No selectd tasktemplatefolder'

        for template in self.get_tasktemplates(tasktemplatefolder):
            terms.append(SimpleTerm(value=template.UID,
                                    token=template.UID,
                                    title=template.Title))

        return SimpleVocabulary(terms)

    def get_selected_tasktemplatefolder(self, context):
        dm = getUtility(IWizardDataStorage)
        uid = dm.get(get_datamanger_key(context), 'tasktemplatefolder')
        return api.content.get(UID=uid)

    def get_tasktemplates(self, tasktemplatefolder):
        return api.content.find(
            context=tasktemplatefolder,
            portal_type='opengever.tasktemplates.tasktemplate')
