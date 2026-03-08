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


    def test_check_auth_missing_split(self):
        """
        Test that an Authorization header without a space triggers the except block
        and results in a 401 response (ValueError from unpacking).
        """
        # Setup mock authentication globals
        infuse_media_server.AUTH_USER = 'test_user'
        infuse_media_server.AUTH_PASS = 'test_pass'
        infuse_media_server.EXPECTED_AUTH_TOKEN = 'mock_token'

        # Setup request context
        self.handler.client_address = ('127.0.0.1', 12345)
        self.handler.headers = {'Authorization': 'BasicInvalidFormatNoSpace'}

        # Method under test
        result = self.handler.check_auth()

        # Assertions
        self.assertFalse(result)
        self.handler.send_response.assert_called_with(401)
        self.handler.send_header.assert_called_with('WWW-Authenticate', 'Basic realm="Infuse Media Server"')

    def test_check_auth_handles_comparison_exception(self):
        """
        Test that an exception during token comparison is caught and results
        in a 401 response.
        """
        # Setup mock authentication globals
        infuse_media_server.AUTH_USER = 'test_user'
        infuse_media_server.AUTH_PASS = 'test_pass'
        infuse_media_server.EXPECTED_AUTH_TOKEN = 'mock_token'

        # Setup request context
        self.handler.client_address = ('127.0.0.1', 12345)

        # Basic followed by a space, then something that would cause compare_digest to raise TypeError
        # Since compare_digest requires bytes or strings of the same length, passing an integer
        # or different type inside the original code wouldn't happen as split returns string.
        # But wait, what if auth_data is a different length from EXPECTED_AUTH_TOKEN?
        # compare_digest does not raise an exception for different lengths, it just returns False.
        # However, we can mock `secrets.compare_digest` to raise an Exception.
        # Actually, let's just use the missing split case as it natively raises ValueError.
        # Another case that natively raises an exception: auth_header.split() on a None value
        # is already caught by `if not auth_header`.

        # Let's mock secrets.compare_digest to raise an Exception to ensure the except block
        # catches it and correctly handles it.
        import secrets
        from unittest.mock import patch

        self.handler.headers = {'Authorization': 'Basic SomeToken'}

        with patch('secrets.compare_digest', side_effect=Exception('Mocked exception')):
            result = self.handler.check_auth()

        # Assertions
        self.assertFalse(result)
        self.handler.send_response.assert_called_with(401)
        self.handler.send_header.assert_called_with('WWW-Authenticate', 'Basic realm="Infuse Media Server"')

if __name__ == '__main__':
    unittest.main()
