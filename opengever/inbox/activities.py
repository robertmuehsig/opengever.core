from opengever.ogds.base.actor import Actor
from opengever.inbox import _
from opengever.task import _ as tmf
from opengever.task.activities import TaskAddedActivity
from plone import api
from Products.CMFPlone import PloneMessageFactory


class ForwardingAddedActivity(TaskAddedActivity):
    """Activity representation for adding a task."""

    @property
    def kind(self):
        return PloneMessageFactory(u'forwarding-added',
                                   default=u'Forwarding added')

    @property
    def summary(self):
        actor = Actor.lookup(self.context.Creator())
        msg = _('msg_forwarding_added', u'New forwarding added by ${user}',
                mapping={'user': actor.get_label(with_principal=False)})
        return self.translate_to_all_languages(msg)

    @property
    def label(self):
        return self.translate_to_all_languages(
            _('label_forwarding_added', u'Forwarding added'))

    def collect_description_data(self, language):
        """Returns a list with [label, value] pairs.
        """
        return [
            [tmf('label_task_title', u'Task title'), self.context.title],
            [tmf('label_deadline', u'Deadline'),
             api.portal.get_localized_time(str(self.context.deadline))],
            [tmf('label_text', u'Text'), self.context.text]
        ]
