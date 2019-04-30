from ftw.testbrowser import browsing
from opengever.testing import IntegrationTestCase
from opengever.trash.trash import Trasher
from plone import api
from urllib import urlencode


class TestSearchEndpoint(IntegrationTestCase):

    api_headers = {'Accept': 'application/json'}

    def search_catalog(self, context, query):
        catalog = api.portal.get_tool('portal_catalog')
        path = '/'.join(context.getPhysicalPath())
        query['path'] = path
        return [b.getURL() for b in catalog(query)]

    def search_restapi(self, browser, context, query):
        browser.open(
            context,
            view='@search?%s' % urlencode(query),
            headers=self.api_headers)
        return [item['@id'] for item in browser.json['items']]

    @browsing
    def test_able_to_search_for_trashed_docs(self, browser):
        self.login(self.regular_user, browser)

        doc_url = self.document.absolute_url()

        # Guard assertion - both direct catalog searches and REST API
        # should give the same results with no trashed documents
        catalog_results = self.search_catalog(
            self.dossier,
            dict(sort_on='path',
                 portal_type='opengever.document.document'))

        api_results = self.search_restapi(
            browser, self.dossier,
            dict(sort_on='path',
                 portal_type='opengever.document.document'))

        self.assertIn(doc_url, catalog_results)
        self.assertIn(doc_url, api_results)
        self.assertEqual(catalog_results, api_results)

        # Trash self.document - should now disappear from regular results
        Trasher(self.document).trash()

        catalog_results = self.search_catalog(
            self.dossier,
            dict(sort_on='path',
                 portal_type='opengever.document.document'))

        api_results = self.search_restapi(
            browser, self.dossier,
            dict(sort_on='path',
                 portal_type='opengever.document.document'))

        self.assertNotIn(doc_url, catalog_results)
        self.assertNotIn(doc_url, api_results)
        self.assertEqual(catalog_results, api_results)

        # But trashed docs can still be searched for explicitly, both
        # directly via catalog and the REST API @search endpoint
        catalog_results = self.search_catalog(
            self.dossier,
            dict(sort_on='path',
                 portal_type='opengever.document.document',
                 trashed=True))

        api_results = self.search_restapi(
            browser, self.dossier,
            {'sort_on': 'path',
             'portal_type': 'opengever.document.document',
             'trashed:boolean': '1'})

        self.assertEqual([doc_url], catalog_results)
        self.assertEqual([doc_url], api_results)
