"""Fail-closed validation for reviewed PR lifecycle source artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pr_lifecycle_validation import validate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "runtime_ledger",
        type=Path,
        help="required fetched runtime ledger from automation/pr-lifecycle-ledger",
    )
    args = parser.parse_args()
    try:
        validate(args.runtime_ledger)
    except (OSError, ValueError, KeyError, IndexError) as exc:
        print(f"PR_LIFECYCLE_INVALID: {exc}", file=sys.stderr)
        return 1
    print("PR_LIFECYCLE_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
