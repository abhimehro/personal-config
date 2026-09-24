"""CLI contract tests for the pipeline health entrypoint."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import yaml  # noqa: E402
from tests.pr_lifecycle_helpers import (  # noqa: E402
    EXAMPLE_LEDGER,
    run_health_cli,
    schema_valid_starved_ledger,
)

class TestPipelineHealthCli(unittest.TestCase):
    def _write(self, ledger: dict[str, object]) -> Path:
        """Write a temporary ledger and register its cleanup."""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "runtime-ledger.yaml"
        path.write_text(yaml.safe_dump(ledger, sort_keys=False), encoding="utf-8")
        return path

    def test_cli_exit_2_on_starvation(self) -> None:
        """Verify starvation exits with status 2 and reports the condition."""
        path = self._write(schema_valid_starved_ledger())
        proc = run_health_cli(str(path))
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("starvation=true", proc.stdout)

    def test_cli_sanitizes_persisted_projection_fields(self) -> None:
        """Verify persisted projection fields do not hide starvation."""
        ledger = schema_valid_starved_ledger()
        ledger["items"][0]["latest_transition"] = "evt-2026-stage1-stage2-001"
        ledger["items"][0]["latest_transition_kind"] = "HANDOFF"
        path = self._write(ledger)
        proc = run_health_cli(str(path))
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("starvation=true", proc.stdout)

    def test_cli_json_and_exit_0_when_clear(self) -> None:
        """Verify healthy ledgers produce JSON and a successful exit."""
        proc = run_health_cli("--json", str(EXAMPLE_LEDGER))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["starvation"])
        self.assertEqual(payload["stage2_work_item_count"], 0)
        self.assertGreaterEqual(payload["stage2_owned_item_count"], 1)

    def test_cli_exit_1_on_schema_invalid_items_mapping(self) -> None:
        """Verify malformed ledger input exits with a schema error."""
        path = self._write({"items": [], "stage2_work_items": []})
        proc = run_health_cli(str(path))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("PR_LIFECYCLE_HEALTH_ERROR", proc.stderr)

    def test_cli_refuses_pointer_copies_and_non_ledger(self) -> None:
        """Verify the CLI rejects pointer documents and arbitrary mappings."""
        path_pointer = ROOT / "tasks" / "pr-lifecycle-ledger.yaml"
        self.assertTrue(path_pointer.is_file())
        proc = run_health_cli(str(path_pointer))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("refusing main-branch pointer", proc.stderr)

        pointer = yaml.safe_load(path_pointer.read_text(encoding="utf-8"))
        cases = (
            ("copied pointer", pointer, "refusing main-branch pointer"),
            ("arbitrary mapping", {"foo": "bar"}, "not a runtime ledger mapping"),
        )
        for label, document, needle in cases:
            with self.subTest(label):
                copied = self._write(document)
                result = run_health_cli(str(copied))
                self.assertEqual(result.returncode, 1)
                self.assertIn(needle, result.stderr)

