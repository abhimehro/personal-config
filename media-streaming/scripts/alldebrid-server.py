#!/usr/bin/env python3
import http.server
import socketserver
import os
import sys

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="/Users/abhimehrotra/mnt/alldebrid", **kwargs)
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def start_server(port=8080):
    mount_dir = "/Users/abhimehrotra/mnt/alldebrid"
    
    if not os.path.exists(mount_dir):
        print(f"❌ Mount directory {mount_dir} doesn't exist!")
        print("Please mount your rclone first:")
        print("rclone mount alldebrid:links ~/mnt/alldebrid --dir-cache-time 10s --multi-thread-streams=0 --cutoff-mode=cautious --vfs-cache-mode minimal --buffer-size=0 --read-only --daemon")
        sys.exit(1)
    
    if not os.listdir(mount_dir):
        print(f"⚠️  Warning: Mount directory {mount_dir} is empty!")
        print("Make sure rclone is properly mounted and there's content in your links folder.")
    
    with socketserver.TCPServer(("", port), CustomHTTPRequestHandler) as httpd:
        print(f"🚀 Serving Alldebrid content on http://localhost:{port}")
        print(f"📁 Directory: {mount_dir}")
        print("Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped")

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    start_server(port)
