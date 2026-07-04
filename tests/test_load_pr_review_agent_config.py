import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Load the script as a module
spec = importlib.util.spec_from_file_location(
    "load_config", "scripts/_load_pr_review_agent_config.py"
)
load_config = importlib.util.module_from_spec(spec)
sys.modules["load_config"] = load_config
spec.loader.exec_module(load_config)


class TestLoadPrReviewAgentConfig(unittest.TestCase):
    def test_try_import_yaml_success(self):
        with patch.dict(sys.modules, {"yaml": MagicMock()}):
            self.assertIsNotNone(load_config._try_import_yaml())

    def test_try_import_yaml_failure(self):
        orig_import = __import__

        def mock_import(name, *args):
            if name == "yaml":
                raise ImportError("No module named 'yaml'")
            return orig_import(name, *args)

        with patch("builtins.__import__", side_effect=mock_import):
            self.assertIsNone(load_config._try_import_yaml())

    @patch("load_config._try_import_yaml")
    def test_load_mapping_success(self, mock_import):
        mock_import.return_value = MagicMock(
            safe_load=lambda x: {"repos": ["repo1"], "bot_authors": ["bot1"]}
        )
        with patch("pathlib.Path.read_text", return_value="dummy"):
            data = load_config._load_mapping(Path("dummy.yaml"))
        self.assertEqual(data, {"repos": ["repo1"], "bot_authors": ["bot1"]})

    @patch("load_config._try_import_yaml", return_value=None)
    def test_load_mapping_no_yaml(self, mock_import):
        self.assertIsNone(load_config._load_mapping(Path("dummy.yaml")))

    @patch("load_config._try_import_yaml")
    def test_load_mapping_not_dict(self, mock_import):
        mock_import.return_value = MagicMock(safe_load=lambda x: ["item1", "item2"])
        with patch("pathlib.Path.read_text", return_value="dummy"):
            self.assertIsNone(load_config._load_mapping(Path("dummy.yaml")))

    def test_emit_repos_output(self):
        from io import StringIO

        self.assertFalse(load_config._emit_repos("not a list"))
        self.assertTrue(load_config._emit_repos(["repo1", "", "  ", 123, "repo2 "]))

        with patch("sys.stdout", new=StringIO()) as fake_out:
            load_config._emit_repos(["repo1", "", "  ", 123, "repo2 "])
            self.assertEqual(fake_out.getvalue(), "repo\trepo1\nrepo\trepo2\n")

    def test_emit_bot_authors(self):
        from io import StringIO

        load_config._emit_bot_authors("not a list")

        with patch("sys.stdout", new=StringIO()) as fake_out:
            load_config._emit_bot_authors(
                ["bot1", 123, " bot2 # comment", "bot3#", " # just comment"]
            )
            self.assertEqual(fake_out.getvalue(), "bot\tbot1\nbot\tbot2\nbot\tbot3\n")

    @patch("sys.argv", ["script.py"])
    def test_main_no_args(self):
        from io import StringIO

        with patch("sys.stderr", new=StringIO()) as fake_err:
            self.assertEqual(load_config.main(), 1)
            self.assertIn("usage:", fake_err.getvalue())

    @patch("sys.argv", ["script.py", "nonexistent_file.yaml"])
    @patch("pathlib.Path.is_file", return_value=False)
    def test_main_file_not_found(self, mock_is_file):
        self.assertEqual(load_config.main(), 1)

    @patch("sys.argv", ["script.py", "dummy.yaml"])
    @patch("pathlib.Path.is_file", return_value=True)
    @patch(
        "load_config._load_mapping",
        return_value={"repos": ["r1"], "bot_authors": ["b1"]},
    )
    def test_main_success(self, mock_load, mock_is_file):
        from io import StringIO

        with patch("sys.stdout", new=StringIO()) as fake_out:
            self.assertEqual(load_config.main(), 0)
            self.assertEqual(fake_out.getvalue(), "repo\tr1\nbot\tb1\n")

    @patch("sys.argv", ["script.py", "dummy.yaml"])
    @patch("pathlib.Path.is_file", return_value=True)
    @patch("load_config._load_mapping", return_value=None)
    @patch("load_config._try_import_yaml", return_value=None)
    def test_main_yaml_import_error(self, mock_import, mock_load, mock_is_file):
        self.assertEqual(load_config.main(), 2)

    @patch("sys.argv", ["script.py", "dummy.yaml"])
    @patch("pathlib.Path.is_file", return_value=True)
    @patch("load_config._load_mapping", return_value=None)
    @patch("load_config._try_import_yaml", return_value=MagicMock())
    def test_main_invalid_data(self, mock_import, mock_load, mock_is_file):
        self.assertEqual(load_config.main(), 1)

    @patch("sys.argv", ["script.py", "dummy.yaml"])
    @patch("pathlib.Path.is_file", return_value=True)
    @patch("load_config._load_mapping", return_value={"repos": "not_a_list"})
    def test_main_invalid_repos(self, mock_load, mock_is_file):
        self.assertEqual(load_config.main(), 1)


if __name__ == "__main__":
    unittest.main()
