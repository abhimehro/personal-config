import unittest
from unittest.mock import patch, MagicMock
from scratch_triage import run_cmd

class TestRunCmd(unittest.TestCase):
    @patch("subprocess.run")
    def test_run_cmd_success(self, mock_run):
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "output"
        mock_res.stderr = ""
        mock_run.return_value = mock_res

        success, stdout, stderr = run_cmd(["echo", "hello"])

        self.assertTrue(success)
        self.assertEqual(stdout, "output")
        self.assertEqual(stderr, "")
        mock_run.assert_called_once_with(["echo", "hello"], capture_output=True, text=True)

    @patch("subprocess.run")
    def test_run_cmd_failure(self, mock_run):
        mock_res = MagicMock()
        mock_res.returncode = 1
        mock_res.stdout = ""
        mock_res.stderr = "error"
        mock_run.return_value = mock_res

        success, stdout, stderr = run_cmd(["false"])

        self.assertFalse(success)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "error")
        mock_run.assert_called_once_with(["false"], capture_output=True, text=True)

if __name__ == "__main__":
    unittest.main()
