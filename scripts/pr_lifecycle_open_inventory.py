#!/usr/bin/env python3
"""Fetch and normalize paginated open pull-request inventory."""

from __future__ import annotations

from pr_lifecycle_inventory_checks import check_state  # noqa: F401
from pr_lifecycle_inventory_graphql import list_open_prs  # noqa: F401
from pr_lifecycle_inventory_norm import _normalize_pr  # noqa: F401
