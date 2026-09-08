import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pr_lifecycle_persist as persist  # noqa: E402
import pr_lifecycle_schema as schema  # noqa: E402
import pr_lifecycle_validation as validator  # noqa: E402
from pr_lifecycle_ledger import apply_transition, initial_projection  # noqa: E402


class TestPrLifecyclePersist(unittest.TestCase):
    def example(self) -> dict:
        return validator.load_yaml(ROOT / "tasks/pr-lifecycle-ledger.example.yaml")

    def write_ledger(self, ledger: dict) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "runtime-ledger.yaml"
        path.write_text(yaml.safe_dump(ledger, sort_keys=False), encoding="utf-8")
        return path

    def test_schema_rejects_persisted_projection_fields(self) -> None:
        ledger = self.example()
        ledger["items"][0]["latest_transition"] = "evt-2026-stage1-stage2-001"
        ledger["items"][0]["latest_transition_kind"] = "HANDOFF"
        with self.assertRaisesRegex(ValueError, "latest_transition"):
            schema.validate_schema(ledger)

    def test_validate_strips_known_derived_fields(self) -> None:
        ledger = self.example()
        ledger["items"][0]["latest_transition"] = "evt-2026-stage1-stage2-001"
        ledger["items"][0]["latest_transition_kind"] = "HANDOFF"
        stripped = validator.validate(self.write_ledger(ledger))
        self.assertEqual(stripped, 2)

    def test_persistable_item_drops_projection_after_apply_transition(self) -> None:
        projected = initial_projection()
        event = {
            "event_id": "evt-test-handoff",
            "kind": "HANDOFF",
            "to_state": "STAGE2_QUEUED",
            "to_owner": "stage2",
            "next_owner": "stage2",
            "terminal_disposition": None,
            "resulting_item_revision": 1,
        }
        apply_transition(event, projected)
        self.assertEqual(projected["latest_transition"], "evt-test-handoff")
        persisted = persist.persistable_item(projected)
        self.assertNotIn("latest_transition", persisted)
        self.assertNotIn("latest_transition_kind", persisted)
        self.assertEqual(persisted["revision"], 1)

    def test_unknown_extra_item_fields_still_fail_closed(self) -> None:
        ledger = self.example()
        ledger["items"][0]["unexpected_writer_field"] = "nope"
        with self.assertRaisesRegex(ValueError, "unexpected_writer_field"):
            validator.validate(self.write_ledger(ledger))

    def test_cli_sanitizes_then_passes_without_strict(self) -> None:
        ledger = self.example()
        ledger["items"][0]["latest_transition"] = "evt-2026-stage1-stage2-001"
        ledger["items"][0]["latest_transition_kind"] = "HANDOFF"
        path = self.write_ledger(ledger)
        default = subprocess.run(
            [sys.executable, "scripts/validate_pr_lifecycle_artifacts.py", str(path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertIn("PR_LIFECYCLE_VALID", default.stdout)
        self.assertIn("PR_LIFECYCLE_SANITIZED", default.stderr)
        strict = subprocess.run(
            [
                sys.executable,
                "scripts/validate_pr_lifecycle_artifacts.py",
                "--strict-persisted",
                str(path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(strict.returncode, 1, strict.stderr)
        self.assertIn("persisted projection fields", strict.stderr)

    def test_line_strip_preserves_surrounding_yaml(self) -> None:
        original = "  revision: 2\n  latest_transition: evt-x\n  latest_transition_kind: HANDOFF\n  updated_at_utc: '2026-09-06T18:00:00Z'\n"
        stripped, removed = persist.strip_derived_item_lines(original)
        self.assertEqual(removed, 2)
        self.assertEqual(
            stripped,
            "  revision: 2\n  updated_at_utc: '2026-09-06T18:00:00Z'\n",
        )


if __name__ == "__main__":
    unittest.main()
