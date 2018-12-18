from ftw.upgrade import UpgradeStep


class Add_opengeverMeeting_AddPeriod_toLawgiverWorkflows(UpgradeStep):
    """Add 'opengever.meeting: Add Period' to lawgiver workflows.
    """

    def __call__(self):
        self.install_upgrade_profile()
        self.update_workflow_security(
            ['opengever_committee_workflow'], reindex_security=False)
