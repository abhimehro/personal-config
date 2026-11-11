#!/usr/bin/env python3
"""Wrapper for backward compatibility. Use `reconcile_main.py` directly."""

from .reconcile_main import main


if __name__ == "__main__":
    raise SystemExit(main())