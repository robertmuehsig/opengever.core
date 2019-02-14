from datetime import date
from dateutil.relativedelta import relativedelta
from ftw.table.helper import readable_date
from ftw.testbrowser import browsing
from opengever.dossier.behaviors.dossier import IDossier
from opengever.dossier.behaviors.dossier import IDossierMarker
from opengever.tabbedview.helper import linked
from opengever.testing import IntegrationTestCase
from plone import api
from plone.uuid.interfaces import IUUID
from Products.CMFPlone.utils import safe_unicode


class TestDossierListing(IntegrationTestCase):

    listing_fields = ['',
                      'Reference Number',
                      'Title',
                      'Review state',
                      'Responsible',
                      'Start',
                      'End',
                      'Keywords']

    @staticmethod
    def get_contained_folders(folder):
        children = folder.getChildNodes()
        return [
            child
            for child in children
            if IDossierMarker.providedBy(child)
            if api.user.has_permission('View', obj=child)
            ]

    @staticmethod
    def get_folder_data(dossier):
        data = ['',
                dossier.get_reference_number(),
                dossier.title,
                api.content.get_state(dossier),
                dossier.responsible_label,
                readable_date(dossier, IDossier(dossier).start),
                readable_date(dossier, IDossier(dossier).end),
                ', '.join(IDossier(dossier).keywords),
                ]
        return data

    def get_listing_data(self, repo_folder):
        folders = self.get_contained_folders(repo_folder)
        listing_data = [(self.get_folder_data(folder), folder.modified())
                        for folder in folders]
        listing_data.sort(key=lambda data: data[1])
        return [data for data, modified in listing_data]

    def open_repo_with_filter(self, browser, dossier, filter_name, subjects=[]):
        data = {'dossier_state_filter': filter_name}
        if subjects:
            data['subjects'] = subjects

        browser.visit(
            dossier,
            view='tabbedview_view-dossiers',
            data=data)

    @staticmethod
    def filter_data(data, state='dossier-state-active'):
        return filter(lambda folder_data: folder_data[3] == state, data)

    def solr_response(self, *facets):
        solr_facets = []
        for facet in facets:
            solr_facets.extend([safe_unicode(facet), 1])

        return {u'facet_counts': {u'facet_fields': {u'Subject': solr_facets}}}

    @browsing
    def test_get_folder_data(self, browser):
        """ As all other tests test against data generated from the fixture
        using get_folder_data method, we make that the data generated by this
        method does not get changed.
        """
        self.login(self.regular_user, browser=browser)
        self.assertEquals(
            ['',
             'Client1 1.1 / 2',
             u'Abgeschlossene Vertr\xe4ge',
             'dossier-state-resolved',
             u'Ziegler Robert (robert.ziegler)',
             '01.01.1995',
             '31.12.2000',
             u'Vertr\xe4ge'],
            self.get_folder_data(self.expired_dossier)
            )

    @browsing
    def test_lists_only_active_dossiers_by_default(self, browser):
        self.login(self.regular_user, browser=browser)
        browser.visit(self.leaf_repofolder, view='tabbedview_view-dossiers')

        data = browser.css('.listing').first.lists()
        self.assertEqual(self.listing_fields, data.pop(0))

        expected_data = self.get_listing_data(self.leaf_repofolder)
        expected_data_filtered = self.filter_data(expected_data)

        # Make sure that there were dossiers to filter out
        self.assertTrue(len(expected_data) - len(expected_data_filtered) > 0)

        self.assertEqual(expected_data_filtered, data)

    @browsing
    def test_list_every_dossiers_with_the_all_filter(self, browser):
        self.login(self.regular_user, browser=browser)

        self.open_repo_with_filter(
            browser, self.leaf_repofolder, 'filter_all')

        data = browser.css('.listing').first.lists()
        self.assertEqual(self.listing_fields, data.pop(0))

        expected_data = self.get_listing_data(self.leaf_repofolder)

        # Make sure that there are dossiers that would normally get filtered out.
        inactive_dossiers_data = self.filter_data(expected_data, state='dossier-state-inactive')
        resolved_dossiers_data = self.filter_data(expected_data, state='dossier-state-resolved')
        self.assertTrue(len(inactive_dossiers_data) > 0)
        self.assertTrue(len(resolved_dossiers_data) > 0)

        self.assertEqual(expected_data, data)

    @browsing
    def test_active_closed_filter_available(self, browser):
        self.login(self.regular_user, browser=browser)
        browser.visit(self.leaf_repofolder, view='tabbedview_view-dossiers')

        self.assertEquals(['label_tabbedview_filter_all', 'Active', 'overdue'],
                          browser.css('.state_filters a').text)

    @browsing
    def test_expired_filter_only_avaiable_for_record_managers(self, browser):
        self.login(self.regular_user, browser=browser)
        browser.visit(self.leaf_repofolder, view='tabbedview_view-dossiers')
        self.assertEquals(['label_tabbedview_filter_all', 'Active', 'overdue'],
                          browser.css('.state_filters a').text)

        self.login(self.records_manager, browser=browser)
        browser.visit(self.leaf_repofolder, view='tabbedview_view-dossiers')
        self.assertEquals(
            ['label_tabbedview_filter_all', 'Active', 'expired', 'overdue'],
            browser.css('.state_filters a').text)

    @browsing
    def test_expired_filters_shows_only_dossiers_with_expired_retention_period(self, browser):
        self.login(self.records_manager, browser=browser)

        self.open_repo_with_filter(
            browser, self.leaf_repofolder, 'filter_retention_expired')

        data = browser.css('.listing').first.lists()
        self.assertEqual(self.listing_fields, data.pop(0))

        expected_data = [self.get_folder_data(self.expired_dossier)]
        self.assertItemsEqual(expected_data, data)

        # update end dates to have expired retention periods
        IDossier(self.expired_dossier).end = date.today()
        self.expired_dossier.reindexObject()
        IDossier(self.inactive_dossier).end = date.today() - relativedelta(years=16)
        self.inactive_dossier.reindexObject()

        self.open_repo_with_filter(
            browser, self.leaf_repofolder, 'filter_retention_expired')

        data = browser.css('.listing').first.lists()
        self.assertEqual(self.listing_fields, data.pop(0))

        expected_data = [self.get_folder_data(self.inactive_dossier)]
        self.assertItemsEqual(expected_data, data)

    @browsing
    def test_expired_filters_exclude_archived_dossiers(self, browser):
        self.login(self.records_manager, browser=browser)

        # update end dates to have expired retention periods
        IDossier(self.expired_dossier).end = date.today() - relativedelta(years=16)
        self.expired_dossier.reindexObject()
        IDossier(self.inactive_dossier).end = date.today() - relativedelta(years=16)
        self.inactive_dossier.reindexObject()

        self.open_repo_with_filter(
            browser, self.leaf_repofolder, 'filter_retention_expired')

        data = browser.css('.listing').first.lists()
        self.assertIn(self.get_folder_data(self.expired_dossier), data)

        api.content.transition(self.expired_dossier, to_state="dossier-state-archived")

        self.open_repo_with_filter(
            browser, self.leaf_repofolder, 'filter_retention_expired')

        data = browser.css('.listing').first.lists()
        self.assertNotIn(self.get_folder_data(self.expired_dossier), data)

    @browsing
    def test_expired_filters_is_hidden_on_subdossier_listings(self, browser):
        self.login(self.records_manager, browser=browser)
        browser.visit(self.dossier, view='tabbedview_view-subdossiers')
        self.assertEquals(['label_tabbedview_filter_all', 'Active'],
                          browser.css('.state_filters a').text)

    @browsing
    def test_linked_helper_adds_uid_data_attribute_using_obj(self, browser):
        self.login(self.regular_user, browser)
        browser.open_html(linked(self.dossier, 'Title'))
        self.assertEquals(browser.css('a').first.attrib['data-uid'],
                          IUUID(self.dossier))

    @browsing
    def test_linked_helper_adds_uid_data_attribute_using_brain(self, browser):
        self.login(self.regular_user, browser)
        uid = IUUID(self.dossier)
        brain = self.portal.portal_catalog(UID=uid)[0]

        browser.open_html(linked(brain, 'Dummy'))
        self.assertEquals(browser.css('a').first.attrib['data-uid'], uid)

    @browsing
    def test_subdossier_lists_children_but_not_itself(self, browser):
        self.login(self.regular_user, browser)
        browser.open(self.subdossier, view='tabbedview_view-subdossiers')
        expected_content = [
            u'Reference Number Title Review state Responsible Start End Keywords',
            u'Client1 1.1 / 1.1.1 Subsubdossier dossier-state-active 31.08.2016 '
            u'Subsubkeyword, Subsubkeyw\xf6rd',
            ]
        self.assertEqual(expected_content, browser.css('.listing tr').text)

    @browsing
    def test_empty_subdossier_does_not_list_itself(self, browser):
        self.login(self.regular_user, browser)
        browser.open(self.subsubdossier, view='tabbedview_view-subdossiers')
        expected_content = ['No contents']
        self.assertEqual(expected_content, browser.css('p').text)

    @browsing
    def test_overdue_filter_shows_open_dossiers_with_expired_end_date(self, browser):
        self.login(self.records_manager, browser=browser)
        self.open_repo_with_filter(browser, self.leaf_repofolder, 'filter_overdue')

        self.assertEqual([], browser.css('.listing'))

        IDossier(self.dossier).end = date.today() - relativedelta(days=1)
        self.dossier.reindexObject()

        IDossier(self.empty_dossier).end = date.today()
        self.empty_dossier.reindexObject()

        self.open_repo_with_filter(browser, self.leaf_repofolder, 'filter_overdue')
        data = browser.css('.listing').first.lists()
        data.pop(0)  # removes row headings.

        self.assertEqual(1, len(data))
        self.assertItemsEqual(self.get_folder_data(self.dossier), data[0])

    @browsing
    def test_filter_dossiers_by_subjects(self, browser):
        self.activate_feature('solr')
        self.login(self.regular_user, browser=browser)

        self.mock_solr(response_json=self.solr_response('Wichtig'))

        self.open_repo_with_filter(browser, self.leaf_repofolder, 'filter_all')
        self.assertLess(1, len(browser.css('.listing tbody tr')))

        self.open_repo_with_filter(
            browser, self.leaf_repofolder, 'filter_all', ['Wichtig'])
        self.assertEqual(1, len(browser.css('.listing tbody tr')))
