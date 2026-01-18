# Repository Guidelines

## Project Structure & Module Organization

This repository manages personal system configurations, dotfiles, and automation scripts.

- **`configs/`**: Core configuration files (dotfiles) for shells (`.bashrc`, `.zshrc`, `.config/fish`), editors, and tools.
- **`scripts/`**: General-purpose automation and setup scripts (e.g., `install_all_configs.sh`, `network-mode-manager.sh`).
- **`tests/`**: Unit and regression tests for configurations and scripts.
- **`docs/`**: Detailed documentation for specific modules (SSH, ControlD, macOS).
- **`controld-system/`**: Specialized module for ControlD DNS configuration and management.
- **`windscribe-controld/`**: Integration scripts for Windscribe VPN and ControlD.
- **`Makefile`**: Shortcuts for common maintenance and testing tasks.

## Build, Test, and Development Commands

- **`make control-d-regression`**: Runs the full regression test suite for ControlD and network mode integration.
- **`./scripts/network-mode-verify.sh`**: Verifies the current network state against expected configurations.
- **`./tests/test_ssh_config.sh`**: Validates SSH configuration and connectivity.
- **`npx trunk check`**: Runs code quality checks and linting (if installed).

## Coding Style & Naming Conventions

- **Shell Scripts**:
  - Use `#!/bin/bash` or `#!/usr/bin/env bash` shebangs.
  - Ensure all scripts are executable (`chmod +x`).
  - Use descriptive variable names (`UPPER_CASE` for globals/constants, `snake_case` for locals).
  - Prefer `[[ ]]` over `[ ]` for tests.
- **Configuration Files**:
  - Keep backups of original files (e.g., `.bashrc.bak`) before overwriting.
  - Comment complex logic or custom aliases.

## Testing Guidelines

- **Frameworks**:
  - **Shell**: Custom bash scripts in `tests/` and `scripts/`.
  - **Python**: `pytest` (implied for `.py` files in `tests/`).
- **Running Tests**:
  - Execute specific test scripts directly: `./tests/test_config_fish.sh`.
  - Run regression suites via `make` or dedicated scripts like `scripts/network-mode-regression.sh`.
- **Requirements**:
  - New features or scripts should include a corresponding verification or test script.
  - Ensure `nm-regress` (Network Mode Regression) passes before pushing changes to network logic.

## Commit & Pull Request Guidelines

- **Commit Messages**:
  - **Format**: Use a structured format with a clear summary line, followed by a detailed body.
  - **Style**: "Type: Summary" (e.g., `feat: Add comprehensive SSH configuration suite`, `fix: Resolve DNS verification strictness`).
  - **Body**: Use bullet points to list specific changes.
  - **Attribution**: Include `Co-Authored-By` trailers if AI agents or pairs contributed.
- **Pull Requests**:
  - **Description**: Clearly state *what* changed and *why*.
  - **Verification**: List commands run to verify the changes (e.g., "Ran `nm-regress`, all passed").
  - **Risk**: Mention any potential side effects (e.g., "Requires re-login to apply new shell aliases").
