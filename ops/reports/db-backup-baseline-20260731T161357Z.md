# Production database backup + baseline — 2026-07-31T16:13:57Z

## Backend write-lock check (before deciding whether to stop anything)

Two local services were found running against this host:
- `uvicorn services.controller.app:app` (port 8001, unrelated service, root, since Jun 29)
- `uvicorn backend.main:app --workers 2` (port 8010, root, since Jul 25) — this is the
  AusGov Budget Tracker production API.

Checked `src/backend/{db.py,facts_db.py,search_index.py}` directly: every connection to
`facts.db` opens with `sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True)` — read-only at
the SQLite URI level. `grep` across `src/backend/` for `INSERT INTO|UPDATE |DELETE FROM|
executemany|.commit()` found zero matches outside `Dockerfile` (a false-positive hit on an
apt-get line). **The API holds no write lock and never writes to facts.db.**

Given that, stopping the live production backend was not necessary and was not done — doing
so would have caused a real outage on a service serving public traffic for no safety benefit,
since SQLite's backup API is safe against concurrent read-only connections regardless.

## Backup

- Method: `scripts/ops/backup_facts_db.py`, using `sqlite3.Connection.backup()` (the SQLite
  backup API - a consistent page-level copy, not a raw file copy taken while the file might be
  mid-write).
- Backup path (outside the Git-tracked repo tree): `/home/vibe-server/backups/ausgov-budget-tracker/facts-20260731T161357Z.db`
- Report: `/home/vibe-server/backups/ausgov-budget-tracker/facts-20260731T161357Z.backup-report.json`
- Source DB SHA-256: `ec67f7505199bcd00e62c1d8669d5ab037f4e9bc169ce2ccf0a7b8dc204680e4`
- Backup file SHA-256: `d997a80a1749f812b9416f0267a99be73ad8149f9a8c8d5935e1d751bd83cf34` (differs from source -
  expected and verified benign, see below)
- Backup size: 633,044,992 bytes (identical to source)

**Why the SHA-256 differs but the backup is still correct:** `journal_mode` is `delete` (not
WAL), so this isn't a WAL-checkpoint artifact. `sqlite3`'s `.backup()` performs a logical,
page-by-page copy into a new file rather than a byte-for-byte copy, so internal bookkeeping
(freelist layout, change-counter fields) can legitimately differ between source and backup
while the *content* is identical. Verified directly rather than assumed:
- `PRAGMA integrity_check` on the backup: `ok`
- `SELECT COUNT(*) FROM facts` on the backup: `324984` (matches source)
- `SELECT COUNT(*) FROM source_documents` on the backup: `127` (matches source)

## Baseline counts (recorded before any Task 3+ ingestion work)

| Metric | Count |
|---|---:|
| `facts` | 324,984 |
| `source_documents` | 127 |
| `nodes` | 232,518 |
| `node_edges` | 0 |
| `lineage_edges` | 0 |
| `facts_pending_attribution` (quarantine) | 15 |

`node_edges` and `lineage_edges` are genuinely 0 in the current production database - not a
query error (both tables exist and are queried successfully with `mode=ro`). Worth revisiting
once hierarchy-linking work (Task 3.5) begins, since a dashboard with node/fact data but zero
edges implies hierarchy traversal is reconstructed some other way (e.g. computed from
`fact_nodes`/`canonical_dataset_id`/`view_family` at query time) rather than via these tables -
flagging for Task 8's dashboard audit rather than assuming it's a bug here.

## Reusable tooling added

`scripts/ops/backup_facts_db.py` - safe to re-run before any future ingestion session. Stores
backups + a JSON report (counts, hashes, paths) under `/home/vibe-server/backups/ausgov-budget-tracker/`,
outside any Git-tracked path.
