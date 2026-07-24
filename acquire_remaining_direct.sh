#!/usr/bin/env bash
# Acquire remaining known-direct handoff sources (orchestrator → browser --url → import).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

IDS_FILE="${1:-remaining_direct_ids.txt}"
URLS_FILE="${2:-remaining_direct_urls.json}"
CONNECT_TIMEOUT="${CONNECT_TIMEOUT:-30}"
READ_TIMEOUT="${READ_TIMEOUT:-180}"
RETRIES="${RETRIES:-2}"
WAIT_SECONDS="${WAIT_SECONDS:-600}"
TIMEOUT_MS="${TIMEOUT_MS:-180000}"

if [[ ! -f "$IDS_FILE" ]]; then
  echo "missing $IDS_FILE" >&2
  exit 1
fi
if [[ ! -f "$URLS_FILE" ]]; then
  echo "missing $URLS_FILE" >&2
  exit 1
fi

mkdir -p data/manual_inbox/_downloads data/.procurement/reports

mapfile -t IDS < <(grep -v '^[[:space:]]*$' "$IDS_FILE" || true)
echo "=== remaining direct acquisition: ${#IDS[@]} sources ==="

for sid in "${IDS[@]}"; do
  if [[ -f "data/raw/federal/${sid}/latest.json" ]] \
    || [[ -f "data/raw/state/${sid}/latest.json" ]] \
    || [[ -f "data/raw/territory/${sid}/latest.json" ]] \
    || [[ -f "data/raw/local/${sid}/latest.json" ]] \
    || [[ -f "data/raw/cross_level/${sid}/latest.json" ]] \
    || find data/raw -type d -name "$sid" -exec test -f "{}/latest.json" \; -print -quit 2>/dev/null | grep -q .; then
    echo "SKIP already on disk: $sid"
    continue
  fi

  echo
  echo "=== $sid ==="
  set +e
  python scripts/procure_sources.py \
    --source-ids "$sid" \
    --connect-timeout "$CONNECT_TIMEOUT" \
    --read-timeout "$READ_TIMEOUT" \
    --retries "$RETRIES"
  orch=$?
  set -e

  if find data/raw -type d -name "$sid" -exec test -f "{}/latest.json" \; -print -quit 2>/dev/null | grep -q .; then
    echo "OK orchestrator: $sid"
    continue
  fi

  url="$(python -c "import json,sys; print(json.load(open(sys.argv[1])).get(sys.argv[2],''))" "$URLS_FILE" "$sid")"
  if [[ -z "$url" ]]; then
    echo "NO URL for browser fallback: $sid" >&2
    continue
  fi

  echo "browser fallback: $sid → $url"
  set +e
  python scripts/procure_browser_session.py \
    --source-id "$sid" \
    --url "$url" \
    --wait-seconds "$WAIT_SECONDS" \
    --timeout-ms "$TIMEOUT_MS"
  set -e
done

echo
echo "=== batch import downloads ==="
python scripts/procure_manual_import_batch.py data/manual_inbox/_downloads || true

echo
echo "=== acquisition queue (need/flaky/candidate) ==="
python scripts/procure_acquisition_queue.py \
  --status need,flaky,candidate,automated \
  --json \
  --write data/.procurement/reports/remaining-after-direct.json || true

echo "done."
