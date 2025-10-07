#!/usr/bin/env python3

import http.server
import socketserver
import subprocess
import json
import os
import sys
from urllib.parse import unquote

class MediaServerHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.rclone_remote = "media:"
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests by proxying to rclone"""
        path = unquote(self.path.lstrip('/'))
        
        try:
            if path == '' or path == '/':
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
            self.end_headers()
            
            # Stream the file
            while True:
                chunk = process.stdout.read(8192)
                if not chunk:
                    break
                self.wfile.write(chunk)
            
            process.wait()
        except Exception as e:
            self.send_error(500, f"Failed to stream file: {e}")
    
    def generate_directory_listing(self, files, current_path):
        """Generate HTML directory listing"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Media Library - {current_path}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .file {{ display: block; padding: 10px; text-decoration: none; color: #333; }}
                .file:hover {{ background: #f0f0f0; }}
                .directory {{ font-weight: bold; color: #0066cc; }}
                .video {{ color: #ff6600; }}
            </style>
        </head>
        <body>
            <h1>📁 Media Library: /{current_path}</h1>
        """
        
        # Add parent directory link if not root
        if current_path and current_path != '/':
            parent = '/'.join(current_path.rstrip('/').split('/')[:-1])
            html += f'<a href="/{parent}" class="file directory">📁 .. (Parent Directory)</a>\n'
        
        # Add files and directories
        for item in files:
            if not item:
                continue
            item_path = f"{current_path.rstrip('/')}/{item}" if current_path != '/' else item
            if item.endswith('/'):
                # Directory
                html += f'<a href="/{item_path}" class="file directory">📁 {item[:-1]}</a>\n'
            else:
                # File
                icon = "🎬" if any(item.lower().endswith(ext) for ext in ['.mp4', '.mkv', '.avi', '.mov']) else "📄"
                html += f'<a href="/{item_path}" class="file video">{icon} {item}</a>\n'
        
        html += """
        </body>
        </html>
        """
        return html
    
    def send_directory_response(self, content):
        """Send directory listing response"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(content.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    
    # Check if rclone media remote exists
    result = subprocess.run(['rclone', 'listremotes'], capture_output=True, text=True)
    if 'media:' not in result.stdout:
        print("❌ Error: 'media:' remote not found in rclone")
        print("Available remotes:")
        print(result.stdout)
        sys.exit(1)
    
    print(f"🚀 Starting Infuse-Compatible Media Server on port {port}")
    print(f"📁 Serving content from rclone remote: media:")
    print(f"🎬 Add this to Infuse:")
    print(f"   Protocol: Other/Network Share")
    print(f"   Address: http://192.168.0.199:{port}")
    print(f"   OR as WebDAV:")
    print(f"   Address: 192.168.0.199")
    print(f"   Port: {port}")
    print()
    
    try:
        with socketserver.TCPServer(("", port), MediaServerHandler) as httpd:
            print(f"✅ Server running at http://192.168.0.199:{port}")
            print("Press Ctrl+C to stop")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")

if __name__ == "__main__":
    main()