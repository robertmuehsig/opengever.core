# -*- coding: utf-8 -*-
from plone.restapi.deserializer.dxfields import DatetimeFieldDeserializer
from plone.restapi.deserializer.dxfields import DefaultFieldDeserializer
from plone.restapi.interfaces import IFieldDeserializer
from persistent.interfaces import IPersistent
from zope.component import adapter
from zope.interface import implementer
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.schema.interfaces import IDatetime
from zope.schema.interfaces import IField


@implementer(IFieldDeserializer)
@adapter(IField, IPersistent, IBrowserRequest)
class AnnotationsDefaultFieldDeserializer(DefaultFieldDeserializer):
    """Default field deserializer for objects stored in the annotations"""


@implementer(IFieldDeserializer)
@adapter(IDatetime, IPersistent, IBrowserRequest)
class AnnotationsDatetimeFieldDeserializer(DatetimeFieldDeserializer):
    """Datetime field deserializer for objects stored in the annotations"""
