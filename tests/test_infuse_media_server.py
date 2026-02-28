"""
Tests for the infuse-media-server.py script.
This module specifically tests the authentication handlers and related methods
in isolation without needing to spin up a full HTTP server instance.
"""
import unittest
from unittest.mock import MagicMock
import importlib.util
import os
import sys

# Add the script directory to sys.path so we can import it
script_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'media-streaming', 'archive', 'scripts'))
sys.path.insert(0, script_dir)

# Import the script module dynamically since it has hyphens in the name
spec = importlib.util.spec_from_file_location("infuse_media_server", os.path.join(script_dir, "infuse-media-server.py"))
infuse_media_server = importlib.util.module_from_spec(spec)
sys.modules["infuse_media_server"] = infuse_media_server
spec.loader.exec_module(infuse_media_server)


class TestMediaServerHandler(unittest.TestCase):
    def setUp(self):
        # Create an instance without calling __init__ to avoid setting up sockets/server
        self.handler = infuse_media_server.MediaServerHandler.__new__(infuse_media_server.MediaServerHandler)

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
        self.handler.send_header.assert_called_once_with('WWW-Authenticate', 'Basic realm="Infuse Media Server"')

        # Verify end_headers is called to close the header block
        self.handler.end_headers.assert_called_once()

        # Verify the body is written
        self.handler.wfile.write.assert_called_once_with(b'Authentication required')

if __name__ == '__main__':
    unittest.main()
