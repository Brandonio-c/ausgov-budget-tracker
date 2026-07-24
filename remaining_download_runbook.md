# Remaining 98 — download runbook

Authoritative item list: `remaining_98_acquisition_plan.csv`

| Class | File | Count (approx) |
|---|---|---|
| Known direct file URL | `remaining_direct_ids.txt` + `remaining_direct_urls.json` | ~26 |
| Landing/archive resolve | `remaining_resolver_ids.txt` | ~43 |
| Dynamic table / collection | `remaining_dynamic_ids.txt` | ~27 |
| No public bulk file | `sa_councils_in_focus`, `wa_mycouncil` | 2 |

## Order

1. **27-ish directs** — `./acquire_remaining_direct.sh`
2. Current P0 PBS + debt tables (browser / upload receiver)
3. Archive PBS resolvers — loop `remaining_resolver_ids.txt`
4. Grants-commission + optional P2
5. Reclassify the two no-bulk rows; do not hammer them

## Browser dependency

```bash
python -m pip install playwright
python -m playwright install chromium
mkdir -p data/manual_inbox/_downloads
```

Use headed Chromium until the persistent profile has cleared WAF challenges. Do not pass `--headless` cold.

## Upload receiver (WAF / AOFM-style)

```bash
python scripts/procure_upload_receiver.py   # Terminal 1
curl http://127.0.0.1:8765/health           # expect {"ok":true}
```

From a cleared browser tab on the real file URL, POST bytes to `http://127.0.0.1:8765/upload?...` then:

```bash
python scripts/procure_manual_import_batch.py data/manual_inbox/_downloads
```

## Verification

```bash
python scripts/procure_acquisition_queue.py \
  --status need,flaky,candidate,automated \
  --json \
  --write data/.procurement/reports/remaining-after-manual.json

find data/raw -type f \( -name '*.pdf' -o -name '*.xlsx' -o -name '*.csv' \) -size -10k -print
grep -RilE 'Just a moment|Access denied|verify you are human|captcha|AWS WAF' \
  data/raw data/manual_inbox/_downloads || true
```
