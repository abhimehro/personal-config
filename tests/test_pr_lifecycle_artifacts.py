import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "lifecycle_validator", ROOT / "scripts/validate_pr_lifecycle_artifacts.py"
)
validator = importlib.util.module_from_spec(SPEC)
sys.modules["lifecycle_validator"] = validator
SPEC.loader.exec_module(validator)


class TestPrLifecycleArtifacts(unittest.TestCase):
    def test_checked_in_ledger_and_exports_validate(self):
        validator.validate(ROOT / "tasks/pr-lifecycle-ledger.yaml")

    def test_all_prompt_sources_include_continuity_contract(self):
        validator._validate_prompts()

    def test_duplicate_yaml_keys_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "duplicate.yaml"
            path.write_text("schema_version: '1.1'\nschema_version: '1.1'\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                validator._load_yaml(path)

    def test_terminal_item_requires_terminal_disposition_and_no_owner(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "invalid-terminal.yaml"
            path.write_text((ROOT / "tasks/pr-lifecycle-ledger.example.yaml").read_text(encoding="utf-8").replace("terminal_disposition: null", "terminal_disposition: null", 1).replace("lifecycle_state: STAGE3_RECONCILIATION", "lifecycle_state: TERMINAL", 1), encoding="utf-8")
            with self.assertRaises(ValueError):
                validator.validate(path)


if __name__ == "__main__":
    unittest.main()
