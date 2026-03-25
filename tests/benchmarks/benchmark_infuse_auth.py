import concurrent.futures
import importlib.util
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from unittest.mock import patch


def wait_for_port(port, timeout=5.0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def worker(url, i):
    try:
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("Authorization", "Basic YmFkOnBhc3N3b3Jk")  # bad:password
        start_time = time.time()
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                status = response.status
        except urllib.error.HTTPError as e:
            status = e.code
        except urllib.error.URLError as e:
            status = -1
        end_time = time.time()
        return (i, end_time - start_time, status)
    except Exception as e:
        return (i, -1, str(e))


def run_benchmark(num_requests=50, concurrency=50):
    port = 8081
    url = f"http://127.0.0.1:{port}/"

    print(
        f"Starting benchmark with {num_requests} total requests, concurrency {concurrency}"
    )

    # Start the server using import instead of subprocess so we can mock verify_rclone_remote
    script_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "media-streaming",
        "archive",
        "scripts",
        "infuse-media-server.py",
    )
    spec = importlib.util.spec_from_file_location("infuse_media_server", script_path)
    infuse_media_server = importlib.util.module_from_spec(spec)
    sys.modules["infuse_media_server"] = infuse_media_server
    spec.loader.exec_module(infuse_media_server)

    # Mock verify_rclone_remote to bypass rclone requirement
    infuse_media_server.verify_rclone_remote = lambda: None

    # Mock sys.argv
    old_argv = sys.argv
    sys.argv = [
        "infuse-media-server.py",
        str(port),
        "--user",
        "admin",
        "--password",
        "admin",
    ]

    # Start server in a background thread
    server_thread = threading.Thread(target=infuse_media_server.main)
    server_thread.daemon = True
    server_thread.start()

    # Wait for server to start
    if not wait_for_port(port):
        print(f"Server failed to start on port {port} within timeout")
        sys.argv = old_argv
        return

    results = []
    start_time_total = time.time()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(worker, url, i) for i in range(num_requests)]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
    finally:
        sys.argv = old_argv

    end_time_total = time.time()
    total_time = end_time_total - start_time_total

    successes = [r for r in results if isinstance(r[2], int) and r[2] == 401]
    rate_limited = [r for r in results if isinstance(r[2], int) and r[2] == 429]
    failures = [r for r in results if r not in successes and r not in rate_limited]

    if successes or rate_limited:
        valid_responses = successes + rate_limited
        avg_latency = sum(r[1] for r in valid_responses) / len(valid_responses)
        max_latency = max(r[1] for r in valid_responses)
        min_latency = min(r[1] for r in valid_responses)
    else:
        avg_latency = max_latency = min_latency = 0

    print(f"\n--- Benchmark Results ---")
    print(f"Total time taken: {total_time:.2f} seconds")
    print(f"401 Unauthorized responses: {len(successes)}")
    print(f"429 Too Many Requests responses: {len(rate_limited)}")
    print(f"Failed requests (timeout/error): {len(failures)}")
    print(f"Average latency per request: {avg_latency:.2f} seconds")
    print(f"Min latency: {min_latency:.2f} seconds")
    print(f"Max latency: {max_latency:.2f} seconds")
    print(
        f"Throughput: {(len(successes) + len(rate_limited)) / total_time:.2f} requests/second"
    )


if __name__ == "__main__":
    run_benchmark(num_requests=50, concurrency=50)
