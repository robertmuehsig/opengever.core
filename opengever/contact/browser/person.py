from opengever.base.browser.modelforms import ModelAddForm
from opengever.base.browser.modelforms import ModelEditForm
from opengever.base.handlebars import prepare_handlebars_template
from opengever.base.model import CONTENT_TITLE_LENGTH
from opengever.base.model import FIRSTNAME_LENGTH
from opengever.base.model import LASTNAME_LENGTH
from opengever.contact import _
from opengever.contact.models import MailAddress
from opengever.contact.models import Organization
from opengever.contact.models import OrgRole
from opengever.contact.models import PhoneNumber
from opengever.contact.models.person import Person
from opengever.ogds.base.actor import Actor
from path import Path
from plone.supermodel import model
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from z3c.form import field
from zope import schema
from zope.interface import implements
from zope.publisher.interfaces import IPublishTraverse
from zope.publisher.interfaces.browser import IBrowserView


TEMPLATES_DIR = Path(__file__).joinpath('..', 'templates').abspath()


class PersonView(BrowserView):
    """Overview for a Person SQL object.
    """

    implements(IBrowserView, IPublishTraverse)

    template = ViewPageTemplateFile('templates/person.pt')
    latest_participations = ViewPageTemplateFile(
        'templates/latest_participations.pt')

    def __init__(self, context, request):
        super(PersonView, self).__init__(context, request)
        self.model = self.context.model
        self.request = request

    def __call__(self):
        return self.template()

    def participations_fetch_url(self):
        return self.context.model.get_url('participations/list')

    def prepare_model_tabs(self, viewlet):
        if not self.model.is_editable():
            return tuple()

        return viewlet.prepare_edit_tab(
            self.model.get_edit_url(self.context.parent))

    def get_actor_link(self, archive):
        return Actor.lookup(archive.actor_id).get_link()

    def get_org_roles(self):
        query = OrgRole.query.filter_by(person=self.context.model)
        return query.join(Organization).order_by(Organization.name).all()

    def latest_participations_template(self):
        return self.latest_participations()


class IPersonModel(model.Schema):
    """Person model schema interface."""

    salutation = schema.TextLine(
        title=_(u"label_salutation", default=u"Salutation"),
        max_length=CONTENT_TITLE_LENGTH,
        required=False)

    academic_title = schema.TextLine(
        title=_(u"label_academic_title", default=u"Academic title"),
        max_length=CONTENT_TITLE_LENGTH,
        required=False)

    firstname = schema.TextLine(
        title=_(u"label_firstname", default=u"Firstname"),
        max_length=FIRSTNAME_LENGTH,
        required=True)

    lastname = schema.TextLine(
        title=_(u"label_lastname", default=u"Lastname"),
        max_length=LASTNAME_LENGTH,
        required=True)

    description = schema.Text(
        title=_(u'label_description', default=u'Description'),
        required=False,
        missing_value=u'',
        default=u'',
        )


class IPhoneNumber(model.Schema):

    # phone number
    label = schema.TextLine(
        title=_(u'label_phone_number_label', default=u'Label phone number'),
        required=False,
        missing_value=u'',
        default=u'',
    )

    phone_number = schema.TextLine(
        title=_(u'label_phone_number', default=u'Phone number'),
        required=False,
        missing_value=u'',
        default=u'',
    )


class IMailAddress(model.Schema):

    # phone number
    label = schema.TextLine(
        title=_(u'label_mail_address_label', default=u'Label mail address'),
        required=False,
        missing_value=u'',
        default=u'',
    )

    address = schema.TextLine(
        title=_(u'label_mail_address', default=u'Mail address'),
        required=False,
        missing_value=u'',
        default=u'',
    )


class IAddress(model.Schema):

    # phone number
    label = schema.TextLine(
        title=_(u'label_mail_address_label', default=u'Label mail address'),
        required=False,
        missing_value=u'',
        default=u'',
    )

    street = schema.Text(
        title=_(u'label_street', default=u'Street'),
        required=False,
        missing_value=u'',
        default=u'',
    )

    zip_code = schema.TextLine(
        title=_(u'label_zip_code', default=u'Zip code'),
        required=False,
        missing_value=u'',
        default=u'',
    )

    city = schema.TextLine(
        title=_(u'label_city', default=u'City'),
        required=False,
        missing_value=u'',
        default=u'',
    )

    country = schema.TextLine(
        title=_(u'label_country', default=u'Country'),
        required=False,
        missing_value=u'',
        default=u'',
    )


class AddPerson(ModelAddForm):
    schema = IPersonModel
    model_class = Person
    additionalSchemata = (IPhoneNumber, IMailAddress, IAddress)

    label = _('Add Person', default=u'Add Person')

    def nextURL(self):
        return self._created_object.get_url()

    def create(self, data):
        self.validate(data)

        person_data = {}
        for field_name in self.schema:
            person_data[field_name] = data[field_name]

        person = self.model_class(**person_data)

        self.add_phone_number(data, person)
        self.add_email_address(data, person)
        self.add_address(data, person)

        return person

    def add_phone_number(self, data, person):
        phone_data = {}
        for field_name in IPhoneNumber:
            phone_data[field_name] = data['IPhoneNumber.{}'.format(field_name)]

        if phone_data.get('phone_number'):
            PhoneNumber(contact=person, **phone_data)

    def add_email_address(self, data, person):
        mail_data = {}
        for field_name in IMailAddress:
            mail_data[field_name] = data['IMailAddress.{}'.format(field_name)]

        if mail_data.get('address'):
            MailAddress(contact=person, **mail_data)

    def add_address(self, data, person):
        address_data = {}
        for field_name in IAddress:
            address_data[field_name] = data['IAddress.{}'.format(field_name)]

        if any(address_data.values()):
            MailAddress(contact=person, **address_data)


class EditPerson(ModelEditForm):

    fields = field.Fields(IPersonModel)
    template = ViewPageTemplateFile('templates/person_edit.pt')

    def __init__(self, context, request):
        super(EditPerson, self).__init__(context, request, context.model)

    def get_fetch_url(self):
        return self.context.model.get_url('mails/list')

    def get_create_mail_url(self):
        return self.context.model.get_url('mails/add')

    def nextURL(self):
        return self.context.model.get_url()

    def prepare_model_tabs(self, viewlet):
        if not self.model.is_editable():
            return tuple()

        return viewlet.prepare_edit_tab(
            self.model.get_edit_url(self.context.parent), is_selected=True)

    def render_handlebars_email_template(self):
        return prepare_handlebars_template(TEMPLATES_DIR.joinpath('email.html'))
