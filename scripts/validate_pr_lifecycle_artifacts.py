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
    parser.add_argument(
        "--strict-persisted",
        action="store_true",
        help="fail if items still contain in-memory projection fields",
    )
    args = parser.parse_args()
    try:
        stripped = validate(args.runtime_ledger)
    except (OSError, ValueError, KeyError, IndexError) as exc:
        print(f"PR_LIFECYCLE_INVALID: {exc}", file=sys.stderr)
        return 1
    if stripped:
        print(
            f"PR_LIFECYCLE_SANITIZED: stripped {stripped} in-memory item fields",
            file=sys.stderr,
        )
        if args.strict_persisted:
            print(
                "PR_LIFECYCLE_INVALID: persisted projection fields are not schema-legal",
                file=sys.stderr,
            )
            return 1
    print("PR_LIFECYCLE_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
