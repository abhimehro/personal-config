import os
import sys
import unittest
from unittest.mock import patch

# Ensure the module can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from adguard.scripts.create_consolidated_lists import process_allowlist_files


class TestProcessAllowlistMocked(unittest.TestCase):

    @patch("adguard.scripts.create_consolidated_lists.extract_domains_from_file")
    @patch("builtins.print")
    def test_process_allowlist_files_mocked(self, mock_print, mock_extract):
        # Create a mock base_dir (Path object)
        mock_base_dir = unittest.mock.MagicMock()

        # Create mock file objects
        mock_bypass_file = unittest.mock.MagicMock()
        mock_tlds_file = unittest.mock.MagicMock()

        # Configure base_dir / filename behavior
        def base_dir_truediv(filename):
            if filename == "CD-Control-D-Bypass.json":
                return mock_bypass_file
            elif filename == "CD-Most-Abused-TLDs.json":
                return mock_tlds_file
            return unittest.mock.MagicMock()

        mock_base_dir.__truediv__.side_effect = base_dir_truediv

        # Configure file existence
        mock_bypass_file.exists.return_value = True
        mock_tlds_file.exists.return_value = True

        # Configure extract_domains_from_file behavior
        def extract_side_effect(filepath, action_filter=None):
            if filepath == mock_bypass_file:
                return ["bypass1.com", "bypass2.com"]
            elif filepath == mock_tlds_file:
                return ["tld1.org", "tld2.net"]
            return []

        mock_extract.side_effect = extract_side_effect

        # Execute
        result = process_allowlist_files(mock_base_dir)

        # Verify
        expected_domains = {"bypass1.com", "bypass2.com", "tld1.org", "tld2.net"}
        self.assertEqual(result, expected_domains)

        # Verify extract_domains_from_file was called with correct arguments
        mock_extract.assert_any_call(mock_bypass_file, action_filter=1)
        mock_extract.assert_any_call(mock_tlds_file, action_filter=1)
        self.assertEqual(mock_extract.call_count, 2)

    @patch("adguard.scripts.create_consolidated_lists.extract_domains_from_file")
    @patch("builtins.print")
    def test_missing_bypass_file(self, mock_print, mock_extract):
        mock_base_dir = unittest.mock.MagicMock()
        mock_bypass_file = unittest.mock.MagicMock()
        mock_tlds_file = unittest.mock.MagicMock()

        def base_dir_truediv(filename):
            if filename == "CD-Control-D-Bypass.json":
                return mock_bypass_file
            elif filename == "CD-Most-Abused-TLDs.json":
                return mock_tlds_file
            return unittest.mock.MagicMock()

        mock_base_dir.__truediv__.side_effect = base_dir_truediv

        mock_bypass_file.exists.return_value = False
        mock_tlds_file.exists.return_value = True

        def extract_side_effect(filepath, action_filter=None):
            if filepath == mock_tlds_file:
                return ["tld1.org"]
            return []

        mock_extract.side_effect = extract_side_effect

        result = process_allowlist_files(mock_base_dir)
        self.assertEqual(result, {"tld1.org"})
        mock_extract.assert_called_once_with(mock_tlds_file, action_filter=1)

    @patch("adguard.scripts.create_consolidated_lists.extract_domains_from_file")
    @patch("builtins.print")
    def test_missing_tlds_file(self, mock_print, mock_extract):
        mock_base_dir = unittest.mock.MagicMock()
        mock_bypass_file = unittest.mock.MagicMock()
        mock_tlds_file = unittest.mock.MagicMock()

        def base_dir_truediv(filename):
            if filename == "CD-Control-D-Bypass.json":
                return mock_bypass_file
            elif filename == "CD-Most-Abused-TLDs.json":
                return mock_tlds_file
            return unittest.mock.MagicMock()

        mock_base_dir.__truediv__.side_effect = base_dir_truediv

        mock_bypass_file.exists.return_value = True
        mock_tlds_file.exists.return_value = False

        def extract_side_effect(filepath, action_filter=None):
            if filepath == mock_bypass_file:
                return ["bypass1.com"]
            return []

        mock_extract.side_effect = extract_side_effect

        result = process_allowlist_files(mock_base_dir)
        self.assertEqual(result, {"bypass1.com"})
        mock_extract.assert_called_once_with(mock_bypass_file, action_filter=1)

    @patch("adguard.scripts.create_consolidated_lists.extract_domains_from_file")
    @patch("builtins.print")
    def test_both_files_missing(self, mock_print, mock_extract):
        mock_base_dir = unittest.mock.MagicMock()
        mock_bypass_file = unittest.mock.MagicMock()
        mock_tlds_file = unittest.mock.MagicMock()

        def base_dir_truediv(filename):
            if filename == "CD-Control-D-Bypass.json":
                return mock_bypass_file
            elif filename == "CD-Most-Abused-TLDs.json":
                return mock_tlds_file
            return unittest.mock.MagicMock()

        mock_base_dir.__truediv__.side_effect = base_dir_truediv

        mock_bypass_file.exists.return_value = False
        mock_tlds_file.exists.return_value = False

        result = process_allowlist_files(mock_base_dir)
        self.assertEqual(result, set())
        mock_extract.assert_not_called()


if __name__ == "__main__":
    unittest.main()
