import unittest
from unittest.mock import MagicMock
import sys
import os
import html

# Import the module using importlib
import importlib.util
module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../media-streaming/archive/scripts/infuse-media-server.py'))
spec = importlib.util.spec_from_file_location("infuse_media_server", module_path)
infuse_media_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(infuse_media_server)

class TestMediaServer(unittest.TestCase):
    def setUp(self):
        # Create a mock for the handler to test instance methods properly
        # We mock the necessary attributes that __init__ might need if we were to call it,
        # but here we just need an instance to call the methods.
        self.handler = MagicMock(spec=infuse_media_server.MediaServerHandler)
        # We want to test the actual implementation of the methods, not the mocks of them
        self.handler.validate_path = infuse_media_server.MediaServerHandler.validate_path.__get__(self.handler)
        self.handler.generate_directory_listing = infuse_media_server.MediaServerHandler.generate_directory_listing.__get__(self.handler)

    def test_valid_paths(self):
        valid_paths = [
            "folder/file.mp4",
            "folder/subfolder/",
            "file with spaces.mkv",
            "movie-2023.mp4",
            "folder/..filename..mp4", # legitimate filenames containing dots
            "",
            "unicode-movie-🎬.mp4",
            "日本語.mkv",
            "very/long/" + "a"*100 + ".mp4"
        ]
        for p in valid_paths:
            with self.subTest(path=p):
                try:
                    result = self.handler.validate_path(p)
                    self.assertEqual(result, p.lstrip('/'))
                except ValueError as e:
                    self.fail(f"Valid path '{p}' rejected: {e}")

    def test_traversal_attempts(self):
        invalid_paths = [
            "../secret",
            "folder/../secret",
            "folder/../../etc/passwd",
            "..",
            "/../secret",
            "a/b/../../../etc/passwd",
            "./../a",
            "..\\etc\\passwd",
            "folder\\..\\secret"
        ]
        for p in invalid_paths:
            with self.subTest(path=p):
                with self.assertRaises(ValueError, msg=f"Traversal path '{p}' should fail"):
                    self.handler.validate_path(p)

    def test_argument_injection(self):
        invalid_paths = [
            "-flag",
            "--option",
            "-v",
            "/-flag"
        ]
        for p in invalid_paths:
            with self.subTest(path=p):
                with self.assertRaises(ValueError, msg=f"Argument injection path '{p}' should fail"):
                    self.handler.validate_path(p)

    def test_null_byte(self):
        invalid_paths = [
            "file.mp4\0",
            "folder\0/file"
        ]
        for p in invalid_paths:
            with self.subTest(path=p):
                with self.assertRaises(ValueError, msg=f"Null byte path '{p}' should fail"):
                    self.handler.validate_path(p)

    def test_slashes_and_backslashes(self):
        # Test backslashes are handled correctly as path separators
        test_cases = [
            ("a\\b", True),   # Backslash as part of filename (not ideal but currently allowed)
            ("..\\etc", False), # Traversal with backslash
            ("a/..\\b", False), # Mixed separators
        ]

        for p, should_pass in test_cases:
             with self.subTest(path=p):
                 if should_pass:
                     self.handler.validate_path(p)
                 else:
                     with self.assertRaises(ValueError):
                         self.handler.validate_path(p)

    def test_generate_directory_listing_escaping(self):
        # Test XSS prevention
        files = ["<script>alert(1)</script>.mp4", "normal.mkv"]
        current_path = "<b>danger</b>"

        html_out = self.handler.generate_directory_listing(files, current_path)

        self.assertNotIn("<b>danger</b>", html_out)
        self.assertIn(html.escape("<b>danger</b>"), html_out)

        self.assertNotIn("<script>alert(1)</script>", html_out)
        self.assertIn(html.escape("<script>alert(1)</script>"), html_out)

    def test_generate_directory_listing_parent_link(self):
        # Root path shouldn't have parent link
        html_root = self.handler.generate_directory_listing(["file.txt"], "")
        self.assertNotIn("Parent Directory", html_root)

        # Subdirectory should have parent link
        html_sub = self.handler.generate_directory_listing(["file.txt"], "movies/action")
        self.assertIn("Parent Directory", html_sub)
        self.assertIn('href="/movies"', html_sub)

if __name__ == '__main__':
    unittest.main()
