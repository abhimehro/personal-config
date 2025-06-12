# Personal System Configuration

A repository for personal system configurations, scripts, and documentation to make my macOS setup reproducible and backed up.

## Overview

This repository contains configuration files, shell scripts, and documentation for my personal computing environment. By keeping these files in a Git repository, I can:

- Back up important configurations and documentation
- Track changes to my system setup over time
- Easily reproduce my environment on a new machine
- Share specific configurations or scripts with others when needed
- Document solutions to problems I've solved

## Repository Structure

```
personal-config/
├── docs/               # Documentation and guides
│   └── vpn_switching_guide.md  # VPN switching workflow documentation
├── configs/            # Configuration files (dotfiles)
└── README.md           # This file
```

## Documentation

### VPN Switching Guide

The [VPN Switching Guide](docs/vpn_switching_guide.md) documents the workflow for switching between Cloudflare WARP+Control D DNS and ProtonVPN configurations for different use cases. It includes step-by-step instructions, troubleshooting steps, and technical details.

### MacOS Resource Monitor MCP Server

The [MacOS Resource Monitor guide](docs/mac_resource_monitor_mcp.md) explains how to run the lightweight MCP server that exposes CPU, memory, and network usage on macOS. It covers installation, usage, integration with LLM clients, and troubleshooting tips.

## Future Additions

This repository will grow to include:

- Shell scripts for automation of routine tasks
- Dotfiles (.bashrc, .bash_profile, etc.)
- Application-specific configuration files
- System setup documentation for new machines
- Additional guides for software configuration

## Usage

Feel free to clone this repository and adapt it to your own needs. To use:

```bash
# Clone the repository
git clone https://github.com/yourusername/personal-config.git

# Copy configuration files to appropriate locations
# or symbolic link them from your home directory
```

## Tests

To verify that the Fish shell configuration is valid, run:

```bash
./tests/test_config_fish.sh
```

## License

These configurations and scripts are for personal use, but feel free to use or adapt them if you find them helpful.

---

*Created: April 11, 2025*

