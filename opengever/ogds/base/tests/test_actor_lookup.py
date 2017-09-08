from opengever.ogds.base.actor import Actor
from opengever.testing import IntegrationTestCase


class TestActorLookup(IntegrationTestCase):

    def test_null_actor(self):
        actor = Actor.lookup('not-existing')
        self.assertEqual('not-existing', actor.get_label())
        self.assertIsNone(actor.get_profile_url())
        self.assertEqual('not-existing', actor.get_link())

    def test_inbox_actor_lookup(self):
        actor = Actor.lookup('inbox:fa')

        self.assertEqual(u'Inbox: Finanzamt', actor.get_label())
        self.assertIsNone(actor.get_profile_url())
        self.assertEqual('Inbox: Finanzamt', actor.get_link())
        self.assertEqual(u'fa_inbox_users', actor.permission_identifier)

    def test_contact_actor_lookup(self):
        self.login(self.regular_user)
        actor = Actor.lookup('contact:{}'.format(self.franz_meier.id))

        self.assertEqual('Meier Franz (meier.f@example.com)',
                         actor.get_label())
        self.assertEqual(self.franz_meier.absolute_url(),
                         actor.get_profile_url())

        link = actor.get_link()
        self.assertIn(actor.get_label(), link)
        self.assertIn(actor.get_profile_url(), link)

    def test_user_actor_ogds_user(self):
        actor = Actor.lookup('jurgen.konig')

        self.assertEqual(
            u'K\xf6nig J\xfcrgen (jurgen.konig)', actor.get_label())
        self.assertEqual('jurgen.konig', actor.permission_identifier)
        self.assertTrue(
            actor.get_profile_url().endswith('@@user-details/jurgen.konig'))

        self.assertEqual(
            u'<a href="http://nohost/plone/@@user-details/jurgen.konig">'
            u'K\xf6nig J\xfcrgen (jurgen.konig)</a>',
            actor.get_link())

        self.assertEqual(
            u'<a href="http://nohost/plone/@@user-details/jurgen.konig" '
            u'class="contenttype-opengever-actor">K\xf6nig J\xfcrgen '
            u'(jurgen.konig)</a>',
            actor.get_link(with_icon=True))

    def test_get_link_returns_safe_html(self):
        self.login(self.regular_user)

        self.franz_meier.firstname = u"Foo <b onmouseover=alert('Foo!')>click me!</b>"
        self.franz_meier.reindexObject()
        actor = Actor.lookup('contact:meier-franz')

        self.assertEquals(
            u'<a href="http://nohost/plone/kontakte/meier-franz">Meier Foo &lt;b onmouseover=alert(&apos;Foo!&apos;)&gt;click me!&lt;/b&gt; (meier.f@example.com)</a>',
            actor.get_link())


class TestActorCorresponding(IntegrationTestCase):

    def test_user_corresponds_to_current_user(self):
        actor = Actor.lookup('jurgen.konig')

        self.assertTrue(
            actor.corresponds_to(self.get_ogds_user(self.secretariat_user)))
        self.assertFalse(
            actor.corresponds_to(self.get_ogds_user(self.regular_user)))

    def test_inbox_corresponds_to_all_inbox_assigned_users(self):
        actor = Actor.lookup('inbox:fa')

        self.assertTrue(
            actor.corresponds_to(self.get_ogds_user(self.secretariat_user)))
        self.assertFalse(
            actor.corresponds_to(self.get_ogds_user(self.regular_user)))


class TestActorRepresentatives(IntegrationTestCase):

    def test_user_is_the_only_representatives_of_a_user(self):
        actor = Actor.lookup('jurgen.konig')
        self.assertEquals([self.get_ogds_user(self.secretariat_user)],
                          actor.representatives())

        actor = Actor.lookup(self.regular_user.getId())
        self.assertEquals([self.get_ogds_user(self.regular_user)],
                          actor.representatives())

    def test_all_users_of_the_inbox_group_are_inbox_representatives(self):
        actor = Actor.lookup('inbox:fa')
        self.assertItemsEqual(
            [self.get_ogds_user(self.secretariat_user)],
            actor.representatives())

    def test_contact_has_no_representatives(self):
        actor = Actor.lookup('contact:meier-franz')
        self.assertItemsEqual([], actor.representatives())
