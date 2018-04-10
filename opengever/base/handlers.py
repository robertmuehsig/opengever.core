from ftw.upgrade.helpers import update_security_for
from opengever.base.model import create_session
from opengever.base.model.favorite import Favorite
from opengever.base.oguid import Oguid
from plone import api
from Products.CMFCore.CMFCatalogAware import CatalogAware
from zope.lifecycleevent import IObjectRemovedEvent


def object_moved_or_added(context, event):
    if IObjectRemovedEvent.providedBy(event):
        return

    # Update object security after moving or copying.
    # Specifically, this is needed for the case where an object is moved out
    # of a location where a Placeful Workflow Policy applies to a location
    # where it doesn't.
    #
    #  Plone then no longer provides the placeful workflow for that object,
    # but doesn't automatically update the object's security.
    #
    # We use ftw.upgrade's update_security_for() here to correctly
    # recalculate security, but do the reindexing ourselves because otherwise
    # Plone will do it recursively (unnecessarily so).
    changed = update_security_for(context, reindex_security=False)
    if changed:
        catalog = api.portal.get_tool('portal_catalog')
        catalog.reindexObject(context, idxs=CatalogAware._cmf_security_indexes,
                              update_metadata=0)


def remove_favorites(context, event):
    """Event handler which removes all existing favorites for the
    current context.
    """
    oguid = Oguid.for_object(context)

    stmt = Favorite.__table__.delete().where(Favorite.oguid == oguid)
    create_session().execute(stmt)
