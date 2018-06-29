from opengever.private.interfaces import IPrivateContainer
from Products.Five.browser import BrowserView


class IsPrivateFolder(BrowserView):

    def __call__(self):
        return IPrivateContainer.providedBy(self.context)
