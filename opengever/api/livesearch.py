from opengever.base.interfaces import ISearchSettings
from opengever.base.solr import OGSolrContentListing
from plone import api
from plone.registry.interfaces import IRegistry
from plone.restapi.services.search.get import SearchGet
from zope.component import getMultiAdapter
from zope.component import getUtility


class GeverLiveSearchGet(SearchGet):

    def reply(self):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(ISearchSettings)

        search_term = self.request.form.get('q', None)
        limit = int(self.request.form.get('limit', 10))
        path = self.request.form.get(
            'path', '/'.join(api.portal.get().getPhysicalPath()))

        if not search_term:
            return []

        if settings.use_solr:
            view = getMultiAdapter((self.context, self.request),
                                   name=u'livesearch_reply')
            view.search_term = search_term
            view.limit = limit
            view.path = path

            return [
                {
                    'title': entry.Title(),
                    '@id': entry.getURL(),
                    '@type': entry.portal_type,
                }
                for entry in OGSolrContentListing(view.results())]

        else:
            del self.request.form['q']
            self.request.form.update({
                'SearchableText': search_term + '*',
                'sort_limit': limit,
                'path': path
            })

            results = super(GeverLiveSearchGet, self).reply()
            return [
                {
                    'title': entry['title'],
                    '@id': entry['@id'],
                    '@type': entry['@type'],
                }
                for entry in results['items'][:limit]]
