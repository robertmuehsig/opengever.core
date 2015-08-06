from ftw.builder import Builder
from ftw.builder import create
from ftw.pdfgenerator.builder import Builder as PDFBuilder
from ftw.pdfgenerator.interfaces import ILaTeXLayout
from ftw.pdfgenerator.interfaces import ILaTeXView
from ftw.pdfgenerator.utils import provide_request_layer
from ftw.testbrowser import browsing
from ftw.testing import MockTestCase
from opengever.dossier.behaviors.dossier import IDossierMarker
from opengever.latex import opentaskreport
from opengever.latex.layouts.default import DefaultLayout
from opengever.latex.opentaskreport import IOpenTaskReportLayer
from opengever.latex.testing import LATEX_ZCML_LAYER
from opengever.testing import FunctionalTestCase
from plone.app.testing import login
from zExceptions import Unauthorized
from zope.component import adaptedBy
from zope.component import getMultiAdapter
from zope.interface.verify import verifyClass
from zope.publisher.interfaces.browser import IDefaultBrowserLayer


class TestOpenTaskReportPDFView(MockTestCase):

    layer = LATEX_ZCML_LAYER

    def test_is_registered(self):
        context = self.providing_stub([IDossierMarker])
        request = self.providing_stub([IDefaultBrowserLayer])

        self.replay()
        view = getMultiAdapter((context, request),
                               name='pdf-open-task-report')

        self.assertTrue(isinstance(
                        view, opentaskreport.OpenTaskReportPDFView))


class TestOpenTaskReportLaTeXView(MockTestCase):

    layer = LATEX_ZCML_LAYER

    def test_component_is_registered(self):
        context = self.create_dummy()
        request = self.providing_stub([opentaskreport.IOpenTaskReportLayer])
        layout = self.providing_stub([ILaTeXLayout])

        self.replay()

        view = getMultiAdapter((context, request, layout), ILaTeXView)

        self.assertEqual(type(view), opentaskreport.OpenTaskReportLaTeXView)

    def test_implements_interface(self):
        self.replay()
        self.assertTrue(ILaTeXView.implementedBy(
                        opentaskreport.OpenTaskReportLaTeXView))

        verifyClass(ILaTeXView, opentaskreport.OpenTaskReportLaTeXView)

    def test_adapts_layer(self):
        self.replay()
        context_iface, request_iface, layout_iface = adaptedBy(
            opentaskreport.OpenTaskReportLaTeXView)

        self.assertEqual(request_iface, opentaskreport.IOpenTaskReportLayer)


class TestOpenTaskReport(FunctionalTestCase):

    use_default_fixture = False

    def setUp(self):
        super(TestOpenTaskReport, self).setUp()

        self.user, self.org_unit, self.admin_unit = create(
            Builder('fixture').with_all_unit_setup())

        self.hans = create(Builder('ogds_user')
                           .having(userid='hans.meier',
                                   firstname='Hans',
                                   lastname='Meier')
                           .assign_to_org_units([self.org_unit]))
        create(Builder('user').with_userid('hans.meier'))

        self.peter = create(Builder('ogds_user')
                            .having(userid='peter.peter',
                                    firstname='Peter',
                                    lastname='Peter'))

        self.task = create(Builder("task")
                           .having(task_type='comment',
                                   issuer='peter.peter',
                                   responsible='hans.meier'))

        provide_request_layer(self.task.REQUEST, IOpenTaskReportLayer)
        layout = DefaultLayout(self.task, self.task.REQUEST, PDFBuilder())
        self.opentaskreport = getMultiAdapter(
            (self.task, self.task.REQUEST, layout), ILaTeXView)

    @browsing
    def test_render_adds_browser_layer(self, browser):
        browser.login().open(view='pdf-open-task-report')
        self.assertTrue(IOpenTaskReportLayer.providedBy(self.request))

    @browsing
    def test_open_task_report_action_visible_for_user_with_correct_group(self, browser):
        browser.login().open()
        self.assertIsNotNone(browser.find('Open tasks report'))

    @browsing
    def test_open_task_report_action_not_visible_for_user_with_wrong_group(self, browser):
        browser.login('hans.meier').open()
        self.assertIsNone(browser.find('Open tasks report'))

    def test_actor_labels_are_visible_in_task_listing(self):
        row = self.opentaskreport.get_data_for_item(self.task.get_sql_object())
        self.assertIn(self.peter.label(with_principal=False), row)
        self.assertIn(self.hans.label(with_principal=False), row)

    @browsing
    def test_smoke_open_task_report_view_allowed(self, browser):
        browser.login().open(view='pdf-open-task-report')

    @browsing
    def test_open_task_report_view_not_allowed_raises_unauthorized(self, browser):
        with self.assertRaises(Unauthorized):
            browser.login('hans.meier').open(view='pdf-open-task-report')

    def test_task_report_is_only_available_for_current_inbox_users(self):
        self.assertTrue(
            self.portal.unrestrictedTraverse('pdf-open-task-report-allowed')())

        login(self.portal, 'hans.meier')
        self.assertFalse(
            self.portal.unrestrictedTraverse('pdf-open-task-report-allowed')())
