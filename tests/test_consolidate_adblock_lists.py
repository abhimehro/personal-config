import json
import sys
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
            patch("pathlib.Path.exists") as mock_exists,
            patch("consolidate_adblock_lists.load_json_file") as mock_load_json,
            patch("sys.stdout", new_callable=unittest.mock.MagicMock),
        ):
            mock_exists.return_value = mock_exists_val
            if load_json_rv is not None:
                mock_load_json.return_value = load_json_rv
            if load_json_se is not None:
                mock_load_json.side_effect = load_json_se

            return process_tracker_files(Path("/fake/dir"), files)

    def test_happy_path(self):
        data = {"rules": [{"PK": "tracker1.com"}, {"PK": "tracker2.com"}]}
        result = self._run_process_tracker(["file1.json"], load_json_rv=data)
        self.assertEqual(result, {"tracker1.com", "tracker2.com"})

    def test_file_not_found(self):
        result = self._run_process_tracker(["missing.json"], mock_exists_val=False)
        self.assertEqual(result, set())

    def test_missing_rules_key(self):
        result = self._run_process_tracker(
            ["norules.json"],
            load_json_rv={"other_key": "data"},
        )
        self.assertEqual(result, set())

    def test_multiple_files_with_duplicates(self):
        load_results = [
            {"rules": [{"PK": "tracker1.com"}]},
            {"rules": [{"PK": "tracker1.com"}, {"PK": "tracker2.com"}]},
        ]
        result = self._run_process_tracker(
            ["file1.json", "file2.json"],
            load_json_se=load_results,
        )
        self.assertEqual(result, {"tracker1.com", "tracker2.com"})


class TestExtractAllowlistFromFile(unittest.TestCase):

    def test_file_not_found(self):
        filepath = MagicMock()
        filepath.exists.return_value = False
        result = extract_allowlist_from_file(filepath, "desc")
        self.assertEqual(result, set())

    @patch("consolidate_adblock_lists.load_json_file")
    def test_missing_or_invalid_data(self, mock_load):
        filepath = MagicMock()
        filepath.exists.return_value = True
        filepath.name = "test.json"

        with patch("sys.stdout", new_callable=unittest.mock.MagicMock):
            mock_load.return_value = None
            result = extract_allowlist_from_file(filepath, "desc")
            self.assertEqual(result, set())

            mock_load.return_value = {"other": "value"}
            result = extract_allowlist_from_file(filepath, "desc")
            self.assertEqual(result, set())

    @patch("consolidate_adblock_lists.load_json_file")
    def test_extract_valid_and_invalid_rules(self, mock_load):
        filepath = MagicMock()
        filepath.exists.return_value = True
        filepath.name = "test.json"

        mock_load.return_value = {
            "rules": [
                {"PK": "valid1.com", "action": {"do": 1}},
                {"action": {"do": 1}},
                {"PK": "invalid_no_action.com"},
                {"PK": "invalid_action_not_dict.com", "action": "allow"},
                {"PK": "invalid_no_do.com", "action": {"other": 1}},
                {"PK": "invalid_do_0.com", "action": {"do": 0}},
                {"PK": "valid2.com", "action": {"do": 1}},
            ]
        }

        with patch("sys.stdout", new_callable=unittest.mock.MagicMock):
            result = extract_allowlist_from_file(filepath, "desc")

        self.assertEqual(result, {"valid1.com", "valid2.com"})


class TestProcessAllowlistFiles(unittest.TestCase):

    @patch("consolidate_adblock_lists.extract_allowlist_from_file")
    def test_happy_path(self, mock_extract):
        mock_extract.side_effect = [
            {"bypass1.com", "bypass2.com"},
            {"tld1.com", "tld2.com"}
        ]

        base_dir = Path("/fake/dir")

        with patch("sys.stdout"):
            result = process_allowlist_files(base_dir)

        self.assertEqual(result, {"bypass1.com", "bypass2.com", "tld1.com", "tld2.com"})

        self.assertEqual(mock_extract.call_count, 2)
        mock_extract.assert_any_call(base_dir / "CD-Control-D-Bypass.json", "bypass domains")
        mock_extract.assert_any_call(base_dir / "CD-Most-Abused-TLDs.json", "legitimate TLD domains")

    @patch("consolidate_adblock_lists.extract_allowlist_from_file")
    def test_overlapping_domains(self, mock_extract):
        mock_extract.side_effect = [
            {"shared.com", "bypass.com"},
            {"shared.com", "tld.com"}
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


class TestRunConsolidation(unittest.TestCase):
    @patch("consolidate_adblock_lists.print_summary")
    @patch("consolidate_adblock_lists.write_text_files")
    @patch("consolidate_adblock_lists.write_json_files")
    @patch("consolidate_adblock_lists.process_allowlist_files")
    @patch("consolidate_adblock_lists.process_tracker_files")
    def test_run_consolidation(
        self,
        mock_process_tracker,
        mock_process_allowlist,
        mock_write_json,
        mock_write_text,
        mock_print_summary,
    ):
        input_dir = Path("/fake/input")
        output_dir = Path("/fake/output")

        mock_process_tracker.return_value = {"tracker.com"}
        mock_process_allowlist.return_value = {"allow.com"}

        with patch("sys.stdout"):
            run_consolidation(input_dir, output_dir)

        mock_process_tracker.assert_called_once_with(
            input_dir,
            [
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
            ],
        )
        mock_process_allowlist.assert_called_once_with(input_dir)
        mock_write_json.assert_called_once_with(
            output_dir, {"tracker.com"}, {"allow.com"}
        )
        mock_write_text.assert_called_once_with(
            output_dir, {"tracker.com"}, {"allow.com"}
        )
        mock_print_summary.assert_called_once_with(
            {"tracker.com"}, {"allow.com"}, output_dir
        )

if __name__ == "__main__":
    unittest.main()
