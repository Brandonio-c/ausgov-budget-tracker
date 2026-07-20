"""Fetch raw source files declared in sources.yaml into data/raw/<level>/<id>/.

Discovers the current resource URL for each source via data.gov.au's CKAN API
(package_show), then downloads it. On failure (dead link, WAF challenge, timeout)
the source is skipped with a warning and a fetch_failed sidecar is written -
the run continues and no data is fabricated for that source.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
SOURCES_FILE = Path(__file__).resolve().parent / "sources.yaml"
RAW_DIR = BASE_DIR / "data" / "raw"
CKAN_PACKAGE_SHOW = "https://data.gov.au/data/api/3/action/package_show"
USER_AGENT = "Mozilla/5.0 (compatible; AusGovBudgetTracker/0.1; +https://vibefactory.app/ausgov-budget-tracker)"
TIMEOUT = 30


def resolve_resource_url(source: dict) -> tuple[str, str]:
    """Return (resource_url, resource_name) for a source, resolved live via CKAN."""
    resp = requests.get(
        CKAN_PACKAGE_SHOW,
        params={"id": source["ckan_package_id"]},
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    package = resp.json()["result"]

    if "resource_id" in source:
        for res in package["resources"]:
            if res["id"] == source["resource_id"]:
                return res["url"], res.get("name") or package["title"]
        raise LookupError(f"resource_id {source['resource_id']} not found in package {source['ckan_package_id']}")

    match = source["resource_match"].lower()
    for res in package["resources"]:
        if match in (res.get("name") or "").lower():
            return res["url"], res.get("name") or package["title"]
    raise LookupError(f"no resource matching '{source['resource_match']}' in package {source['ckan_package_id']}")


def fetch_one(source: dict) -> dict:
    dest_dir = RAW_DIR / source["level"] / source["id"]
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / source["raw_filename"]
    meta_file = dest_dir / f"{source['id']}.meta.json"
    retrieved_at = datetime.now(timezone.utc).isoformat()

    meta = {
        "id": source["id"],
        "level": source["level"],
        "jurisdiction": source["jurisdiction"],
        "source_document_name": source["title"],
        "retrieved_at": retrieved_at,
    }

    try:
        resource_url, resource_name = resolve_resource_url(source)
        meta["source_url"] = resource_url
        meta["resource_name"] = resource_name

        r = requests.get(resource_url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        waf_challenge = r.headers.get("x-amzn-waf-action") == "challenge"
        if waf_challenge or r.status_code != 200 or len(r.content) == 0:
            meta["status"] = "fetch_failed"
            meta["http_status"] = r.status_code
            meta["reason"] = "waf_challenge" if waf_challenge else "non_200_or_empty_body"
            print(f"[SKIP] {source['id']}: {meta['reason']} (HTTP {r.status_code}) — {resource_url}")
        else:
            dest_file.write_bytes(r.content)
            meta["status"] = "ok"
            meta["http_status"] = r.status_code
            meta["bytes"] = len(r.content)
            meta["raw_file"] = str(dest_file.relative_to(BASE_DIR))
            print(f"[OK]   {source['id']}: {len(r.content):,} bytes -> {dest_file.relative_to(BASE_DIR)}")
    except (requests.RequestException, LookupError) as exc:
        meta["status"] = "fetch_failed"
        meta["reason"] = f"{type(exc).__name__}: {exc}"
        print(f"[SKIP] {source['id']}: {meta['reason']}")

    meta_file.write_text(json.dumps(meta, indent=2))
    return meta


def main() -> int:
    sources = yaml.safe_load(SOURCES_FILE.read_text())["sources"]
    results = [fetch_one(s) for s in sources]

    ok = sum(1 for r in results if r["status"] == "ok")
    failed = len(results) - ok
    print(f"\n{ok}/{len(results)} sources fetched successfully" + (f", {failed} failed (see .meta.json files)" if failed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
