#!/usr/bin/env python3
"""Assist browser-based acquisition: write URL manifests + import helper.

After a human (or Cursor browser) clears a WAF gate and lists file URLs, drop a
JSON list into data/manual_inbox/_downloads/<source_id>_urls.json and either:

  1. Download on a machine that can reach the host (browser session / local), OR
  2. Use this script's --from-urls-file with an already-accessible network path.

This does not bypass WAF; it only stages provenance for the import pipeline.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
DOWNLOADS = REPO_ROOT / "data" / "manual_inbox" / "_downloads"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--write-manifest", type=Path, help="path to JSON list of {url,name?} or URL strings")
    parser.add_argument("--print-curl", action="store_true", help="print curl commands for the manifest")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    if args.write_manifest:
        payload = json.loads(args.write_manifest.read_text(encoding="utf-8"))
        dest = DOWNLOADS / f"{args.source_id}_urls.json"
        dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {dest.relative_to(REPO_ROOT)}")
        if args.print_curl:
            items = payload.get("urls", payload) if isinstance(payload, dict) else payload
            for item in items:
                url = item if isinstance(item, str) else item.get("url")
                if not url:
                    continue
                name = Path(urlparse(url).path).name or "download.bin"
                print(f"curl -L -o '{args.source_id}__{name}' '{url}'")
                print(f"echo '{url}' > '{args.source_id}__{name}.url'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
