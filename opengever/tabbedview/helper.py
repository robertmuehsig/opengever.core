from zope.component import getUtility
from plone.memoize import ram

from Products.PluggableAuthService.interfaces.authservice import IPropertiedUser
from Products.CMFCore.interfaces._tools import IMemberData

from opengever.octopus.tentacle.interfaces import IContactInformation


def author_cache_key(m, i, author):
    if IPropertiedUser.providedBy(author) or IMemberData.providedBy(author):
        return author.getId()
    else:
        return author

@ram.cache(author_cache_key)
def readable_ogds_author(item, author):
    if IPropertiedUser.providedBy(author) or IMemberData.providedBy(author):
        author = author.getId()
    info = getUtility(IContactInformation)
    return info.render_link(str(author))

def linked(item, value):
    url_method = lambda: '#'
    #item = hasattr(item, 'aq_explicit') and item.aq_explicit or item
    if hasattr(item, 'getURL'):
        url_method = item.getURL
    elif hasattr(item, 'absolute_url'):
        url_method = item.absolute_url
    img = u'<img src="%s/%s"/>' % (item.portal_url(), item.getIcon)
    link = u'<a class="rollover-breadcrumb" href="%s" title="%s">%s%s</a>' % (url_method()," &gt; ".join(i['Title'] for i in item.breadcrumb_titles), img, value) 
    wrapper = u'<span class="linkWrapper">%s</span>' % link
    return wrapper