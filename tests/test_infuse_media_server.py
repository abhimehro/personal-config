"""
Tests for the infuse-media-server.py script.
This module specifically tests the authentication handlers and related methods
in isolation without needing to spin up a full HTTP server instance.
"""

import importlib.util
import os
import sys
import unittest
from unittest.mock import MagicMock

# Add the script directory to sys.path so we can import it
script_dir = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "media-streaming", "archive", "scripts"
    )
)
sys.path.insert(0, script_dir)

# Import the script module dynamically since it has hyphens in the name
spec = importlib.util.spec_from_file_location(
    "infuse_media_server", os.path.join(script_dir, "infuse-media-server.py")
)
infuse_media_server = importlib.util.module_from_spec(spec)
sys.modules["infuse_media_server"] = infuse_media_server
spec.loader.exec_module(infuse_media_server)


class TestMediaServerHandler(unittest.TestCase):
    def setUp(self):
        # Create an instance without calling __init__ to avoid setting up sockets/server
        self.handler = infuse_media_server.MediaServerHandler.__new__(
            infuse_media_server.MediaServerHandler
        )

        # Mock the underlying HTTP handler methods
        self.handler.send_response = MagicMock()
        self.handler.send_header = MagicMock()
        self.handler.end_headers = MagicMock()
        self.handler.wfile = MagicMock()

    def test_send_auth_request_returns_401_with_basic_auth_header(self):
        """
        Test that send_auth_request sends a 401 response with the correct
        WWW-Authenticate Basic header and a response body.
        """
        # Call the method under test
        self.handler.send_auth_request()

        # Verify 401 response is sent
        self.handler.send_response.assert_called_once_with(401)

        # Verify correct WWW-Authenticate header is set
        self.handler.send_header.assert_called_once_with(
            "WWW-Authenticate", 'Basic realm="Infuse Media Server"'
        )

        # Verify end_headers is called to close the header block
        self.handler.end_headers.assert_called_once()

        # Verify the body is written
        self.handler.wfile.write.assert_called_once_with(b"Authentication required")

    def test_check_auth_missing_split(self):
        """
        Test that an Authorization header without a space triggers the except block
        and results in a 401 response (ValueError from unpacking).
        """
        # Setup mock authentication globals
        infuse_media_server.AUTH_USER = "test_user"
        infuse_media_server.AUTH_PASS = "test_pass"
        infuse_media_server.EXPECTED_AUTH_TOKEN = "mock_token"

        # Setup request context
        self.handler.client_address = ("127.0.0.1", 12345)
        self.handler.headers = {"Authorization": "BasicInvalidFormatNoSpace"}

        # Method under test
        result = self.handler.check_auth()

        # Assertions
        self.assertFalse(result)
        self.handler.send_response.assert_called_with(401)
        self.handler.send_header.assert_called_with(
            "WWW-Authenticate", 'Basic realm="Infuse Media Server"'
        )

    def test_check_auth_handles_comparison_exception(self):
        """
        Test that an exception during token comparison is caught and results
        in a 401 response.
        """
        # Setup mock authentication globals
        infuse_media_server.AUTH_USER = "test_user"
        infuse_media_server.AUTH_PASS = "test_pass"
        infuse_media_server.EXPECTED_AUTH_TOKEN = "mock_token"

        # Setup request context
        self.handler.client_address = ("127.0.0.1", 12345)

        # Force an exception from the token comparison logic so we can verify
        # that check_auth catches it and responds with 401.
        from unittest.mock import patch

        self.handler.headers = {"Authorization": "Basic SomeToken"}

        # Patch the compare_digest used inside infuse_media_server so the mock
        # is scoped to this module under test.
        with patch(
            "infuse_media_server.secrets.compare_digest",
            side_effect=Exception("Mocked exception"),
        ):
            result = self.handler.check_auth()

        # Assertions
        self.assertFalse(result)
        self.handler.send_response.assert_called_with(401)
        self.handler.send_header.assert_called_with(
            "WWW-Authenticate", 'Basic realm="Infuse Media Server"'
        )

    def test_generate_directory_listing(self):
        """
        Test that generate_directory_listing produces correct HTML output,
        handles proper paths, and escapes file and directory names.
        """
        # Include files and directories with characters needing escaping like < > &
        files = [
            "video.mp4",
            "movie.MKV",
            "folder with <tag>/",
            "document & file.txt",
            "<script>alert(1)</script>.avi",
        ]

        # Test 1: Root path
        html_root = self.handler.generate_directory_listing(files, "/")

        self.assertIn("<title>Media Library - /</title>", html_root)
        self.assertIn("\U0001f4c1 Media Library: //</h1>", html_root)
        self.assertNotIn(".. (Parent Directory)", html_root)

        # File checks with escaped characters
        self.assertIn(
            '<a href="/video.mp4" class="file video">\U0001f3ac video.mp4</a>',
            html_root,
        )
        self.assertIn(
            '<a href="/folder with &lt;tag&gt;/" class="file directory">\U0001f4c1 folder with &lt;tag&gt;</a>',
            html_root,
        )
        self.assertIn(
            '<a href="/document &amp; file.txt" class="file video">\U0001f4c4 document &amp; file.txt</a>',
            html_root,
        )
        self.assertIn(
            '<a href="/&lt;script&gt;alert(1)&lt;/script&gt;.avi" class="file video">\U0001f3ac &lt;script&gt;alert(1)&lt;/script&gt;.avi</a>',
            html_root,
        )

        # Test 2: Subdirectory with escaping - matching a realistic path shape
        # The server script typically hosts from a specific media directory, so we'll use a realistic relative path
        current_path = "/Movies & TV/Action <Sci-Fi>"
        html_sub = self.handler.generate_directory_listing(files, current_path)

        self.assertIn(
            "Media Library - /Movies &amp; TV/Action &lt;Sci-Fi&gt;", html_sub
        )
        self.assertIn(".. (Parent Directory)", html_sub)

        # Check parent link (split takes off the last component)
        # Note: actually current_path does NOT get escaped before computing parent?
        # Let's check code: parent = "/".join(current_path.rstrip("/").split("/")[:-1]) -> "/Movies & TV"
        # safe_parent = html.escape(parent) -> "/Movies &amp; TV"
        self.assertIn('<a href="//Movies &amp; TV" class="file directory">', html_sub)

        # Check files in subdirectory (href should append to the escaped base_path)
        self.assertIn(
            '<a href="//Movies &amp; TV/Action &lt;Sci-Fi&gt;/video.mp4" class="file video">\U0001f3ac video.mp4</a>',
            html_sub,
        )
        self.assertIn(
            '<a href="//Movies &amp; TV/Action &lt;Sci-Fi&gt;/folder with &lt;tag&gt;/" class="file directory">\U0001f4c1 folder with &lt;tag&gt;</a>',
            html_sub,
        )


if __name__ == "__main__":
    unittest.main()
