#!/bin/bash

echo "🔧 Final Media Server - Network Diagnosis & Setup"
echo "=================================================="
echo

# Kill any existing servers
echo "🧹 Cleaning up existing servers..."
pkill -f "rclone serve" 2>/dev/null
pkill -f "infuse-media-server.py" 2>/dev/null
pkill -f "python.*media.*server" 2>/dev/null
sleep 2

# Network discovery
echo "🔍 Network Discovery:"
DEFAULT_INTERFACE=$(route get default | grep interface | awk '{print $2}')
echo "   Default Interface: $DEFAULT_INTERFACE"

# Get all possible IP addresses
for interface in en0 en1 en2 en3 en4 en5 en6; do
    ip=$(ipconfig getifaddr $interface 2>/dev/null)
    if [[ -n "$ip" ]]; then
        echo "   $interface: $ip"
        if [[ "$interface" == "$DEFAULT_INTERFACE" ]]; then
            PRIMARY_IP="$ip"
            echo "   ★ PRIMARY: $interface ($ip)"
        fi
    fi
done

# Fallback if no primary found
if [[ -z "$PRIMARY_IP" ]]; then
    PRIMARY_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "127.0.0.1")
fi

echo "   🎯 Using IP: $PRIMARY_IP"
echo

# Test ports
echo "🔌 Finding available port..."
for port in 8080 8081 8082 8083 8090 8091; do
    if ! lsof -nP -i:$port | grep -q LISTEN; then
        AVAILABLE_PORT=$port
        echo "   ✅ Port $port is available"
        break
    else
        echo "   ❌ Port $port is in use"
    fi
done

if [[ -z "$AVAILABLE_PORT" ]]; then
    echo "   ⚠️ No ports available, using 8080 anyway"
    AVAILABLE_PORT=8080
fi

echo

# Check rclone
echo "📡 Checking rclone configuration..."
if ! rclone listremotes | grep -q "media:"; then
    echo "❌ Error: 'media:' remote not found"
    echo "Available remotes:"
    rclone listremotes
    exit 1
else
    echo "✅ rclone 'media:' remote found"
fi

# Test media remote
echo "   Testing media remote..."
if rclone lsf media: >/dev/null 2>&1; then
    echo "   ✅ Media remote accessible"
    echo "   📁 Available folders:"
    rclone lsf media: | sed 's/^/      /'
else
    echo "   ❌ Media remote not accessible"
    echo "   💡 Try running: ~/fix-gdrive.sh"
    exit 1
fi

echo

# Start simple HTTP server
echo "🚀 Starting HTTP server..."
echo "   Address: $PRIMARY_IP:$AVAILABLE_PORT"

# Create a simple Python server inline
cat > /tmp/simple_server.py << EOF
import http.server
import socketserver
import subprocess
import sys

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '':
            # List root directory
            try:
                result = subprocess.run(['rclone', 'lsf', 'media:'], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    content = '<html><body><h1>Media Library</h1><ul>'
                    for item in result.stdout.strip().split('\n'):
                        if item:
                            content += f'<li><a href="/{item}">{item}</a></li>'
                    content += '</ul></body></html>'
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html')
                    self.send_header('Content-Length', str(len(content)))
                    self.end_headers()
                    self.wfile.write(content.encode())
                else:
                    self.send_error(500, "Failed to list directory")
            except Exception as e:
                self.send_error(500, str(e))
        else:
            # For now, just show a placeholder
            content = f'<html><body><h1>File: {self.path}</h1><p>File streaming not implemented in simple server</p></body></html>'
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(content.encode())

port = int(sys.argv[1])
with socketserver.TCPServer(("", port), Handler) as httpd:
    print(f"Server running on port {port}")
    httpd.serve_forever()
EOF

echo "   Starting server on port $AVAILABLE_PORT..."
nohup python3 /tmp/simple_server.py $AVAILABLE_PORT > ~/simple-server.log 2>&1 &
SERVER_PID=$!

sleep 3

# Test the server
echo "🧪 Testing server..."
if curl -s -I "http://localhost:$AVAILABLE_PORT/" | grep -q "200 OK"; then
    echo "   ✅ Server responding locally"
else
    echo "   ❌ Server not responding locally"
    echo "   Check logs: tail ~/simple-server.log"
    exit 1
fi

if curl -s -I "http://$PRIMARY_IP:$AVAILABLE_PORT/" | grep -q "200 OK"; then
    echo "   ✅ Server responding on network"
else
    echo "   ⚠️ Server not responding on network (firewall/network issue)"
fi

echo
echo "🎬 INFUSE CONFIGURATION:"
echo "========================"
echo "Try these options in order:"
echo
echo "Option 1 - Direct URL:"
echo "   Add Share → via Direct URL"
echo "   URL: http://$PRIMARY_IP:$AVAILABLE_PORT"
echo
echo "Option 2 - WebDAV:"
echo "   Protocol: WebDAV"
echo "   Address: $PRIMARY_IP"
echo "   Port: $AVAILABLE_PORT"
echo "   Username: (blank)"
echo "   Password: (blank)"
echo "   Path: /"
echo
echo "Option 3 - Alternative IPs to try:"
for interface in en0 en1 en5; do
    alt_ip=$(ipconfig getifaddr $interface 2>/dev/null)
    if [[ -n "$alt_ip" && "$alt_ip" != "$PRIMARY_IP" ]]; then
        echo "   Try: http://$alt_ip:$AVAILABLE_PORT"
    fi
done

echo
echo "🌐 Test in browser first:"
echo "   http://$PRIMARY_IP:$AVAILABLE_PORT"
echo
echo "🔧 Server PID: $SERVER_PID (kill with: kill $SERVER_PID)"
echo "📊 Logs: tail -f ~/simple-server.log"

# Keep script running to show logs
echo
echo "📋 Live server logs (Ctrl+C to stop):"
tail -f ~/simple-server.log
EOF