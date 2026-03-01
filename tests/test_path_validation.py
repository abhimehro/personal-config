import unittest
import sys
import os

# Add the script directory to path to import the module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../media-streaming/archive/scripts')))

# Import the module
import importlib.util
spec = importlib.util.spec_from_file_location("infuse_media_server",
    os.path.abspath(os.path.join(os.path.dirname(__file__), '../media-streaming/archive/scripts/infuse-media-server.py')))
infuse_media_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(infuse_media_server)

class TestPathValidation(unittest.TestCase):
    def setUp(self):
        # Instantiate the handler without calling __init__ fully (mocking request/client_address/server)
        # However, SimpleHTTPRequestHandler.__init__ is complex.
        # Easier to just call the method since it doesn't use self state in my implementation,
        # but technically it's an instance method.
        # So I will create a mock instance.
        self.handler = infuse_media_server.MediaServerHandler
        # Since validate_path is an instance method but doesn't use self, we can call it unbound or bind it to a dummy.
        # Or better, just instantiate a dummy.

    def validate_path(self, path):
        # Helper to call the method on the class with a dummy self (or just use the class if it was static, but it's not decorated)
        # Since it doesn't use 'self', I can pass None as self if I call it as a function from the class.
        return infuse_media_server.MediaServerHandler.validate_path(None, path)

    def test_valid_paths(self):
        valid_paths = [
            "folder/file.mp4",
            "folder/subfolder/",
            "file with spaces.mkv",
            "movie-2023.mp4",
            "folder/..filename..mp4", # legitimate filenames containing dots
            ""
        ]
        for p in valid_paths:
            try:
                self.validate_path(p)
            except ValueError as e:
                self.fail(f"Valid path '{p}' rejected: {e}")

    def test_traversal_attempts(self):
        invalid_paths = [
            "../secret",
            "folder/../secret",
            "folder/../../etc/passwd",
            "..",
            "/../secret",
            "..\\secret",
            "folder\\..\\secret",
            "..\\..\\etc\\passwd",
            "\\\\etc\\\\passwd",
            "\\\\folder\\\\file",
        ]
        for p in invalid_paths:
            with self.assertRaises(ValueError, msg=f"Traversal path '{p}' should fail"):
                self.validate_path(p)

    def test_argument_injection(self):
        invalid_paths = [
            "-flag",
            "--option",
            "-v"
        ]
        for p in invalid_paths:
            with self.assertRaises(ValueError, msg=f"Argument injection path '{p}' should fail"):
                self.validate_path(p)

    def test_null_byte(self):
        invalid_paths = [
            "file.mp4\0",
            "folder\0/file"
        ]
        for p in invalid_paths:
            with self.assertRaises(ValueError, msg=f"Null byte path '{p}' should fail"):
                self.validate_path(p)

if __name__ == '__main__':
    unittest.main()
