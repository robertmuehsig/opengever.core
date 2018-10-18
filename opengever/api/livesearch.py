from opengever.base.interfaces import ISearchSettings
from opengever.base.solr import OGSolrContentListing
from plone import api
from plone.restapi.services.search.get import SearchGet
from zope.component import getMultiAdapter


class GeverLiveSearchGet(SearchGet):

    def reply(self):
        search_term = self.request.form.get('q', None)
        limit = int(self.request.form.get('limit', 10))
        portal_path = '/'.join(api.portal.get().getPhysicalPath())
        path = '{}/{}'.format(
            portal_path,
            self.request.form.get('path', '/').lstrip('/'),
        ).rstrip('/')

        if not search_term:
            return []

        if api.portal.get_registry_record(
                'use_solr', interface=ISearchSettings, default=False):
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
