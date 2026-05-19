import sys
import os
import unittest
from unittest.mock import patch

# Ensure the project root is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Also add the scripts dir so we can import repository_automation_common directly
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.github', 'scripts'))

try:
    from repository_automation_common import task_dir, OUTPUT_ROOT
    _IMPORT_ERROR = None
except ImportError as exc:  # e.g. PyYAML not installed in the test environment
    task_dir = None
    OUTPUT_ROOT = None
    _IMPORT_ERROR = exc

@unittest.skipIf(_IMPORT_ERROR is not None, f"repository_automation_common unavailable: {_IMPORT_ERROR}")
class TestTaskDir(unittest.TestCase):
    @patch('pathlib.Path.mkdir')
    def test_task_dir_basic(self, mock_mkdir):
        """Test basic directory creation"""
        task_name = "test_task"
        result = task_dir(task_name)

        expected_path = OUTPUT_ROOT / task_name
        self.assertEqual(result, expected_path)
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch('pathlib.Path.mkdir')
    def test_task_dir_nested(self, mock_mkdir):
        """Test creating a nested task directory"""
        task_name = "nested/test_task"
        result = task_dir(task_name)

        expected_path = OUTPUT_ROOT / task_name
        self.assertEqual(result, expected_path)
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch('pathlib.Path.mkdir')
    def test_task_dir_exception(self, mock_mkdir):
        """Test that exceptions from mkdir are propagated"""
        mock_mkdir.side_effect = PermissionError("Permission denied")
        with self.assertRaises(PermissionError):
            task_dir("test_task")

if __name__ == '__main__':
    unittest.main()
