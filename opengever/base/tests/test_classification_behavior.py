from ftw.builder import Builder
from ftw.builder import create
from ftw.testbrowser import browsing
from ftw.testbrowser.pages import factoriesmenu
from opengever.base.behaviors import classification
from opengever.testing import FunctionalTestCase
from plone.dexterity.fti import DexterityFTI
from plone.dexterity.utils import createContentInContainer
import transaction


class TestClassificationBehavior(FunctionalTestCase):
    use_browser = True

    def setUp(self):
        super(TestClassificationBehavior, self).setUp()
        self.grant('Contributor')

        fti = DexterityFTI('ClassificationFTI',
                           klass="plone.dexterity.content.Container",
                           global_allow=True,
                           filter_content_types=False)
        fti.behaviors = (
            'opengever.base.behaviors.classification.IClassification',)
        self.portal.portal_types._setObject('ClassificationFTI', fti)
        fti.lookupSchema()
        transaction.commit()

    @browsing
    def test_classification_behavior(self, browser):
        # Defaul view doesnt work for system users
        browser.login().open(view='folder_contents')
        self.assertIn('ClassificationFTI', factoriesmenu.addable_types())
        factoriesmenu.add('ClassificationFTI')

        browser.fill({
            'Title': u'My Object',
            'Classification': classification.CLASSIFICATION_CONFIDENTIAL,
            'Privacy layer': classification.PRIVACY_LAYER_YES,
            'Public Trial': classification.PUBLIC_TRIAL_PRIVATE,
            'Public trial statement': u'My statement'
        }).submit()

        self.assertEquals(
            '{0}/classificationfti/view'.format(self.portal.absolute_url()),
            browser.url)

        # Get the created object:
        obj = self.portal.get('classificationfti')
        self.assertNotEquals(None, obj)
        self.assertEquals(classification.CLASSIFICATION_CONFIDENTIAL,
                          obj.classification)
        self.assertEquals(classification.PRIVACY_LAYER_YES, obj.privacy_layer)
        self.assertEquals(classification.PUBLIC_TRIAL_PRIVATE,
                          obj.public_trial)
        self.assertEquals(u'My statement',
                          obj.public_trial_statement)

        # Create a subitem:
        subobj = createContentInContainer(obj,
                                          'ClassificationFTI',
                                          title='testobject')
        transaction.commit()

        browser.open(subobj, view='edit')
        classification_options = browser.css(
            '#form-widgets-IClassification-classification option').text
        self.assertNotIn(classification.CLASSIFICATION_UNPROTECTED,
                         classification_options)
        self.assertIn(classification.CLASSIFICATION_CLASSIFIED,
                      classification_options)

        privacy_options = browser.css(
            '#form-widgets-IClassification-privacy_layer option').text
        self.assertNotIn(classification.PRIVACY_LAYER_NO, privacy_options)

        public_trial_options = browser.css(
            '#form-widgets-IClassification-public_trial option').text
        self.assertEquals(classification.PUBLIC_TRIAL_OPTIONS,
                          public_trial_options)

    def test_public_trial_default_value_is_unchecked(self):
        repo = create(Builder('repository').titled('New repo'))
        self.assertEquals(classification.PUBLIC_TRIAL_UNCHECKED,
                          repo.public_trial)

    def test_public_trial_is_no_longer_restricted_on_subitems(self):
        repo = create(Builder('repository')
                      .titled('New repo')
                      .having(
                          public_trial=classification.PUBLIC_TRIAL_PRIVATE))
        subrepo = create(Builder('repository').titled('New repo').within(repo))

        self.assertEquals(classification.PUBLIC_TRIAL_UNCHECKED,
                          subrepo.public_trial)
