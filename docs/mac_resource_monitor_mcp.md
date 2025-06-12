# MacOS Resource Monitor MCP Server

This document summarizes how to run and extend the MacOS Resource Monitor MCP server. The server exposes real‑time CPU, memory and network usage through the Model Context Protocol (MCP).

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Pratyay/mac-monitor-mcp.git
   cd mac-monitor-mcp
   ```
2. (Optional) Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. Install the dependencies:
   ```bash
   pip install mcp
   ```

## Running the Server

Start the MCP server with:
```bash
python src/monitor.py
```
You should see output similar to:
```text
Simple MacOS Resource Monitor MCP server starting...
Monitoring CPU, Memory, and Network resource usage...
```

## Using `get_resource_intensive_processes()`

The server exposes a single tool that returns JSON describing the most CPU, memory, and network intensive processes. Each entry contains fields such as `pid`, `cpu_percent`, `memory_percent`, and `network_connections`.

## Integration with LLM Clients

Add a server block to clients such as Cursor or Claude Desktop so they can call the MCP tool. After restarting the client, LLMs will prompt before invoking `get_resource_intensive_processes`.

## Potential Enhancements

- **Disk I/O Monitoring** – use `iostat` for device statistics or tools like `iosnoop`, `fs_usage`, or `iotop` for per‑process monitoring.
- **Network Bandwidth** – leverage `psutil.net_io_counters(pernic=True)` to compute throughput per interface.
- **Visualization Dashboard** – build a small Flask app with Chart.js or create plots with Matplotlib to visualize resource usage over time.
- **Cross‑Platform Support** – replace direct `ps`/`lsof` calls with `psutil` to support Linux and Windows.

## Troubleshooting

- **Virtual Environment Problems** – confirm that Python 3.10+ is available and the virtual environment is activated before installing `mcp`.
- **`lsof` Permissions** – run the server with elevated privileges or configure a sudoers rule to list all network connections.
- **Missing Utilities** – if tools like `iostat` or `lsof` are missing, install Xcode command‑line tools using:
  ```bash
  xcode-select --install
  ```

## Resources

- [MCP Python SDK](https://pypi.org/project/mcp/)
- [MacOS Resource Monitor repository](https://github.com/Pratyay/mac-monitor-mcp)
- [psutil documentation](https://psutil.readthedocs.io/en/latest/)

