from opengever.ogds.models.user_settings import IUserSettings
from opengever.ogds.models.user_settings import UserSettings
from opengever.webactions.validation import get_validation_errors
from plone import api
from plone.restapi.deserializer import json_body
from plone.restapi.services import Service
from zExceptions import BadRequest
from zope.schema import getFieldsInOrder


def serialize_setting(setting):
    data = {}
    for name, field in getFieldsInOrder(IUserSettings):
        if setting:
            data[name] = getattr(setting, name)
        else:
            data[name] = field.default

    return data


class UserSettingsGet(Service):

    def reply(self):
        userid = api.user.get_current().id
        setting = UserSettings.query.filter_by(userid=userid).one_or_none()
        return serialize_setting(setting)


class UserSettingsPatch(Service):

    def reply(self):
        userid = api.user.get_current().id
        data = json_body(self.request)

        errors = get_validation_errors(data, IUserSettings)
        if errors:
            raise BadRequest(errors)

        setting = UserSettings.get_or_create(userid)
        for name, field in getFieldsInOrder(IUserSettings):
            if name in data:
                setattr(setting, name, data[name])

        prefer = self.request.getHeader("Prefer")
        if prefer == "return=representation":
            self.request.response.setStatus(200)
            return serialize_setting(setting)

        return self.reply_no_content()
