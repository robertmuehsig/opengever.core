from ftw.datepicker.widget import DatePickerFieldWidget
from opengever.base import _ as bmf
from opengever.meeting import _
from plone.autoform import directives as form
from plone.autoform.interfaces import IFormFieldProvider
from plone.supermodel import model
from zope import schema
from zope.interface import alsoProvides


class IPeriodSchema(model.Schema):
    """Base schema for period."""

    model.fieldset(
        u'common',
        label=bmf(u'fieldset_common', default=u'Common'),
        fields=[
            u'start',
            u'end',
            u'decision_sequence_number',
            u'meeting_sequence_number',
        ],
    )

    form.widget(start=DatePickerFieldWidget)
    start = schema.Date(
        title=_('label_date_from', default='Start date'),
        required=True,
    )

    form.widget(end=DatePickerFieldWidget)
    end = schema.Date(
        title=_('label_date_to', default='End date'),
        required=True,
    )

    form.write_permission(decision_sequence_number='cmf.ManagePortal')
    decision_sequence_number = schema.Int(
        title=_(u'label_decision_sequence_number',
                default=u'Sequence number for decisions'),
        required=True,
        default=0,
    )

    form.write_permission(meeting_sequence_number='cmf.ManagePortal')
    meeting_sequence_number = schema.Int(
        title=_(u'label_meeting_sequence_number',
                default=u'Sequence number for meetings'),
        required=True,
        default=0,
    )


alsoProvides(IPeriodSchema, IFormFieldProvider)
