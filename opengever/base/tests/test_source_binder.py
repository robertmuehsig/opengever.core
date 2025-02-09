from ftw.testbrowser import browsing
from opengever.base.source import DossierPathSourceBinder
from opengever.base.source import RepositoryPathSourceBinder
from opengever.testing import IntegrationTestCase


class TestRepositoryPathSourceBinder(IntegrationTestCase):

    def test_navigation_tree_query_is_limited_to_current_repository(self):
        self.login(self.regular_user)

        source_binder = RepositoryPathSourceBinder()

        source = source_binder(self.branch_repofolder)
        self.assertEqual({'query': '/plone/ordnungssystem'},
                         source.navigation_tree_query['path'])

        source = source_binder(self.leaf_repofolder)
        self.assertEqual({'query': '/plone/ordnungssystem'},
                         source.navigation_tree_query['path'])


class TestDossierSourceBinder(IntegrationTestCase):

    def test_only_objects_inside_the_maindossier_are_selectable(self):
        self.login(self.regular_user)

        self.document.title = 'Test open'
        self.subdocument.title = 'Test sub'
        self.inactive_document.title = 'Test inactive'
        [obj.reindexObject() for obj in
         (self.document, self.subdocument, self.inactive_document)]

        source_binder = DossierPathSourceBinder(
            portal_type=("opengever.document.document", "ftw.mail.mail"),
            navigation_tree_query={
                'object_provides':
                ['opengever.dossier.behaviors.dossier.IDossierMarker',
                 'opengever.document.document.IDocumentSchema',
                 'opengever.task.task.ITask',
                 'ftw.mail.mail.IMail']}
        )

        source = source_binder(self.dossier)
        self.assertEqual(['Test open', 'Test sub'],
                         [term.title for term in source.search('Test')])

        source = source_binder(self.subdossier)
        self.assertEqual(['Test open', 'Test sub'],
                         [term.title for term in source.search('Test')])

        source = source_binder(self.inactive_dossier)
        self.assertEqual(['Test inactive'],
                         [term.title for term in source.search('Test')])


class TestRelatedDossierAutocomplete(IntegrationTestCase):

    @browsing
    def test_related_dossier_autocomplete_uses_solr_when_feature_enabled(self, browser):
        self.activate_feature('solr')
        self.solr = self.mock_solr('solr_autocomplete_dossier.json')

        self.login(self.dossier_responsible, browser)
        browser.open(
            self.dossier,
            view='@@edit/++widget++form.widgets.IDossier.relatedDossier/@@autocomplete-search?q=empty'
        )
        self.assertEqual(
            '/plone/ordnungssystem/fuhrung/vertrage-und-vereinbarungen/dossier-7|An empty dossier',
            browser.contents
        )
        self.assert_solr_called(
            self.solr, 'empty', rows=20, fl=['path'],
            filters=[u'object_provides:opengever.dossier.behaviors.dossier.IDossierMarker']
        )

    @browsing
    def test_related_dossier_autocomplete_uses_catalog_when_solr_disabled(self, browser):
        self.login(self.dossier_responsible, browser)
        browser.open(
            self.dossier,
            view='@@edit/++widget++form.widgets.IDossier.relatedDossier/@@autocomplete-search?q=empty'
        )
        self.assertEqual(
            '/plone/ordnungssystem/fuhrung/vertrage-und-vereinbarungen/dossier-7|An empty dossier',
            browser.contents
        )


class TestAddableDossierTemplatesAutocomplete(IntegrationTestCase):

    @browsing
    def test_addable_dossier_autocomplete_uses_solr_when_feature_enabled(self, browser):
        self.activate_feature('solr')
        self.solr = self.mock_solr('solr_autocomplete_dossiertemplate.json')

        self.login(self.administrator, browser)
        browser.open(
            self.empty_repofolder,
            view=''
            '@@edit/++widget++form.widgets.IRestrictAddableDossierTemplates.addable_dossier_templates/'
            '@@autocomplete-search?q=Bauvorhaben'
        )
        self.assertEqual(
            '/plone/vorlagen/dossiertemplate-1|Bauvorhaben klein',
            browser.contents
        )
        self.assert_solr_called(
            self.solr, 'Bauvorhaben', rows=20, fl=['path'],
            filters=[u'portal_type:opengever.dossier.dossiertemplate',
                     u'is_subdossier:false']
        )

    @browsing
    def test_addable_dossier_autocomplete_uses_catalog_when_solr_disabled(self, browser):
        self.login(self.administrator, browser)
        browser.open(
            self.empty_repofolder,
            view=''
            '@@edit/++widget++form.widgets.IRestrictAddableDossierTemplates.addable_dossier_templates/'
            '@@autocomplete-search?q=Bauvorhaben'
        )
        self.assertEqual(
            '/plone/vorlagen/dossiertemplate-1|Bauvorhaben klein',
            browser.contents
        )
