#!/usr/bin/env python3
"""
sync_package.py — regenerate igagent/__init__.py from igagent.py
================================================================
The PyPI package is a byte-identical synced copy of the single-file tool,
never a refactor.  This script copies `igagent.py` over
`igagent/__init__.py` verbatim; `tests/test_package_sync.py` fails the
build when the two drift apart.

Usage:
    python scripts/sync_package.py            # regenerate
    python scripts/sync_package.py --check    # exit 1 if out of sync
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "igagent.py"
TARGET = ROOT / "igagent" / "__init__.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    check = "--check" in sys.argv[1:]
    if not SOURCE.is_file():
        print(f"source missing: {SOURCE}", file=sys.stderr)
        return 1
    if check:
        if not TARGET.is_file():
            print("drift: igagent/__init__.py is missing", file=sys.stderr)
            return 1
        if digest(SOURCE) != digest(TARGET):
            print("drift: igagent/__init__.py differs from igagent.py — "
                  "run `python scripts/sync_package.py`", file=sys.stderr)
            return 1
        print("package in sync")
        return 0
    TARGET.write_bytes(SOURCE.read_bytes())
    print(f"synced {TARGET} (sha256 {digest(TARGET)[:16]}…)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
