#!/usr/bin/env python3

import http.server
import socketserver
import subprocess
import json
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

class MediaServerHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.rclone_remote = "media:"
        super().__init__(*args, **kwargs)
    
    def do_HEAD(self):
        if not self.check_auth():
            return
        super().do_HEAD()

    def check_auth(self):
        global AUTH_USER, AUTH_PASS

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

            decoded = base64.b64decode(auth_data).decode('utf-8')
            username, password = decoded.split(':', 1)

            user_match = secrets.compare_digest(username, AUTH_USER)
            pass_match = secrets.compare_digest(password, AUTH_PASS)

            if user_match and pass_match:
                return True
        except Exception:
            pass

        time.sleep(1)
        self.send_auth_request()
        return False

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

        # Remove leading slash to ensure relative path
        clean_path = path.lstrip('/')

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

        html_content = f"""
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
        """
        
        # Add parent directory link if not root
        if current_path and current_path != '/':
            parent = '/'.join(current_path.rstrip('/').split('/')[:-1])
            # Parent path is constructed safely from split, but escaping is good hygiene
            safe_parent = html.escape(parent)
            html_content += f'<a href="/{safe_parent}" class="file directory">📁 .. (Parent Directory)</a>\n'
        
        # Add files and directories
        for item in files:
            if not item:
                continue

            # Escape the item name for display and URL construction
            safe_item = html.escape(item)

            # Construct item path. Note: item_path is used in href, so we should be careful.
            # If current_path has special chars, they are already in it.
            # We need to construct the URL properly.
            # Ideally we should use quote() for hrefs, and escape() for display.
            # For now, let's escape for HTML context to prevent XSS.

            item_path = f"{current_path.rstrip('/')}/{item}" if current_path != '/' else item
            safe_item_path = html.escape(item_path)

            if item.endswith('/'):
                # Directory
                html_content += f'<a href="/{safe_item_path}" class="file directory">📁 {safe_item[:-1]}</a>\n'
            else:
                # File
                icon = "🎬" if any(item.lower().endswith(ext) for ext in ['.mp4', '.mkv', '.avi', '.mov']) else "📄"
                html_content += f'<a href="/{safe_item_path}" class="file video">{icon} {safe_item}</a>\n'
        
        html_content += """
        </body>
        </html>
        """
        return html_content
    
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

def main():
    parser = argparse.ArgumentParser(description="Infuse Media Server")
    parser.add_argument("port", type=int, nargs="?", default=8080, help="Port to serve on")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind to")
    parser.add_argument("--public", action="store_true", help="Bind to all interfaces (0.0.0.0)")
    parser.add_argument("--user", help="Username for Basic Auth")
    parser.add_argument("--password", help="Password for Basic Auth")
    args = parser.parse_args()

    global AUTH_USER, AUTH_PASS
    
    # Check if rclone media remote exists
    result = subprocess.run(['rclone', 'listremotes'], capture_output=True, text=True)
    if 'media:' not in result.stdout:
        print("❌ Error: 'media:' remote not found in rclone")
        print("Available remotes:")
        print(result.stdout)
        sys.exit(1)
    
    host = "0.0.0.0" if args.public else args.host

    # Generate secure defaults
    AUTH_USER = args.user or os.environ.get("AUTH_USER")
    AUTH_PASS = args.password or os.environ.get("AUTH_PASS")

    generated_user = False
    if not AUTH_USER:
        user_alphabet = string.ascii_lowercase + string.digits
        AUTH_USER = "user_" + "".join(secrets.choice(user_alphabet) for _ in range(8))
        generated_user = True

    if not AUTH_PASS:
        alphabet = string.ascii_letters + string.digits
        AUTH_PASS = ''.join(secrets.choice(alphabet) for i in range(16))
        print("\n🔒 Security: Authentication Enabled")
        print(f"   User: {AUTH_USER}")
        print(f"   Pass: {AUTH_PASS}")
        if generated_user:
             print("   (Random username generated. Set custom user via --user)")
        print("   (Use these credentials to access the server; store the password securely)\n")
    else:
        print("\n🔒 Security: Authentication Enabled (using configured credentials; password is hidden)\n")

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