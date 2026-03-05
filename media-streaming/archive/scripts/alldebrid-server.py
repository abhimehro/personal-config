#!/usr/bin/env python3
import http.server
import socketserver
import os
import sys
import argparse
import base64
import secrets
import string
import time

MOUNT_DIR = os.environ.get("ALD_MOUNT_DIR", os.path.expanduser("~/mnt/alldebrid"))

# Global auth credentials
AUTH_USER = None
AUTH_PASS = None
EXPECTED_AUTH_TOKEN = None

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=MOUNT_DIR, **kwargs)

    def do_HEAD(self):
        if not self.check_auth():
            return
        super().do_HEAD()

    def do_GET(self):
        if not self.check_auth():
            return
        super().do_GET()

    def check_auth(self):
        global AUTH_USER, AUTH_PASS, EXPECTED_AUTH_TOKEN

        # If no auth configured (shouldn't happen with new logic), allow
        if not AUTH_USER or not AUTH_PASS:
            return True

        auth_header = self.headers.get('Authorization')
        if not auth_header:
            self.send_auth_request()
            return False

        try:
            auth_type, auth_data = auth_header.split(' ', 1)
            if auth_type.lower() != 'basic':
                self.send_auth_request()
                return False

            # ⚡ Performance: Compare base64 token directly (O(1) request time vs O(n) decoding + splitting)
            # Use constant time comparison to prevent timing attacks
            if secrets.compare_digest(auth_data, EXPECTED_AUTH_TOKEN):
                return True
        except Exception:
            # Malformed header or decoding error
            pass

        # Simple delay to mitigate brute force attacks
        time.sleep(1)
        self.send_auth_request()
        return False

    def send_auth_request(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Media Server"')
        self.end_headers()
        self.wfile.write(b'Authentication required')

    def end_headers(self):
        # Handle CORS
        # If auth is enabled, strictly control CORS
        if AUTH_USER and AUTH_PASS:
            origin = self.headers.get('Origin')
            allowed_origins_env = os.environ.get('ALD_ALLOWED_ORIGINS')

            if allowed_origins_env and origin:
                allowed_origins = {o.strip() for o in allowed_origins_env.split(',') if o.strip()}
                safe_origin = origin.replace("\r", "").replace("\n", "")
                # Security: Use exact match, not substring check, to prevent bypass attacks
                # (e.g., "http://example.com" should not match "http://example.com.evil.com")
                if safe_origin in allowed_origins:  # This 'in' checks set membership (exact match), not substring
                    self.send_header('Access-Control-Allow-Origin', safe_origin)
                    self.send_header('Vary', 'Origin')
            # If no allowed origins configured, do not send Access-Control-Allow-Origin
            # This effectively blocks browser fetch/XHR from other origins
        else:
            # No auth, allow all (legacy behavior)
            self.send_header('Access-Control-Allow-Origin', '*')

        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()

def start_server(host, port):
    mount_dir = MOUNT_DIR

    if not os.path.exists(mount_dir):
        print(f"❌ Mount directory {mount_dir} doesn't exist!")
        print("Please mount your rclone first:")
        print("rclone mount alldebrid:links ~/mnt/alldebrid --dir-cache-time 10s --multi-thread-streams=0 --cutoff-mode=cautious --vfs-cache-mode minimal --buffer-size=0 --read-only --daemon")
        sys.exit(1)

    if not os.listdir(mount_dir):
        print(f"⚠️  Warning: Mount directory {mount_dir} is empty!")
        print("Make sure rclone is properly mounted and there's content in your links folder.")

    # ⚡ Performance: Use ThreadingTCPServer to handle concurrent requests
    with socketserver.ThreadingTCPServer((host, port), CustomHTTPRequestHandler) as httpd:
        print(f"🚀 Serving Alldebrid content on http://{host}:{port}")
        print(f"📁 Directory: {mount_dir}")
        print("Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Alldebrid Media Server")
    parser.add_argument("port", type=int, nargs="?", default=8080, help="Port to serve on")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind to")
    parser.add_argument("--public", action="store_true", help="Bind to all interfaces (0.0.0.0)")
    parser.add_argument("--user", help="Username for Basic Auth")
    parser.add_argument("--password", help="Password for Basic Auth")
    args = parser.parse_args()

    host = "0.0.0.0" if args.public else args.host

    # Generate secure defaults
    AUTH_USER = args.user or os.environ.get("AUTH_USER")
    AUTH_PASS = args.password or os.environ.get("AUTH_PASS")

    generated_user = False
    if not AUTH_USER:
        # Generate a random username to avoid "admin" default
        user_alphabet = string.ascii_lowercase + string.digits
        AUTH_USER = "user_" + "".join(secrets.choices(user_alphabet, k=8))
        generated_user = True

    if not AUTH_PASS:
        alphabet = string.ascii_letters + string.digits
        AUTH_PASS = ''.join(secrets.choices(alphabet, k=16))
        print("\n🔒 Security: Authentication Enabled")
        print(f"   User: {AUTH_USER}")
        print(f"   Pass: {AUTH_PASS}")
        if generated_user:
             print("   (Random username generated. Set custom user via --user)")
        print("   (Use these credentials to access the server)\n")
    else:
        print("\n🔒 Security: Authentication Enabled (using configured credentials)\n")

    # Pre-compute expected token
    EXPECTED_AUTH_TOKEN = base64.b64encode(f"{AUTH_USER}:{AUTH_PASS}".encode('utf-8')).decode('utf-8')

    start_server(host, args.port)
