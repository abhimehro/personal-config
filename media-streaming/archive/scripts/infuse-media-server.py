#!/usr/bin/env python3

import http.server
import socketserver
import subprocess
import os
import sys
import argparse
import base64
import secrets
import string
import time
import html
from urllib.parse import unquote

# Global auth credentials
AUTH_USER = None
AUTH_PASS = None
EXPECTED_AUTH_TOKEN = None

# Rate limiting for auth failures
FAILED_AUTH_ATTEMPTS = {}

class MediaServerHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.rclone_remote = "media:"
        super().__init__(*args, **kwargs)

    def do_HEAD(self):
        if not self.check_auth():
            return
        super().do_HEAD()

    def check_auth(self):
        global AUTH_USER, AUTH_PASS, EXPECTED_AUTH_TOKEN, FAILED_AUTH_ATTEMPTS

        if not AUTH_USER or not AUTH_PASS:
            return True

        # Extract client IP
        client_ip = self.client_address[0]
        now = time.time()

        # Cleanup old failed attempts (older than 1 minute)
        # Avoid concurrent modification issues by copying keys and safely getting values
        for ip in list(FAILED_AUTH_ATTEMPTS.keys()):
            attempt = FAILED_AUTH_ATTEMPTS.get(ip)
            if attempt and now - attempt['last_attempt'] > 60:
                FAILED_AUTH_ATTEMPTS.pop(ip, None)

        # Check rate limit (e.g., max 5 failures per minute)
        attempts = FAILED_AUTH_ATTEMPTS.get(client_ip)
        if attempts and attempts['count'] >= 5 and now - attempts['last_attempt'] < 60:
            self.send_response(429)
            self.send_header('Retry-After', '60')
            self.end_headers()
            self.wfile.write(b'Too Many Requests')
            return False

        auth_header = self.headers.get('Authorization')
        if not auth_header:
            self._record_auth_failure(client_ip, now)
            self.send_auth_request()
            return False

        try:
            auth_type, auth_data = auth_header.split(' ', 1)
            if auth_type.lower() != 'basic':
                self._record_auth_failure(client_ip, now)
                self.send_auth_request()
                return False

            # ⚡ Performance: Compare base64 token directly to avoid decoding and splitting overhead
            if secrets.compare_digest(auth_data, EXPECTED_AUTH_TOKEN):
                # Successful auth resets the counter safely
                FAILED_AUTH_ATTEMPTS.pop(client_ip, None)
                return True
        except Exception:
            pass

        self._record_auth_failure(client_ip, now)
        self.send_auth_request()
        return False

    def _record_auth_failure(self, ip, now):
        """Helper to record failed auth attempts for rate limiting."""
        global FAILED_AUTH_ATTEMPTS
        if ip not in FAILED_AUTH_ATTEMPTS:
            FAILED_AUTH_ATTEMPTS[ip] = {'count': 0, 'last_attempt': now}
        FAILED_AUTH_ATTEMPTS[ip]['count'] += 1
        FAILED_AUTH_ATTEMPTS[ip]['last_attempt'] = now

    def send_auth_request(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Infuse Media Server"')
        self.end_headers()
        self.wfile.write(b'Authentication required')

    def validate_path(self, path):
        """
        Validates the path to prevent directory traversal and argument injection.
        Returns the validated path or raises ValueError.
        """
        # Decode URL encoding (already done by caller, but good to be safe if moved)
        # unquote(path) is called before passing here in do_GET

        # Normalize backslashes to forward slashes to prevent bypasses
        clean_path = path.replace('\\', '/')

        # Remove leading slash to ensure relative path
        clean_path = clean_path.lstrip('/')
        # 1. Prevent Directory Traversal
        # Check for '..' components
        parts = clean_path.split('/')
        if '..' in parts:
            raise ValueError("Invalid path: Directory traversal attempt detected")

        # 2. Prevent Argument Injection (for rclone)
        # Check if path starts with '-'
        if clean_path.startswith('-'):
            raise ValueError("Invalid path: Argument injection attempt detected")

        # 3. Prevent Null Byte Injection
        if '\0' in clean_path:
            raise ValueError("Invalid path: Null byte detected")

        return clean_path

    def do_GET(self):
        """Handle GET requests by proxying to rclone"""
        if not self.check_auth():
            return

        try:
            # unquote first, then validate (which does lstrip)
            raw_path = unquote(self.path)
            path = self.validate_path(raw_path)
        except ValueError as e:
            self.send_error(403, str(e))
            return

        try:
            if path == '':
                # List root directory
                result = subprocess.run(['rclone', 'lsf', self.rclone_remote],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    content = self.generate_directory_listing(result.stdout.strip().split('\n'), '/')
                    self.send_directory_response(content)
                else:
                    self.send_error(500, "Failed to list directory")
            else:
                # Check if it's a directory
                result = subprocess.run(['rclone', 'lsf', f"{self.rclone_remote}{path}/"],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    # It's a directory
                    files = result.stdout.strip().split('\n') if result.stdout.strip() else []
                    content = self.generate_directory_listing(files, path)
                    self.send_directory_response(content)
                else:
                    # Try as a file
                    self.stream_file(path)
        except Exception as e:
            print(f"Error: {e}")
            self.send_error(500, str(e))

    def stream_file(self, path):
        """Stream a file from rclone"""
        try:
            # Start rclone cat process
            process = subprocess.Popen(['rclone', 'cat', f"{self.rclone_remote}{path}"],
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)

            # Send headers
            self.send_response(200)
            self.send_header('Content-Type', self.guess_type(path))
            self.send_header('Accept-Ranges', 'bytes')
            # Security Headers for file content
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()

            # Stream the file
            while True:
                # ⚡ Performance: Read 64KB chunks (up from 8KB) for better throughput
                chunk = process.stdout.read(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)

            process.wait()
        except Exception as e:
            # Cannot send error header after response started
            print(f"Failed to stream file: {e}")

    def generate_directory_listing(self, files, current_path):
        """Generate HTML directory listing"""
        safe_path = html.escape(current_path)

        html_parts = [f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Media Library - {safe_path}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .file {{ display: block; padding: 10px; text-decoration: none; color: #333; }}
                .file:hover {{ background: #f0f0f0; }}
                .directory {{ font-weight: bold; color: #0066cc; }}
                .video {{ color: #ff6600; }}
            </style>
        </head>
        <body>
            <h1>📁 Media Library: /{safe_path}</h1>
        """]

        # Add parent directory link if not root
        if current_path and current_path != '/':
            parent = '/'.join(current_path.rstrip('/').split('/')[:-1])
            # Parent path is constructed safely from split, but escaping is good hygiene
            safe_parent = html.escape(parent)
            html_parts.append(f'<a href="/{safe_parent}" class="file directory">📁 .. (Parent Directory)</a>\n')

        # ⚡ Performance: tuple for fast C-level endswith checking
        video_exts = ('.mp4', '.mkv', '.avi', '.mov')

        # Add files and directories
        # ⚡ Performance: Use generator expression/list comprehension instead of for loop with .append
        # Pre-compute the base path logic to avoid evaluating it per-item
        # Pre-escape the base path once to avoid O(N) redundant string concatenations and html.escape calls
        # This reduces overhead for large directories
        base_path = f"{current_path.rstrip('/')}/" if current_path != '/' else ""
        safe_base_path = html.escape(base_path)

        items_html = [
            (
                f'<a href="/{safe_base_path}{html.escape(item)}" class="file directory">'
                f'📁 {html.escape(item)[:-1]}</a>\n'
            )
            if item.endswith('/') else
            (
                f'<a href="/{safe_base_path}{html.escape(item)}" class="file video">'
                f'{"🎬" if item.lower().endswith(video_exts) else "📄"} {html.escape(item)}</a>\n'
            )
            for item in files if item
        ]
        html_parts.extend(items_html)

        html_parts.append("""
        </body>
        </html>
        """)
        return "".join(html_parts)

    def send_directory_response(self, content):
        """Send directory listing response"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(content.encode('utf-8'))))
        # Security Headers
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'unsafe-inline'; script-src 'none';")
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))

def setup_authentication(args):
    """Set up authentication credentials with secure defaults.

    Returns: tuple (AUTH_USER, AUTH_PASS, EXPECTED_AUTH_TOKEN) or exits if password cannot be generated.
    """
    user = args.user or os.environ.get("AUTH_USER")
    password = args.password or os.environ.get("AUTH_PASS")

    generated_user = False
    if not user:
        user_alphabet = string.ascii_lowercase + string.digits
        user = "user_" + "".join(secrets.SystemRandom().choices(user_alphabet, k=8))
        generated_user = True

    if not password:
        # If output is a TTY, generate a password for interactive use
        if sys.stdout.isatty():
            alphabet = string.ascii_letters + string.digits
            password = ''.join(secrets.choices(alphabet, k=16))
            print("\n🔒 Security: Authentication Enabled")
            print(f"   User: {user}")
            print(f"   Password: {password}")
            if generated_user:
                print("   (Random username generated. Set custom user via --user)")
            print("   (A random password has been generated and shown above. Store it securely, and consider setting a custom password via --password or AUTH_PASS.)\n")
        else:
            # Fail and require user to set a password to avoid logging it
            print("\n❌ Error: Auto-generating a password is not supported when output is not a TTY.", file=sys.stderr)
            print("   (e.g., when output is redirected to a file or running in automation/CI)", file=sys.stderr)
            print("Please provide a password using the --password argument or the AUTH_PASS environment variable.", file=sys.stderr)
            sys.exit(1)
    else:
        print("\n🔒 Security: Authentication Enabled (using configured credentials; password is hidden)\n")

    expected_token = base64.b64encode(f"{user}:{password}".encode('utf-8')).decode('utf-8')
    return user, password, expected_token

def verify_rclone_remote():
    """Verify that rclone media remote exists.

    Exits if the remote is not found.
    """
    result = subprocess.run(['rclone', 'listremotes'], capture_output=True, text=True)
    if 'media:' not in result.stdout:
        print("❌ Error: 'media:' remote not found in rclone")
        print("Available remotes:")
        print(result.stdout)
        sys.exit(1)

def main():
    """Start the Infuse-compatible media server."""
    parser = argparse.ArgumentParser(description="Infuse Media Server")
    parser.add_argument("port", type=int, nargs="?", default=8080, help="Port to serve on")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind to")
    parser.add_argument("--public", action="store_true", help="Bind to all interfaces (0.0.0.0)")
    parser.add_argument("--user", help="Username for Basic Auth")
    parser.add_argument("--password", help="Password for Basic Auth")
    args = parser.parse_args()

    global AUTH_USER, AUTH_PASS, EXPECTED_AUTH_TOKEN

    # Verify rclone setup
    verify_rclone_remote()

    # Configure authentication
    AUTH_USER, AUTH_PASS, EXPECTED_AUTH_TOKEN = setup_authentication(args)

    # Configure host
    host = "0.0.0.0" if args.public else args.host

    print(f"🚀 Starting Infuse-Compatible Media Server on http://{host}:{args.port}")
    if args.public:
        print(f"⚠️  Public Access Enabled (0.0.0.0). Ensure your network is trusted.")

    try:
        # ⚡ Performance: Use ThreadingTCPServer to handle concurrent requests (e.g. streaming + browsing)
        with socketserver.ThreadingTCPServer((host, args.port), MediaServerHandler) as httpd:
            print("Press Ctrl+C to stop")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")

if __name__ == "__main__":
    main()