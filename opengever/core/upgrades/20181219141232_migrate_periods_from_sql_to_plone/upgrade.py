from opengever.base.interfaces import INoSeparateConnectionForSequenceNumbers
from opengever.core.upgrade import SQLUpgradeStep
from plone.dexterity.utils import createContentInContainer
from sqlalchemy.sql.expression import column
from sqlalchemy.sql.expression import table
from zope.interface import alsoProvides
import logging


LOG = logging.getLogger('ftw.upgrade')


periods_table = table(
    'periods',
    column('id'),
    column('committee_id'),
    column('title'),
    column('date_from'),
    column('date_to'),
    column('decision_sequence_number'),
    column('meeting_sequence_number'),
)


class MigratePeriodsFromSqlToPlone(SQLUpgradeStep):
    """Migrate periods from sql to plone.
    """

    def migrate(self):
        # do not open separate connections when increasing the sequence
        # number as that breaks atomicity of the upgrade and may cause
        # conflicts with the long-running upgrade transaction
        alsoProvides(self.portal.REQUEST,
                     INoSeparateConnectionForSequenceNumbers)

        query = {'portal_type': 'opengever.meeting.committee'}
        msg = 'Migrate periods from sql to plone'
        for committee in self.objects(query, msg):
            self.migrate_periods_for_committee(committee)

    def migrate_periods_for_committee(self, committee):
        committee_model = committee.load_model()

        periods_for_committee = self.execute(
            periods_table.select()
            .where(periods_table.c.committee_id == committee_model.committee_id)
        ).fetchall()

        # this is unexpected and wrong, but not wrong enough to completely
        # abort the upgrades. as now users creating periods is plone-ish the
        # periods can be created manually as of now
        if not periods_for_committee:
            LOG.warning(u"No periods found for commitee {}".format(
                committee_model.title))
            return

        for period in periods_for_committee:
            self.create_plone_period(period, committee)
            self.drop_sql_period(period)

    def create_plone_period(self, period, committee):
        attributes = dict(
            title=period.title,
            start=period.date_from,
            end=period.date_to,
            decision_sequence_number=period.decision_sequence_number,
            meeting_sequence_number=period.meeting_sequence_number,
        )
        createContentInContainer(committee,
                                 'opengever.meeting.period',
                                 **attributes)

    def drop_sql_period(self, period):
        self.execute(
            periods_table.delete()
            .where(periods_table.c.id == period.id)
        )
