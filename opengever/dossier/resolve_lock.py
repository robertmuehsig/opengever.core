from Acquisition import aq_parent
from datetime import datetime
from datetime import timedelta
from opengever.base.sentry import log_msg_to_sentry
from opengever.dossier.behaviors.dossier import IDossierMarker
from persistent.mapping import PersistentMapping
from plone import api
from zope.annotation import IAnnotations
from zope.globalrequest import getRequest
import itertools
import logging
import transaction


logger = logging.getLogger('opengever.dossier')


RESOLVE_LOCK_KEY = 'opengever.dossier.resolve_lock'
RESOLVE_LOCK_LIFETIME = timedelta(hours=24)


class ResolveLock(object):
    """Locking mechanism to prevent concurrent dossier resolution.

    This mechanism is intended to prevent users from simultaneously triggering
    the 'resolve' transition for a dossier (which would result in degraded
    performance because retries of conflicting transactions).

    We do this by issuing a persistent lock that gets committed in its own
    transaction as the very first thing in the resolution process. Further
    attempts at resolving a dossier are then rejected as long as such a lock
    exists (and hasn't expired). Once the dossier is resolved successfully,
    the lock is removed and the removal will be committed again.

    In case of an exception, we catch it, abort the transaction, remove the
    lock, commit the removal, and re-reaise the exception to be handled by
    the usual error handling in ZPublisher.

    This class implements the necessary primitives for this locking mechanism.
    The high-level implementation of the strategy described above is actually
    done in the view in opengever.dossier.resolve.
    """

    def __init__(self, context):
        self.context = context
        self.catalog = api.portal.get_tool('portal_catalog')

    def acquire(self, commit=False):
        """Acquire a resolve lock for a dossier.

        Will overwrite a possibly existing expired lock.
        """
        self.log("Acquiring resolve lock for %s..." % self.context)

        if self.txn_is_dirty():
            # Acquiring and committing the lock should always be the first
            # thing that's being done when resolving the dossier, otherwise
            # we would be committing unrelated, unexpected changes.
            #
            # Detect if that happens, but still proceed and log to sentry.
            msg = 'Dirty transaction when comitting resolve lock'
            self.log(msg)
            self.log('Registered objects: %r' % self._registered_objects())
            log_msg_to_sentry(msg, level='warning', extra={
                'registered_objects': repr(self._registered_objects())}
            )

        ann = IAnnotations(self.context)
        lockinfo = PersistentMapping({
            'timestamp': datetime.now(),
            'userid': api.user.get_current().id,
        })
        ann[RESOLVE_LOCK_KEY] = lockinfo
        self.invalidate_cache()

        if commit:
            transaction.commit()

        self.log("Resolve lock acquired.")

    def release(self, commit=False):
        """Release a previously acquired lock.

        Will raise a KeyError if no lock has been acquired.
        """
        self.log("Releasing resolve lock...")
        ann = IAnnotations(self.context)
        del ann[RESOLVE_LOCK_KEY]
        self.invalidate_cache()

        if commit:
            transaction.commit()

        self.log("Resolve lock released for %s" % self.context)

    def invalidate_cache(self):
        """Increment catalog counter to invalidate plone.app.caching ETAGs.
        """
        self.catalog._increment_counter()

    def is_expired(self, lockinfo):
        """Determine whether a lock is expired.
        """
        ts = lockinfo['timestamp']
        age = datetime.now() - ts
        expired = age > RESOLVE_LOCK_LIFETIME
        if expired:
            self.log("Resolve lock is expired (age: %s): %s" % (age, lockinfo))
        return expired

    def is_locked(self, recursive=True):
        """Determine whether a dossier currently is resolve locked.

        By default also considers a subdossier locked if any of its parent
        dossiers have a lock on them.

        If recursive=False is given, only the current dossier is checked for
        a lock (cheaper, this is used to display the state in the byline).

        If a lock exists (somewhere) but is older than RESOLVE_LOCK_LIFETIME,
        it is considered expired and treated as if it wouldn't exist.
        """
        item = self.context

        while IDossierMarker.providedBy(item):

            lockinfo = self.get_lockinfo(item)
            if lockinfo is not None and not self.is_expired(lockinfo):
                self.log("%s is resolve locked via lock on %r" % (self.context, item))
                return True

            if not recursive:
                return False

            item = aq_parent(item)

        return False

    def get_lockinfo(self, context):
        return IAnnotations(context).get(RESOLVE_LOCK_KEY)

    def log(self, msg):
        """Log a message including the current connection identifier.
        """
        conn = self.context._p_jar
        logger.info('[%r] %s' % (conn, msg))

    def _registered_objects(self):
        """Returns a list of objects changed in this transaction.

        Lifted from plone.protect.auto.
        """
        app = getRequest().PARENTS[-1]
        return list(itertools.chain.from_iterable([
            conn._registered_objects
            # skip the 'temporary' connection since it stores session objects
            # which get written all the time
            for name, conn in app._p_jar.connections.items()
            if name != 'temporary'
        ]))

    def txn_is_dirty(self):
        return bool(self._registered_objects())
