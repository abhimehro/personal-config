import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
        original = (
            "  revision: 2\n"
            "  latest_transition: evt-x\n"
            "  latest_transition_kind: HANDOFF\n"
            "  updated_at_utc: '2026-09-06T18:00:00Z'\n"
        )
        stripped, removed = persist.strip_derived_item_lines(original)
        self.assertEqual(removed, 2)
        self.assertEqual(
            stripped,
            "  revision: 2\n  updated_at_utc: '2026-09-06T18:00:00Z'\n",
        )

    def test_git_ref_update_uses_plural_collection(self) -> None:
        from pr_lifecycle_ledger_cas import ref_path, update_ref_path

        branch = "automation/pr-lifecycle-ledger"
        self.assertIn("/git/ref/heads/", ref_path(branch))
        self.assertNotIn("/git/refs/heads/", ref_path(branch))
        self.assertIn("/git/refs/heads/", update_ref_path(branch))

    def test_run_commit_sanitizes_without_revision_bump(self) -> None:
        import pr_lifecycle_ledger_cas as cas

        ledger = self.example()
        ledger["items"][0]["latest_transition"] = "evt-2026-stage1-stage2-001"
        ledger["items"][0]["latest_transition_kind"] = "HANDOFF"
        path = self.write_ledger(ledger)
        with mock.patch.object(cas, "pointer_runtime", return_value={}):
            with mock.patch.object(
                cas, "cas_commit", return_value={"commit_sha": "a" * 40}
            ) as commit:
                result = cas.run_commit(
                    path, cas.DEFAULT_COMMIT_MESSAGE, bump_revision=False
                )
        uploaded = commit.call_args.args[1]
        self.assertNotIn("latest_transition:", uploaded)
        self.assertNotIn("latest_transition_kind:", uploaded)
        self.assertEqual(result["validator_stripped_fields"], 0)
        self.assertNotIn("latest_transition:", path.read_text(encoding="utf-8"))

    def test_cas_commit_does_not_retry_stale_bytes(self) -> None:
        import pr_lifecycle_ledger_cas as cas

        runtime = {
            "data_branch": "automation/pr-lifecycle-ledger",
            "data_path": "pr-lifecycle-ledger.yaml",
        }
        parent = {"object": {"sha": "a" * 40}}
        patches: list[str] = []

        def fail_patch(_branch: str, sha: str) -> dict:
            patches.append(sha)
            raise cas.CasError(http_code=422)

        with mock.patch.object(
            cas, "ensure_data_ref", return_value={"restored": False, "ref": parent}
        ):
            with mock.patch.object(
                cas, "read_commit", return_value={"tree": {"sha": "b" * 40}}
            ):
                with mock.patch.object(cas, "create_blob", return_value="c" * 40):
                    with mock.patch.object(cas, "create_tree", return_value="d" * 40):
                        with mock.patch.object(
                            cas, "create_commit", return_value="e" * 40
                        ) as created:
                            with mock.patch.object(
                                cas, "update_ref", side_effect=fail_patch
                            ):
                                with self.assertRaisesRegex(
                                    cas.CasError, cas.OPERATOR_CONFLICT
                                ):
                                    cas.cas_commit(runtime, "stale-bytes", "msg")
        self.assertEqual(patches, ["e" * 40])
        created.assert_called_once()

    def test_contained_output_rejects_symlink_and_escape(self) -> None:
        import pr_lifecycle_ledger_cas as cas

        nested = tempfile.TemporaryDirectory()
        self.addCleanup(nested.cleanup)
        real = Path(nested.name) / "real.yaml"
        real.write_text("ok\n", encoding="utf-8")
        link = Path(nested.name) / "link.yaml"
        link.symlink_to(real)
        with self.assertRaises(cas.CasError):
            cas.contained_output_path(link)
        with self.assertRaises(cas.CasError):
            cas.contained_output_path(Path("/etc/passwd"))

    def test_commit_parser_defaults_message(self) -> None:
        import pr_lifecycle_ledger_cas as cas

        args = cas.build_parser().parse_args(["commit", "--file", "ledger.yaml"])
        self.assertEqual(args.message, cas.DEFAULT_COMMIT_MESSAGE)

    def test_github_errors_omit_response_body(self) -> None:
        import urllib.error

        import pr_lifecycle_ledger_cas as cas

        leak = b'{"message":"secret-token-should-not-leak"}'
        error = urllib.error.HTTPError(
            "https://api.github.com/repos/x",
            500,
            "boom",
            hdrs={},
            fp=io.BytesIO(leak),
        )
        with mock.patch.object(cas._HTTPS_OPENER, "open", side_effect=error):
            with mock.patch.object(cas, "github_token", return_value="token"):
                with self.assertRaises(cas.CasError) as raised:
                    cas.github_request(
                        "GET",
                        "/repos/abhimehro/personal-config/git/ref/heads/x",
                    )
        self.assertEqual(str(raised.exception), cas.OPERATOR_ERROR)
        self.assertNotIn("secret-token", str(raised.exception))

    def test_github_api_url_rejects_non_https_and_off_origin(self) -> None:
        import pr_lifecycle_ledger_cas as cas

        url = cas.github_api_url("/repos/abhimehro/personal-config/git/ref/heads/x")
        self.assertTrue(url.startswith("https://api.github.com/"))
        with self.assertRaises(cas.CasError):
            cas.github_api_url("https://evil.example/steal")
        with self.assertRaises(cas.CasError):
            cas.github_api_url("file:///etc/passwd")

    def test_missing_ref_restore_uses_recorded_sha(self) -> None:
        import pr_lifecycle_ledger_cas as cas

        restored_sha = "3" * 40
        created = {"object": {"sha": restored_sha}}

        def fake_request(method: str, path: str, body=None):
            if method == "GET" and "/git/ref/" in path:
                raise cas.CasError(http_code=404)
            if method == "POST" and path.endswith("/git/refs"):
                self.assertEqual(body["sha"], restored_sha)
                return created
            raise AssertionError((method, path, body))

        runtime = {
            "data_branch": "automation/pr-lifecycle-ledger",
            "last_known_data_commit": restored_sha,
        }
        with mock.patch.object(cas, "github_request", fake_request):
            result = cas.ensure_data_ref(runtime)
        self.assertTrue(result["restored"])
        self.assertEqual(result["ref"], created)


if __name__ == "__main__":
    unittest.main()
