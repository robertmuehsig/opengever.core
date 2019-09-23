# -*- coding: utf-8 -*-
from Acquisition import aq_base
from Acquisition.interfaces import IAcquirer
from plone.restapi.deserializer import json_body
from plone.restapi.exceptions import DeserializationError
from plone.restapi.interfaces import IDeserializeFromJson
from plone.restapi.interfaces import ISerializeToJson
from plone.restapi.services import Service
from plone.restapi.services.content.utils import add
from plone.restapi.services.content.utils import create
from Products.CMFPlone.utils import safe_hasattr
from zExceptions import BadRequest
from zExceptions import Unauthorized
from zope.component import queryMultiAdapter
from zope.event import notify
from zope.interface import alsoProvides
from zope.lifecycleevent import ObjectCreatedEvent

import plone.protect.interfaces


class FolderPost(Service):
    """Copy of plone.restapi.services.content.add.FolderPost
    """

    def reply(self):
        data = json_body(self.request)

        self.type = data.get("@type", None)
        self.id = data.get("id", None)
        self.title = data.get("title", None)

        if not self.type:
            raise BadRequest("Property '@type' is required")

        # Disable CSRF protection
        if "IDisableCSRFProtection" in dir(plone.protect.interfaces):
            alsoProvides(self.request, plone.protect.interfaces.IDisableCSRFProtection)

        try:
            self.obj = create(self.context, self.type, id_=self.id, title=self.title)
        except Unauthorized as exc:
            self.request.response.setStatus(403)
            return dict(error=dict(type="Forbidden", message=str(exc)))
        except BadRequest as exc:
            self.request.response.setStatus(400)
            return dict(error=dict(type="Bad Request", message=str(exc)))

        # Acquisition wrap temporarily to satisfy things like vocabularies
        # depending on tools
        temporarily_wrapped = False
        if IAcquirer.providedBy(self.obj) and not safe_hasattr(self.obj, "aq_base"):
            self.obj = self.obj.__of__(self.context)
            temporarily_wrapped = True

        # Update fields
        deserializer = queryMultiAdapter((self.obj, self.request), IDeserializeFromJson)
        if deserializer is None:
            self.request.response.setStatus(501)
            return dict(
                error=dict(message="Cannot deserialize type {}".format(self.obj.portal_type))
            )

        try:
            deserializer(validate_all=True, create=True)
        except DeserializationError as e:
            self.request.response.setStatus(400)
            return dict(error=dict(type="DeserializationError", message=str(e)))

        if temporarily_wrapped:
            self.obj = aq_base(self.obj)

        if not getattr(deserializer, "notifies_create", False):
            notify(ObjectCreatedEvent(self.obj))

        self.obj = add(self.context, self.obj, rename=not bool(self.id))

        self.request.response.setStatus(201)
        self.request.response.setHeader("Location", self.obj.absolute_url())

        serializer = queryMultiAdapter((self.obj, self.request), ISerializeToJson)

        serialized_obj = serializer()

        # HypermediaBatch can't determine the correct canonical URL for
        # objects that have just been created via POST - so we make sure
        # to set it here
        serialized_obj["@id"] = self.obj.absolute_url()

        return serialized_obj
