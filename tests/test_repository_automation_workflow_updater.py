import os
import sys
from unittest import TestCase
from unittest.mock import DEFAULT, MagicMock, patch

# Stub out the optional third-party `yaml` dependency so this test remains
# stdlib-only (per AGENTS.md / CONTRIBUTING.md: tests must not require pip
# installs). `repository_automation_common` imports `yaml` at module load
# time, but `run_workflow_updater` itself does not use it.
sys.modules.setdefault("yaml", MagicMock())

sys.path.append(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ".github/scripts",
    )
)

from repository_automation_tasks import run_workflow_updater


class TestRunWorkflowUpdater(TestCase):
    def setUp(self):
        self.patcher = patch.multiple(
            "repository_automation_tasks",
            workflow_file_plans=DEFAULT,
            flattened_updates=DEFAULT,
            write_result=DEFAULT,
            writes_allowed=DEFAULT,
            ensure_gh_token=DEFAULT,
            close_invalid_prs=DEFAULT,
            allowed_workflow_updates=DEFAULT,
            apply_workflow_updates=DEFAULT,
            create_pr_for_current_changes=DEFAULT,
            create=True,
        )
        self.mocks = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_run_workflow_updater_no_updates(self):
        self.mocks["flattened_updates"].return_value = []
        self.mocks["write_result"].return_value = {"status": "success"}

        result = run_workflow_updater({})
        self.assertEqual(result, {"status": "success"})
        self.mocks["write_result"].assert_called_once()
        args, _kwargs = self.mocks["write_result"].call_args
        self.assertEqual(args[0], "workflow-updater")
        self.assertEqual(args[1], ("success", "No GitHub Action updates were detected."))
        self.assertEqual(args[3], {"updates": []})

    def test_run_workflow_updater_writes_disabled(self):
        self.mocks["flattened_updates"].return_value = [
            {
                "file": "main.yml",
                "action": "actions/checkout",
                "current": "v1",
                "target": "v2",
                "old": "uses: actions/checkout@v1",
                "new": "uses: actions/checkout@v2",
            }
        ]
        self.mocks["writes_allowed"].return_value = False
        self.mocks["ensure_gh_token"].return_value = True
        self.mocks["write_result"].return_value = {"status": "warning"}

        result = run_workflow_updater({})
        self.assertEqual(result, {"status": "warning"})
        args, _kwargs = self.mocks["write_result"].call_args
        self.assertEqual(args[0], "workflow-updater")
        self.assertEqual(args[1][0], "warning")
        self.assertIn("Draft PR creation is disabled or writes are not allowed", args[2])

    def test_run_workflow_updater_success(self):
        self.mocks["flattened_updates"].return_value = [
            {
                "file": "main.yml",
                "action": "actions/checkout",
                "current": "v1",
                "target": "v2",
                "old": "uses: actions/checkout@v1",
                "new": "uses: actions/checkout@v2",
            }
        ]
        self.mocks["writes_allowed"].return_value = True
        self.mocks["ensure_gh_token"].return_value = True
        self.mocks["allowed_workflow_updates"].return_value = True
        self.mocks["create_pr_for_current_changes"].return_value = "http://pr-url"
        self.mocks["write_result"].return_value = {"status": "success"}

        config = {"workflow_updater": {"create_draft_pr": True}}
        result = run_workflow_updater(config)
        self.assertEqual(result, {"status": "success"})
        args, _kwargs = self.mocks["write_result"].call_args
        self.assertEqual(args[0], "workflow-updater")
        self.assertEqual(args[1][0], "success")
        self.assertEqual(args[3]["pull_request_url"], "http://pr-url")
        self.mocks["apply_workflow_updates"].assert_called_once()
        self.mocks["create_pr_for_current_changes"].assert_called_once()
