from opengever.activity import ACTIVITY_TRANSLATIONS
from opengever.activity.base import BaseActivity
from opengever.meeting import _
from opengever.ogds.base.actor import Actor
from plone import api


def actor_link():
    return Actor.lookup(api.user.get_current().id).get_link()


class ProposalCommentedActivitiy(BaseActivity):
    """Activity representation for commenting a proposal.
    """
    kind = 'proposal-commented'

    @property
    def summary(self):
        return self.translate_to_all_languages(
            _('proposal_history_label_commented', u'Proposal commented by ${user}',
              mapping={'user': actor_link()}))

    @property
    def label(self):
        return self.translate_to_all_languages(ACTIVITY_TRANSLATIONS[self.kind])

    @property
    def description(self):
        return {}


class ProposalTransitionActivity(BaseActivity):
    """Activity which represents a proposal transition change.
    """

    def __init__(self, context, request):
        super(ProposalTransitionActivity, self).__init__(context, request)

    @property
    def description(self):
        return {}

    @property
    def label(self):
        return self.translate_to_all_languages(ACTIVITY_TRANSLATIONS[self.kind])


class ProposalSubmittedActivity(ProposalTransitionActivity):
    kind = 'proposal-transition-submit'

    @property
    def summary(self):
        return self.translate_to_all_languages(
            _('proposal_history_label_submitted', u'Submitted by ${user}',
              mapping={'user': actor_link()}))
