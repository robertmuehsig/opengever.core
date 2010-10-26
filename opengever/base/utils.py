from collective.elephantvocabulary import wrap_vocabulary
from five import grok
from zope.schema.interfaces import IContextSourceBinder


@grok.provider(IContextSourceBinder)
def get_communities_vocabulary(context):
    """Returns the vdex vocabulary with communities. Hides some
    terms according to portal_registry configuration.
    """

    voc = wrap_vocabulary(
        u'opengever.base.communities',
        hidden_terms_from_registry=u'opengever.base.interfaces.' +\
            u'IBaseSettings.vocabulary_disabled_communities')
    return voc(context)
