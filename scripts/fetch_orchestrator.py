#!/usr/bin/env python3
"""Single fetch orchestrator (M11).

Dispatches:
  --mode phase1     → scripts/fetch_sources.py (CKAN Phase 1 trio)
  --mode procure    → scripts/procure_sources.py
  --mode all        → both
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["phase1", "procure", "all"], default="all")
    args, passthrough = parser.parse_known_args(argv)
    rc = 0
    if args.mode in {"phase1", "all"}:
        rc = subprocess.call([sys.executable, str(ROOT / "scripts" / "fetch_sources.py"), *passthrough])
        if rc != 0:
            return rc
    if args.mode in {"procure", "all"}:
        rc = subprocess.call([sys.executable, str(ROOT / "scripts" / "procure_sources.py"), *passthrough])
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
