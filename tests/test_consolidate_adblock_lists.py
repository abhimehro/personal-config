import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

# Explicitly add the script directory to sys.path so we can import it
script_dir = Path(__file__).parent.parent / "adguard" / "scripts"
sys.path.append(str(script_dir.resolve()))

from consolidate_adblock_lists import (
    create_json_structure,
    extract_allowlist_from_file,
    extract_domains_from_rules,
    load_json_file,
    process_allowlist_files,
    process_tracker_files,
    run_consolidation,
    write_text_files,
)


class TestExtractDomainsFromRules(unittest.TestCase):

    def test_happy_path(self):
        rules = [{"PK": "example.com"}, {"PK": "test.com"}]
        result = extract_domains_from_rules(rules)
        self.assertEqual(result, ["example.com", "test.com"])

    def test_missing_pk(self):
        rules = [{"PK": "example.com"}, {"other": "value"}, {"PK": "test.com"}]
        result = extract_domains_from_rules(rules)
        self.assertEqual(result, ["example.com", "test.com"])

    def test_empty_rules(self):
        result = extract_domains_from_rules([])
        self.assertEqual(result, [])


class TestLoadJsonFile(unittest.TestCase):

    @patch("builtins.open", new_callable=mock_open, read_data='{"key": "value"}')
    def test_valid_json_happy_path(self, mock_file):
        # 1. Valid JSON file (happy path, returns expected dict)
        result = load_json_file("dummy_path.json")
        self.assertEqual(result, {"key": "value"})
        mock_file.assert_called_once_with("dummy_path.json", "r", encoding="utf-8")

    @patch("builtins.open")
    def test_file_not_found_error(self, mock_file):
        # 2. FileNotFoundError (file does not exist)
        mock_file.side_effect = FileNotFoundError("No such file or directory")

        # Suppress print output for clean test output
        with patch("sys.stdout", new_callable=unittest.mock.MagicMock):
            result = load_json_file("nonexistent_path.json")

        self.assertIsNone(result)

    @patch("builtins.open", new_callable=mock_open, read_data="{invalid_json: 123")
    def test_json_decode_error(self, mock_file):
        # 3. json.JSONDecodeError (malformed JSON)
        with patch("sys.stdout", new_callable=unittest.mock.MagicMock):
            result = load_json_file("malformed_path.json")

        self.assertIsNone(result)

    @patch("builtins.open")
    def test_permission_error(self, mock_file):
        # 4. PermissionError (file not readable)
        mock_file.side_effect = PermissionError("Permission denied")

        with patch("sys.stdout", new_callable=unittest.mock.MagicMock):
            result = load_json_file("unreadable_path.json")

        self.assertIsNone(result)

    @patch("builtins.open", new_callable=mock_open, read_data="")
    def test_empty_file(self, mock_file):
        # 5. Empty file (0 bytes)
        with patch("sys.stdout", new_callable=unittest.mock.MagicMock):
            result = load_json_file("empty_path.json")

        self.assertIsNone(result)

    @patch("builtins.open", new_callable=mock_open, read_data='["item1", "item2"]')
    def test_valid_json_unexpected_type(self, mock_file):
        # 6. Valid JSON, unexpected type (array or primitive instead of dict)
        result = load_json_file("array_path.json")

        # The function should just parse whatever JSON returns, in this case a list
        self.assertEqual(result, ["item1", "item2"])
        self.assertIsInstance(result, list)


class TestCreateJsonStructure(unittest.TestCase):

    def test_happy_path(self):
        """Test with valid domains, group name, and action_do integer."""
        domains = {"example.com", "test.com", "apple.com"}
        group_name = "Comprehensive Allowlist"
        action_do = 1

        result = create_json_structure(domains, group_name, action_do)

        # Verify group metadata
        self.assertEqual(result["group"]["group"], group_name)
        self.assertEqual(result["group"]["action"]["do"], action_do)
        self.assertEqual(result["group"]["action"]["status"], 1)

        # Verify rules structure and sorting
        self.assertEqual(len(result["rules"]), 3)
        self.assertEqual(result["rules"][0]["PK"], "apple.com")
        self.assertEqual(result["rules"][0]["action"]["do"], action_do)
        self.assertEqual(result["rules"][1]["PK"], "example.com")
        self.assertEqual(result["rules"][2]["PK"], "test.com")

    def test_single_domain(self):
        """Verify correct structure with exactly one domain."""
        result = create_json_structure({"solo.com"}, "Single", 1)
        self.assertEqual(len(result["rules"]), 1)
        self.assertEqual(result["rules"][0]["PK"], "solo.com")

    def test_empty_domains(self):
        """Test the 'zero state' behavior with an empty domains set."""
        result = create_json_structure(set(), "Empty List", 0)

        self.assertEqual(result["group"]["group"], "Empty List")
        self.assertEqual(result["group"]["action"]["do"], 0)
        self.assertEqual(result["rules"], [])

    def test_invalid_input_types(self):
        """Document the current contract handling invalid input types.
        Currently, integers passed to group_name are preserved as integers
        and not cast to strings. Action_do accepts strings natively.

        # NOTE: If input validation is added later (e.g., raising TypeError),
        # update this test to assert the new expected behavior.
        """
        # Passing an integer where a string group name is expected
        result_int_group = create_json_structure({"domain.com"}, 12345, "0")
        self.assertEqual(result_int_group["group"]["group"], 12345)

        # Passing a string where an action_do integer is expected
        self.assertEqual(result_int_group["rules"][0]["action"]["do"], "0")

    def test_json_serialization_safety(self):
        """Verify that characters potentially breaking JSON formatting
        are handled safely when dumped by the json module."""
        nasty_group_name = 'Test "quotes" and \\backslashes\\ and \n newlines'
        domains = {'weird"domain.com'}

        result = create_json_structure(domains, nasty_group_name, 0)

        # Dump to JSON string and parse it back to verify serialization works
        json_string = json.dumps(result)
        parsed_result = json.loads(json_string)

        self.assertEqual(parsed_result["group"]["group"], nasty_group_name)
        self.assertEqual(parsed_result["rules"][0]["PK"], 'weird"domain.com')


class TestProcessTrackerFiles(unittest.TestCase):

    def _run_process_tracker(
        self,
        files,
        mock_exists_val=True,
        load_json_rv=None,
        load_json_se=None,
    ):
        with (
            patch("pathlib.Path.is_file") as mock_is_file,
            patch("consolidate_adblock_lists.load_json_file") as mock_load_json,
            patch("sys.stdout", new_callable=unittest.mock.MagicMock),
        ):
            mock_is_file.return_value = mock_exists_val
            if load_json_rv is not None:
                mock_load_json.return_value = load_json_rv
            if load_json_se is not None:
                mock_load_json.side_effect = load_json_se

            return process_tracker_files(Path("/fake/dir"), files)

    def test_happy_path(self):
        data = {
            "rules": [
                {"PK": "tracker1.com", "action": {"do": 0}},
                {"PK": "tracker2.com", "action": {"do": 0}},
            ]
        }
        result = self._run_process_tracker(["file1.json"], load_json_rv=data)
        self.assertEqual(result, {"tracker1.com", "tracker2.com"})

    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self._run_process_tracker(["missing.json"], mock_exists_val=False)

    def test_missing_rules_key(self):
        with self.assertRaises(ValueError):
            self._run_process_tracker(
                ["norules.json"],
                load_json_rv={"other_key": "data"},
            )

    def test_unreadable_or_malformed_source(self):
        with self.assertRaises(ValueError):
            self._run_process_tracker(["bad.json"], load_json_rv={"rules": []})
        with self.assertRaises(ValueError):
            self._run_process_tracker(["unreadable.json"], load_json_se=[None])

    def test_multiple_files_with_duplicates(self):
        load_results = [
            {"rules": [{"PK": "tracker1.com", "action": {"do": 0}}]},
            {
                "rules": [
                    {"PK": "tracker1.com", "action": {"do": 0}},
                    {"PK": "tracker2.com", "action": {"do": 0}},
                ]
            },
        ]
        result = self._run_process_tracker(
            ["file1.json", "file2.json"],
            load_json_se=load_results,
        )
        self.assertEqual(result, {"tracker1.com", "tracker2.com"})


class TestExtractAllowlistFromFile(unittest.TestCase):

    def test_file_not_found(self):
        filepath = MagicMock()
        filepath.is_file.return_value = False
        with self.assertRaises(FileNotFoundError):
            extract_allowlist_from_file(filepath, "desc")

    @patch("consolidate_adblock_lists.load_json_file")
    def test_missing_or_invalid_data(self, mock_load):
        filepath = MagicMock()
        filepath.is_file.return_value = True
        filepath.name = "test.json"

        with patch("sys.stdout", new_callable=unittest.mock.MagicMock):
            mock_load.return_value = None
            with self.assertRaises(ValueError):
                extract_allowlist_from_file(filepath, "desc")

            mock_load.return_value = {"other": "value"}
            with self.assertRaises(ValueError):
                extract_allowlist_from_file(filepath, "desc")

    @patch("consolidate_adblock_lists.load_json_file")
    def test_extract_allow_rules_only(self, mock_load):
        filepath = MagicMock()
        filepath.exists.return_value = True
        filepath.name = "test.json"
        filepath.is_file.return_value = True

        mock_load.return_value = {
            "rules": [
                {"PK": "valid1.com", "action": {"do": 1}},
                {"PK": "invalid_do_0.com", "action": {"do": 0}},
                {"PK": "valid2.com", "action": {"do": 1}},
            ]
        }

        with patch("sys.stdout", new_callable=unittest.mock.MagicMock):
            result = extract_allowlist_from_file(filepath, "desc")

        self.assertEqual(result, {"valid1.com", "valid2.com"})

    @patch("consolidate_adblock_lists.load_json_file")
    def test_invalid_rule_is_rejected(self, mock_load):
        filepath = MagicMock()
        filepath.is_file.return_value = True
        mock_load.return_value = {
            "rules": [
                {"PK": "valid.com", "action": {"do": 1}},
                {"PK": "invalid.com"},
            ]
        }
        with patch("sys.stdout"), self.assertRaises(ValueError):
            extract_allowlist_from_file(filepath, "desc")


class TestProcessAllowlistFiles(unittest.TestCase):

    @patch("consolidate_adblock_lists.extract_allowlist_from_file")
    def test_happy_path(self, mock_extract):
        mock_extract.side_effect = [
            {"bypass1.com", "bypass2.com"},
            {"tld1.com", "tld2.com"},
        ]

        base_dir = Path("/fake/dir")

        with patch("sys.stdout"):
            result = process_allowlist_files(base_dir)

        self.assertEqual(result, {"bypass1.com", "bypass2.com", "tld1.com", "tld2.com"})

        self.assertEqual(mock_extract.call_count, 2)
        mock_extract.assert_any_call(
            base_dir / "CD-Control-D-Bypass.json", "bypass domains"
        )
        mock_extract.assert_any_call(
            base_dir / "CD-Most-Abused-TLDs.json", "legitimate TLD domains"
        )

    @patch("consolidate_adblock_lists.extract_allowlist_from_file")
    def test_overlapping_domains(self, mock_extract):
        mock_extract.side_effect = [
            {"shared.com", "bypass.com"},
            {"shared.com", "tld.com"},
        ]

        base_dir = Path("/fake/dir")
        with patch("sys.stdout"):
            result = process_allowlist_files(base_dir)

        self.assertEqual(result, {"shared.com", "bypass.com", "tld.com"})

    @patch("consolidate_adblock_lists.extract_allowlist_from_file")
    def test_empty_results(self, mock_extract):
        mock_extract.side_effect = [set(), set()]

        base_dir = Path("/fake/dir")
        with patch("sys.stdout"):
            result = process_allowlist_files(base_dir)

        self.assertEqual(result, set())


class TestWriteTextFiles(unittest.TestCase):
    def setUp(self):
        self.output_dir = Path("/fake/output")

    @patch("builtins.open", new_callable=mock_open)
    @patch("sys.stdout")
    def test_happy_path(self, mock_stdout, mock_file):
        denylist_domains = {"tracker2.com", "tracker1.com"}
        allowlist_domains = {"allow2.com", "allow1.com"}

        write_text_files(self.output_dir, denylist_domains, allowlist_domains)

        handle = mock_file()
        expected_calls = [
            unittest.mock.call("tracker1.com\ntracker2.com\n"),
            unittest.mock.call("@@allow1.com\n@@allow2.com\n"),
        ]
        handle.write.assert_has_calls(expected_calls)
        self.assertEqual(handle.write.call_count, 2)

    @patch("builtins.open", new_callable=mock_open)
    @patch("sys.stdout")
    def test_empty_domains(self, mock_stdout, mock_file):
        write_text_files(self.output_dir, set(), set())

        # Files should still be opened
        self.assertEqual(mock_file.call_count, 2)

        # But write should not be called when domain sets are empty
        handle = mock_file()
        handle.write.assert_not_called()


class TestRunConsolidation(unittest.TestCase):
    tracker_files = (
        "CD-Microsoft-Tracker.json",
        "CD-No-Safesearch-Support.json",
        "CD-OPPO_Realme-Tracker.json",
        "CD-Roku-Tracker.json",
        "CD-Samsung-Tracker.json",
        "CD-Tiktok-Tracker---aggressive.json",
        "CD-Vivo-Tracker.json",
        "CD-Xiaomi-Tracker.json",
        "CD-Amazon-Tracker.json",
        "CD-Apple-Tracker.json",
        "CD-Badware-Hoster.json",
        "CD-LG-webOS-Tracker.json",
        "CD-Huawei-Tracker.json",
    )
    outputs = (
        "Consolidated-Denylist.json",
        "Consolidated-Allowlist.json",
        "Consolidated-Denylist.txt",
        "Consolidated-Allowlist.txt",
    )

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.input_dir = Path(self.temp.name) / "input"
        self.output_dir = Path(self.temp.name) / "output"
        self.input_dir.mkdir()
        self.output_dir.mkdir()
        for index, name in enumerate(self.tracker_files):
            (self.input_dir / name).write_text(
                json.dumps(
                    {"rules": [{"PK": f"tracker{index}.example", "action": {"do": 0}}]}
                )
            )
        for name in ("CD-Control-D-Bypass.json", "CD-Most-Abused-TLDs.json"):
            (self.input_dir / name).write_text(
                json.dumps({"rules": [{"PK": "allowed.example", "action": {"do": 1}}]})
            )

    def seed_outputs(self):
        for name in self.outputs:
            (self.output_dir / name).write_text("existing content\n")

    def assert_outputs_unchanged(self):
        for name in self.outputs:
            self.assertEqual((self.output_dir / name).read_text(), "existing content\n")
        self.assertEqual({p.name for p in self.output_dir.iterdir()}, set(self.outputs))

    def test_run_consolidation(self):
        self.seed_outputs()
        with patch("sys.stdout"):
            run_consolidation(self.input_dir, self.output_dir)
        denylist = (self.output_dir / "Consolidated-Denylist.txt").read_text()
        self.assertEqual(len(denylist.splitlines()), len(self.tracker_files))
        self.assertIn("tracker0.example\n", denylist)
        self.assertEqual(
            (self.output_dir / "Consolidated-Allowlist.txt").read_text(),
            "@@allowed.example\n",
        )
        self.assertEqual(
            len(
                json.loads(
                    (self.output_dir / "Consolidated-Denylist.json").read_text()
                )["rules"]
            ),
            len(self.tracker_files),
        )

    def test_missing_or_invalid_tracker_preserves_existing_outputs(self):
        self.seed_outputs()
        source = self.input_dir / self.tracker_files[-1]
        for change in (
            source.unlink,
            lambda: source.write_text("{invalid"),
            lambda: source.write_text('{"rules": []}'),
        ):
            change()
            with (
                patch("sys.stdout"),
                self.assertRaises((FileNotFoundError, ValueError)),
            ):
                run_consolidation(self.input_dir, self.output_dir)
            self.assert_outputs_unchanged()

    def test_invalid_allowlist_preserves_existing_outputs(self):
        self.seed_outputs()
        (self.input_dir / "CD-Control-D-Bypass.json").write_text("{invalid")
        with patch("sys.stdout"), self.assertRaises(ValueError):
            run_consolidation(self.input_dir, self.output_dir)
        self.assert_outputs_unchanged()

    def test_output_write_failure_preserves_existing_outputs(self):
        self.seed_outputs()
        with (
            patch("sys.stdout"),
            patch(
                "consolidate_adblock_lists.write_text_files",
                side_effect=OSError("disk full"),
            ),
            self.assertRaises(OSError),
        ):
            run_consolidation(self.input_dir, self.output_dir)
        self.assert_outputs_unchanged()

    def test_symlinked_output_is_rejected_before_replacement(self):
        self.seed_outputs()
        target = Path(self.temp.name) / "linked-denylist.txt"
        target.write_text("linked content\n")
        link = self.output_dir / "Consolidated-Denylist.txt"
        link.unlink()
        link.symlink_to(target)
        with (
            patch("sys.stdout"),
            self.assertRaisesRegex(ValueError, "symlinked output"),
        ):
            run_consolidation(self.input_dir, self.output_dir)
        self.assertTrue(link.is_symlink())
        self.assertEqual(target.read_text(), "linked content\n")
        for name in self.outputs:
            if name != link.name:
                self.assertEqual(
                    (self.output_dir / name).read_text(), "existing content\n"
                )
        self.assertEqual({p.name for p in self.output_dir.iterdir()}, set(self.outputs))

    def test_non_file_output_is_rejected_before_replacement(self):
        self.seed_outputs()
        destination = self.output_dir / "Consolidated-Allowlist.txt"
        destination.unlink()
        destination.mkdir()
        with patch("sys.stdout"), self.assertRaisesRegex(ValueError, "regular file"):
            run_consolidation(self.input_dir, self.output_dir)
        self.assertTrue(destination.is_dir())
        for name in self.outputs:
            if name != destination.name:
                self.assertEqual(
                    (self.output_dir / name).read_text(), "existing content\n"
                )
        self.assertEqual({p.name for p in self.output_dir.iterdir()}, set(self.outputs))


if __name__ == "__main__":
    unittest.main()
