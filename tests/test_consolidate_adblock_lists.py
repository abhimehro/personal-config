import unittest
from unittest.mock import patch, mock_open, call
import sys
import tempfile
from pathlib import Path

# Add the scripts directory to sys.path so we can import the script
scripts_dir = Path(__file__).parent.parent / "adguard" / "scripts"
sys.path.insert(0, str(scripts_dir))

import consolidate_adblock_lists

class TestConsolidateAdblockListsUnit(unittest.TestCase):
    def setUp(self):
        self.output_dir = Path("/mock/output/dir")

    @patch("builtins.open", new_callable=mock_open)
    @patch("builtins.print") # Suppress print statements during tests
    def test_write_text_files_basic(self, mock_print, mock_file):
        """Test basic functionality with simple domains."""
        denylist = {"bad1.com", "bad2.com"}
        allowlist = {"good1.com", "good2.com"}

        expected_deny_path = self.output_dir / "Consolidated-Denylist.txt"
        expected_allow_path = self.output_dir / "Consolidated-Allowlist.txt"

        result_deny, result_allow = consolidate_adblock_lists.write_text_files(
            self.output_dir, denylist, allowlist
        )

        # Verify return values
        self.assertEqual(result_deny, expected_deny_path)
        self.assertEqual(result_allow, expected_allow_path)

        # Verify files were opened correctly
        mock_file.assert_any_call(expected_deny_path, 'w', encoding='utf-8')
        mock_file.assert_any_call(expected_allow_path, 'w', encoding='utf-8')

        # Verify content written (sorted order)
        # TODO: Update assertions when migrating to full AdGuard syntax (||domain^)
        handle = mock_file()
        expected_calls = [
            call("bad1.com\n"),
            call("bad2.com\n"),
            call("@@good1.com\n"),
            call("@@good2.com\n")
        ]
        handle.write.assert_has_calls(expected_calls, any_order=True)

    @patch("builtins.open", new_callable=mock_open)
    @patch("builtins.print")
    def test_write_text_files_edge_cases(self, mock_print, mock_file):
        """Test various edge cases using parameterized subtests."""
        test_cases = [
            ("empty_both", set(), set(), [], []),
            ("empty_deny", set(), {"good.com"}, [], ["@@good.com\n"]),
            ("empty_allow", {"bad.com"}, set(), ["bad.com\n"], []),
            ("unicode_idn", {"xn--bcher-kva.example"}, {"münchen.example"}, ["xn--bcher-kva.example\n"], ["@@münchen.example\n"])
        ]

        for name, deny, allow, expected_deny_writes, expected_allow_writes in test_cases:
            with self.subTest(case=name):
                # Reset the mock for each subtest
                mock_file.reset_mock()

                consolidate_adblock_lists.write_text_files(self.output_dir, deny, allow)

                handle = mock_file()

                # Combine expected calls
                # TODO: Update assertions when migrating to full AdGuard syntax (||domain^)
                expected_calls = [call(w) for w in expected_deny_writes] + [call(w) for w in expected_allow_writes]

                if expected_calls:
                    handle.write.assert_has_calls(expected_calls, any_order=True)
                else:
                    handle.write.assert_not_called()

    @patch("builtins.open", new_callable=mock_open)
    @patch("builtins.print")
    def test_write_text_files_duplicates(self, mock_print, mock_file):
        """Test duplicates by passing lists instead of sets (though the script uses sets, it accepts any iterable)."""
        denylist = ["bad.com", "bad.com", "worse.com"]
        allowlist = ["good.com", "good.com", "best.com"]

        consolidate_adblock_lists.write_text_files(
            self.output_dir, denylist, allowlist
        )

        handle = mock_file()

        # Verify that sorted() doesn't deduplicate on its own
        # TODO: Update assertions when migrating to full AdGuard syntax (||domain^)
        expected_calls = [
            call("bad.com\n"),
            call("bad.com\n"),
            call("worse.com\n"),
            call("@@best.com\n"),
            call("@@good.com\n"),
            call("@@good.com\n")
        ]

        # check exact calls (order matters because sorted())
        self.assertEqual(handle.write.call_args_list, expected_calls)


class TestConsolidateAdblockListsIntegration(unittest.TestCase):
    @patch("builtins.print") # Suppress print statements during tests
    def test_write_text_files_disk_write(self, mock_print):
        """Test actual end-to-end file writing to disk."""
        denylist = {"malicious.com", "tracker.com"}
        allowlist = {"safe.com", "trusted.com"}

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result_deny, result_allow = consolidate_adblock_lists.write_text_files(
                output_dir, denylist, allowlist
            )

            # Verify paths
            self.assertTrue(result_deny.exists())
            self.assertTrue(result_allow.exists())

            # Verify file contents
            # TODO: Update assertions when migrating to full AdGuard syntax (||domain^)
            with open(result_deny, 'r', encoding='utf-8') as f:
                deny_content = f.read()
                self.assertEqual(deny_content, "malicious.com\ntracker.com\n")

            with open(result_allow, 'r', encoding='utf-8') as f:
                allow_content = f.read()
                self.assertEqual(allow_content, "@@safe.com\n@@trusted.com\n")

    @patch("builtins.print")
    def test_write_text_files_large_input(self, mock_print):
        """Test with a large number of domains to ensure no truncation."""
        denylist = {f"bad{i}.com" for i in range(1000)}
        allowlist = {f"good{i}.com" for i in range(1000)}

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result_deny, result_allow = consolidate_adblock_lists.write_text_files(
                output_dir, denylist, allowlist
            )

            with open(result_deny, 'r', encoding='utf-8') as f:
                deny_lines = f.readlines()
                self.assertEqual(len(deny_lines), 1000)

            with open(result_allow, 'r', encoding='utf-8') as f:
                allow_lines = f.readlines()
                self.assertEqual(len(allow_lines), 1000)

    @patch("builtins.print")
    def test_write_text_files_invalid_path(self, mock_print):
        """Test error handling for invalid or missing output paths."""
        denylist = {"bad.com"}
        allowlist = {"good.com"}

        # Test writing to a non-existent directory without parents
        # This will raise FileNotFoundError because open() requires the directory to exist
        invalid_dir = Path("/does/not/exist/ever")

        with self.assertRaises(FileNotFoundError):
            consolidate_adblock_lists.write_text_files(
                invalid_dir, denylist, allowlist
            )

if __name__ == "__main__":
    unittest.main()
