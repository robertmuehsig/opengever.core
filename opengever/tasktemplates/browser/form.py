from AccessControl import Unauthorized
from Acquisition import aq_inner, aq_parent
from Products.CMFPlone.interfaces.siteroot import IPloneSiteRoot
from Products.CMFPlone.utils import getToolByName
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.statusmessages.interfaces import IStatusMessage
from datetime import datetime, timedelta
from ftw.table import helper
from ftw.table.interfaces import ITableGenerator
from ftw.table.column import Column
from opengever.dossier.behaviors.dossier import IDossierMarker, IDossier
from opengever.ogds.base.utils import get_current_client
from opengever.ogds.base.interfaces import IContactInformation
from plone.dexterity.utils import createContent, addContentToContainer
from zope.component import queryUtility, getUtility
from zope.event import notify
from zope.lifecycleevent import ObjectCreatedEvent, ObjectAddedEvent

meta_data = {}
meta_data['templates'] = {
    'root': 'rows',
    'totalProperty': 'totalCount',
    'fields': [
        {'name': 'path_radiobutton', 'type': 'string' ,'hideable' : False},
        {'name': 'created', 'type': 'string'},
        {'name': 'Title', 'type': 'string'}
    ],
    'columns': [
        {'id':'path_radiobutton', 'width': 30, 'menuDisabled':True, 'sortable': False, 'dataIndex': 'path_radiobutton', 'hideable' : False},
        {'id':'Title','header': 'Title', 'sortable': True, 'dataIndex': 'Title'},
        {'id':'created','header': 'Created', 'width': 160, 'sortable': True, 'dataIndex': 'created'}
    ],
}

meta_data['tasks'] = {
    'root': 'rows',
    'totalProperty': 'totalCount',
    'fields': [
        {'name': 'path_checkbox', 'type': 'string'},
        {'name': 'created', 'type': 'string'},
        {'name': 'Title', 'type': 'string'}
    ],
    'columns': [
        {'id':'path_checkbox','header': '', 'width': 30,'sortable': False, 'hideable':False, 'menuDisabled':True, 'dataIndex': 'path_checkbox'},
        {'id':'Title','header': 'Title', 'sortable': True, 'dataIndex': 'Title'},
        {'id':'created','header': 'Created', 'width': 160, 'sortable': True, 'dataIndex': 'created'}
    ],
}

def path_checkbox(item, value):
    preselected = item.getObject().preselected
    return """
            <input type="checkbox"
                    class="noborder"
                    name="paths:list"
                    id="%s" value="%s"
                    alt="Select %s"
                    title="Select %s"
                    %s
                    >""" % (item.id,
                            item.getPath(),
                            item.Title,
                            item.Title,
                            preselected and 'checked="checked"' or None
                            )

class AddForm(BrowserView):

    __call__ = ViewPageTemplateFile("form.pt")

    steps = {
        'templates': {
            'columns' : (('', helper.path_radiobutton), 'Title' ,('created', helper.readable_date)),
            # 'columns' : (
            #                  Column(hideable = False,
            #                         resizeable = False,
            #                         sortable = False,
            #                         width = '10',
            #                         transform = helper.path_radiobutton
            #                         ),
            #                  Column(id = 'title',
            #                         header = 'Title',
            #                         data_index = 'sortable_title',
            #                         auto_expand_column = True,
            #                         transform = helper.linked
            #                         ),
            #                  Column(id = 'created',
            #                         header = 'Created',
            #                         transform = helper.readable_date)
            #  ),
            'types': ('TaskTemplateFolder',),
            'states': ('tasktemplate-state-activ',),
            },
        'tasks': {
            'columns' : (('', path_checkbox), 'Title', ('created', helper.readable_date)),
            'types': ('TaskTemplate',),
            'states':'*',

            }
        }

    def listing(self, show='templates'):
        """returns a listing of either TaskTemplateFolders or TaskTemplates"""
        sort_on = self.request.get('sort', 'Title')
        sort_on = {'Title':'sortable_title'}.get(sort_on, sort_on)
        sort_order = self.request.get('dir', 'ASC')
        sort_order = {'ASC': 'ascending', 'DESC':'descending'}.get(sort_order)
        templates = self.context.portal_catalog(
                        Type=self.steps[show]['types'],
                        sort_on = sort_on,
                        sort_order = sort_order
                        
        )
        generator = queryUtility(ITableGenerator, 'ftw.tablegenerator')
        return generator.generate(templates,
                                  self.steps[show]['columns'],
                                  sortable = True,
                                  output='json',
                                  meta_data = meta_data[show]
                                  )

    def create(self, paths):
        """generate the task templates"""
        for path in paths:
            template = self.context.restrictedTraverse(path)
            deadline = datetime.today()+timedelta(template.deadline)


            data = dict(title=template.title,
                        issuer=self.replace_interactive_user(template.issuer),
                        responsible=\
                            self.replace_interactive_user(template.responsible),
                        task_type=template.task_type,
                        text=template.text,
                        deadline=deadline,
                        )

            if template.responsible_client == 'interactive_users':
                info = getUtility(IContactInformation)
                responsible_assigned_clients = tuple(
                    info.get_assigned_clients(data['responsible']))
                current_client = get_current_client()
                if not responsible_assigned_clients or \
                        current_client in responsible_assigned_clients:
                    data['responsible_client'] = current_client.client_id
                else:
                    data['responsible_client'] = \
                        responsible_assigned_clients[0].client_id
            else:
                data['responsible_client'] = template.responsible_client

            task = createContent('opengever.task.task', **data)
            notify(ObjectCreatedEvent(task))
            task = addContentToContainer(self.context,
                                         task,
                                         checkConstraints=True)
            notify(ObjectAddedEvent(task))
            task.reindexObject()

        IStatusMessage(self.request).addStatusMessage("tasks created",
                                                      type="info")
        return self.request.RESPONSE.redirect(self.context.absolute_url() + \
                                                  '#tasks')

    def replace_interactive_user(self, principal):
        """Replaces interactive users in the principal.
        """

        if principal == 'responsible':
            # find the dossier
            dossier = self.context
            while not IDossierMarker.providedBy(dossier):
                if IPloneSiteRoot.providedBy(dossier):
                    raise ValueError('Could not find dossier')
                dossier = aq_parent(aq_inner(dossier))
            # get the responsible of the dossier
            wrapped_dossier = IDossier(dossier)
            return wrapped_dossier.responsible

        elif principal == 'current_user':
            # get the current user
            mtool = getToolByName(self.context, 'portal_membership')
            member = mtool.getAuthenticatedMember()
            if not member:
                raise Unauthorized()
            return member.getId()

        else:
            return principal
