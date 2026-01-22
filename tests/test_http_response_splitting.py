import unittest
import sys
import os
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock

# Add the script directory to path to import the module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../media-streaming/scripts')))

# Import the module
import importlib.util
spec = importlib.util.spec_from_file_location("alldebrid_server",
    os.path.abspath(os.path.join(os.path.dirname(__file__), '../media-streaming/scripts/alldebrid-server.py')))
alldebrid_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(alldebrid_server)

class TestHTTPResponseSplitting(unittest.TestCase):
    """Test CORS header handling to prevent HTTP Response Splitting attacks."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the request, client_address, and server
        self.mock_request = Mock()
        self.mock_request.makefile = Mock(side_effect=[BytesIO(b''), BytesIO(b'')])
        self.client_address = ('127.0.0.1', 8080)
        self.mock_server = Mock()
        
        # Store original environment variables
        self.original_auth_user = os.environ.get('ALD_AUTH_USER')
        self.original_auth_pass = os.environ.get('ALD_AUTH_PASS')
        self.original_allowed_origins = os.environ.get('ALD_ALLOWED_ORIGINS')
        
        # Store original module variables
        self.original_module_auth_user = alldebrid_server.AUTH_USER
        self.original_module_auth_pass = alldebrid_server.AUTH_PASS
        
    def tearDown(self):
        """Clean up after tests."""
        # Restore original environment variables
        if self.original_auth_user is None:
            os.environ.pop('ALD_AUTH_USER', None)
        else:
            os.environ['ALD_AUTH_USER'] = self.original_auth_user
            
        if self.original_auth_pass is None:
            os.environ.pop('ALD_AUTH_PASS', None)
        else:
            os.environ['ALD_AUTH_PASS'] = self.original_auth_pass
            
        if self.original_allowed_origins is None:
            os.environ.pop('ALD_ALLOWED_ORIGINS', None)
        else:
            os.environ['ALD_ALLOWED_ORIGINS'] = self.original_allowed_origins
        
        # Restore original module variables
        alldebrid_server.AUTH_USER = self.original_module_auth_user
        alldebrid_server.AUTH_PASS = self.original_module_auth_pass
    
    def _test_origin_rejection(self, origin_value, error_message):
        """Helper method to test that a given origin is rejected.
        
        Args:
            origin_value: The Origin header value to test
            error_message: Error message for assertion failures
        """
        os.environ['ALD_ALLOWED_ORIGINS'] = 'http://example.com'
        
        # Set module-level auth variables (auth is required for origin validation)
        alldebrid_server.AUTH_USER = 'testuser'
        alldebrid_server.AUTH_PASS = 'testpass'
        
        handler = alldebrid_server.CustomHTTPRequestHandler(
            self.mock_request, self.client_address, self.mock_server
        )
        
        handler.headers = MagicMock()
        handler.headers.get.return_value = origin_value
        
        sent_headers = []
        def track_headers(key, value):
            sent_headers.append((key, value))
        handler.send_header = track_headers
        
        with patch.object(alldebrid_server.http.server.SimpleHTTPRequestHandler, 'end_headers'):
            handler.end_headers()
        
        cors_headers = [h for h in sent_headers if h[0] == 'Access-Control-Allow-Origin']
        self.assertEqual(len(cors_headers), 0, error_message)
    
    def test_origin_with_newline_sanitized(self):
        """Test that origin headers with newlines are sanitized before being reflected."""
        # Set up auth and allowed origins
        os.environ['ALD_AUTH_USER'] = 'testuser'
        os.environ['ALD_AUTH_PASS'] = 'testpass'
        os.environ['ALD_ALLOWED_ORIGINS'] = 'http://example.com'
        
        # Set module-level auth variables
        alldebrid_server.AUTH_USER = 'testuser'
        alldebrid_server.AUTH_PASS = 'testpass'
        
        # Create handler with mocked components
        handler = alldebrid_server.CustomHTTPRequestHandler(
            self.mock_request, self.client_address, self.mock_server
        )
        
        # Mock headers with malicious origin containing newline
        handler.headers = MagicMock()
        handler.headers.get.return_value = 'http://example.com\r\n'
        
        # Track sent headers
        sent_headers = []
        original_send_header = handler.send_header
        def track_headers(key, value):
            sent_headers.append((key, value))
            # Don't actually send the header to avoid connection issues
        handler.send_header = track_headers
        
        # Mock super().end_headers() to prevent actual header sending
        with patch.object(alldebrid_server.http.server.SimpleHTTPRequestHandler, 'end_headers'):
            handler.end_headers()
        
        # Verify that the origin was sanitized (no \r\n in the header value)
        cors_headers = [h for h in sent_headers if h[0] == 'Access-Control-Allow-Origin']
        self.assertEqual(len(cors_headers), 1, "Should have exactly one CORS header")
        self.assertEqual(cors_headers[0][1], 'http://example.com', 
                        "Origin should be sanitized without newlines")
        self.assertNotIn('\r', cors_headers[0][1], "Should not contain carriage return")
        self.assertNotIn('\n', cors_headers[0][1], "Should not contain newline")
    
    def test_origin_with_carriage_return_sanitized(self):
        """Test that origin headers with carriage returns are sanitized."""
        os.environ['ALD_AUTH_USER'] = 'testuser'
        os.environ['ALD_AUTH_PASS'] = 'testpass'
        os.environ['ALD_ALLOWED_ORIGINS'] = 'http://example.com'
        
        # Set module-level auth variables
        alldebrid_server.AUTH_USER = 'testuser'
        alldebrid_server.AUTH_PASS = 'testpass'
        
        handler = alldebrid_server.CustomHTTPRequestHandler(
            self.mock_request, self.client_address, self.mock_server
        )
        
        handler.headers = MagicMock()
        handler.headers.get.return_value = 'http://example.com\r'
        
        sent_headers = []
        def track_headers(key, value):
            sent_headers.append((key, value))
        handler.send_header = track_headers
        
        with patch.object(alldebrid_server.http.server.SimpleHTTPRequestHandler, 'end_headers'):
            handler.end_headers()
        
        cors_headers = [h for h in sent_headers if h[0] == 'Access-Control-Allow-Origin']
        self.assertEqual(len(cors_headers), 1)
        self.assertEqual(cors_headers[0][1], 'http://example.com')
        self.assertNotIn('\r', cors_headers[0][1])
    
    def test_origin_with_multiple_newlines_sanitized(self):
        """Test that multiple newlines and carriage returns are all removed."""
        os.environ['ALD_AUTH_USER'] = 'testuser'
        os.environ['ALD_AUTH_PASS'] = 'testpass'
        os.environ['ALD_ALLOWED_ORIGINS'] = 'http://example.com'
        
        # Set module-level auth variables
        alldebrid_server.AUTH_USER = 'testuser'
        alldebrid_server.AUTH_PASS = 'testpass'
        
        handler = alldebrid_server.CustomHTTPRequestHandler(
            self.mock_request, self.client_address, self.mock_server
        )
        
        handler.headers = MagicMock()
        handler.headers.get.return_value = 'http://example.com\r\n\r\nSet-Cookie: malicious=true'
        
        sent_headers = []
        def track_headers(key, value):
            sent_headers.append((key, value))
        handler.send_header = track_headers
        
        with patch.object(alldebrid_server.http.server.SimpleHTTPRequestHandler, 'end_headers'):
            handler.end_headers()
        
        cors_headers = [h for h in sent_headers if h[0] == 'Access-Control-Allow-Origin']
        # After sanitization: 'http://example.com\r\n\r\nSet-Cookie: malicious=true' 
        # becomes 'http://example.comSet-Cookie: malicious=true' (concatenated without separator)
        # This won't match allowed origin 'http://example.com', so no CORS header should be sent
        self.assertEqual(len(cors_headers), 0, 
                        "Malicious origin should not match after sanitization")
    
    def test_valid_origin_accepted_after_sanitization(self):
        """Test that a valid origin with extraneous newlines is accepted after sanitization."""
        os.environ['ALD_AUTH_USER'] = 'testuser'
        os.environ['ALD_AUTH_PASS'] = 'testpass'
        os.environ['ALD_ALLOWED_ORIGINS'] = 'http://example.com,http://test.com'
        
        # Set module-level auth variables
        alldebrid_server.AUTH_USER = 'testuser'
        alldebrid_server.AUTH_PASS = 'testpass'
        
        handler = alldebrid_server.CustomHTTPRequestHandler(
            self.mock_request, self.client_address, self.mock_server
        )
        
        handler.headers = MagicMock()
        # Origin with trailing newlines that should be accepted after cleaning
        handler.headers.get.return_value = 'http://example.com\r\n'
        
        sent_headers = []
        def track_headers(key, value):
            sent_headers.append((key, value))
        handler.send_header = track_headers
        
        with patch.object(alldebrid_server.http.server.SimpleHTTPRequestHandler, 'end_headers'):
            handler.end_headers()
        
        cors_headers = [h for h in sent_headers if h[0] == 'Access-Control-Allow-Origin']
        self.assertEqual(len(cors_headers), 1, 
                        "Valid origin with newlines should be accepted after sanitization")
        self.assertEqual(cors_headers[0][1], 'http://example.com')
    
    def test_invalid_origin_rejected(self):
        """Test that an origin not in the allowlist is rejected."""
        os.environ['ALD_AUTH_USER'] = 'testuser'
        os.environ['ALD_AUTH_PASS'] = 'testpass'
        os.environ['ALD_ALLOWED_ORIGINS'] = 'http://example.com'
        
        # Set module-level auth variables
        alldebrid_server.AUTH_USER = 'testuser'
        alldebrid_server.AUTH_PASS = 'testpass'
        
        handler = alldebrid_server.CustomHTTPRequestHandler(
            self.mock_request, self.client_address, self.mock_server
        )
        
        handler.headers = MagicMock()
        handler.headers.get.return_value = 'http://malicious.com'
        
        sent_headers = []
        def track_headers(key, value):
            sent_headers.append((key, value))
        handler.send_header = track_headers
        
        with patch.object(alldebrid_server.http.server.SimpleHTTPRequestHandler, 'end_headers'):
            handler.end_headers()
        
        cors_headers = [h for h in sent_headers if h[0] == 'Access-Control-Allow-Origin']
        self.assertEqual(len(cors_headers), 0, "Invalid origin should be rejected")
    
    def test_subdomain_bypass_attempt_blocked(self):
        """Test that subdomain attacks are blocked (e.g., http://example.com.evil.com)."""
        self._test_origin_rejection(
            'http://example.com.evil.com',
            "Subdomain bypass attempt should be blocked"
        )
    
    def test_path_based_bypass_attempt_blocked(self):
        """Test that path-based attacks are blocked (e.g., http://evil.com/http://example.com)."""
        self._test_origin_rejection(
            'http://evil.com/http://example.com',
            "Path-based bypass attempt should be blocked"
        )
    
    def test_query_string_bypass_attempt_blocked(self):
        """Test that query string attacks are blocked (e.g., http://evil.com?ref=http://example.com)."""
        self._test_origin_rejection(
            'http://evil.com?ref=http://example.com',
            "Query string bypass attempt should be blocked"
        )
    
    def test_no_auth_allows_all_origins(self):
        """Test that when auth is disabled, all origins are allowed (legacy behavior)."""
        # Ensure auth is not set
        os.environ.pop('ALD_AUTH_USER', None)
        os.environ.pop('ALD_AUTH_PASS', None)
        
        # Set module-level auth variables to None
        alldebrid_server.AUTH_USER = None
        alldebrid_server.AUTH_PASS = None
        
        handler = alldebrid_server.CustomHTTPRequestHandler(
            self.mock_request, self.client_address, self.mock_server
        )
        
        handler.headers = MagicMock()
        handler.headers.get.return_value = 'http://any-origin.com'
        
        sent_headers = []
        def track_headers(key, value):
            sent_headers.append((key, value))
        handler.send_header = track_headers
        
        with patch.object(alldebrid_server.http.server.SimpleHTTPRequestHandler, 'end_headers'):
            handler.end_headers()
        
        cors_headers = [h for h in sent_headers if h[0] == 'Access-Control-Allow-Origin']
        self.assertEqual(len(cors_headers), 1)
        self.assertEqual(cors_headers[0][1], '*', "Should allow all origins when no auth")

if __name__ == '__main__':
    unittest.main()
