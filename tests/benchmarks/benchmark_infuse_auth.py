import concurrent.futures
import importlib.util
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request


def wait_for_port(port, timeout=5.0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def worker(url, i, auth_header):
    try:
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("Authorization", auth_header)
        start_time = time.time()
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                status = response.status
        except urllib.error.HTTPError as e:
            status = e.code
        except urllib.error.URLError:
            status = -1
        end_time = time.time()
        return (i, end_time - start_time, status)
    except Exception as e:
        return (i, -1, str(e))


class ServerRunner:
    def __init__(self, port):
        self.port = port
        self.server_thread = None
        self.old_argv = sys.argv

    def start(self):
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "media-streaming",
            "archive",
            "scripts",
            "infuse-media-server.py",
        )
        spec = importlib.util.spec_from_file_location("infuse_media_server", script_path)
        self.infuse_media_server = importlib.util.module_from_spec(spec)
        sys.modules["infuse_media_server"] = self.infuse_media_server
        spec.loader.exec_module(self.infuse_media_server)

        self.infuse_media_server.verify_rclone_remote = lambda: None

        sys.argv = [
            "infuse-media-server.py",
            str(self.port),
            "--user",
            "admin",
            "--password",
            "admin",
        ]

        self.server_thread = threading.Thread(target=self.infuse_media_server.main)
        self.server_thread.daemon = True
        self.server_thread.start()

        if not wait_for_port(self.port):
            sys.argv = self.old_argv
            raise RuntimeError(f"Server failed to start on port {self.port} within timeout")

    def stop(self):
        sys.argv = self.old_argv


def run_valid_auth_benchmark(num_requests=50, concurrency=50, port=8081):
    _run_benchmark(num_requests, concurrency, port, "Basic YWRtaW46YWRtaW4=", "Valid Auth")


def run_invalid_auth_benchmark(num_requests=50, concurrency=50, port=8081):
    _run_benchmark(num_requests, concurrency, port, "Basic YmFkOnBhc3N3b3Jk", "Invalid Auth")


def _run_benchmark(num_requests, concurrency, port, auth_header, scenario_name):
    url = f"http://127.0.0.1:{port}/"

    print(
        f"\nStarting {scenario_name} benchmark with {num_requests} total requests, concurrency {concurrency}"
    )

    results = []
    start_time_total = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker, url, i, auth_header) for i in range(num_requests)]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    end_time_total = time.time()
    total_time = end_time_total - start_time_total

    successes = [r for r in results if isinstance(r[2], int) and r[2] in (200, 401)]
    rate_limited = [r for r in results if isinstance(r[2], int) and r[2] == 429]
    failures = [r for r in results if r not in successes and r not in rate_limited]

    if successes or rate_limited:
        valid_responses = successes + rate_limited
        avg_latency = sum(r[1] for r in valid_responses) / len(valid_responses)
        max_latency = max(r[1] for r in valid_responses)
        min_latency = min(r[1] for r in valid_responses)
    else:
        avg_latency = max_latency = min_latency = 0

    print(f"\n--- {scenario_name} Benchmark Results ---")
    print(f"Total time taken: {total_time:.2f} seconds")
    if scenario_name == "Invalid Auth":
        print(f"401 Unauthorized responses: {len(successes)}")
    else:
        print(f"200 OK responses: {len(successes)}")
    print(f"429 Too Many Requests responses: {len(rate_limited)}")
    print(f"Failed requests (timeout/error): {len(failures)}")
    print(f"Average latency per request: {avg_latency:.2f} seconds")
    print(f"Min latency: {min_latency:.2f} seconds")
    print(f"Max latency: {max_latency:.2f} seconds")
    if total_time > 0:
        print(
            f"Throughput: {(len(successes) + len(rate_limited)) / total_time:.2f} requests/second"
        )
    else:
        print("Throughput: 0.00 requests/second")


def run_benchmark(num_requests=50, concurrency=50):
    port = 8081
    server = ServerRunner(port)
    try:
        server.start()
        run_valid_auth_benchmark(num_requests, concurrency, port=port)
        run_invalid_auth_benchmark(num_requests, concurrency, port=port)
    except RuntimeError as e:
        print(e)
    finally:
        server.stop()


if __name__ == "__main__":
    run_benchmark(num_requests=50, concurrency=50)
