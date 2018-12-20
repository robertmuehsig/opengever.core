from plone.dexterity.content import Container
from plone.supermodel import model


class IPeriod(model.Schema):
    """Marker interface for period."""


class Period(Container):

    @staticmethod
    def get_current(committee):
        pass
