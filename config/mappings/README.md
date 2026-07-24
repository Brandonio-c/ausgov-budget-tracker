# Mapping YAML specification

Per-source (or shared-template) mappings drive DuckDB ETL into `data/facts.db`.

## Required top-level keys

| Key | Type | Purpose |
|---|---|---|
| `source_id` | string | Stable registry id / `source_documents.source_key` |
| `measure_type` | string | FK → `measure_definitions` |
| `accounting_basis` | string | cash / accrual / gfs / … |
| `estimate_status` | string | budget / actual / … |
| `period_granularity` | string | financial_year / month / … |
| `government_level` | string | federal / state / territory / local / … |
| `jurisdiction` | string | e.g. Commonwealth, SA, VIC |
| `publisher` | string | Publisher name |
| `title` | string | Document title |
| `source_family` | string | Family tag |
| `input` | object | Path + format |
| `columns` | object | Logical → physical column map |
| `attribution` | object | Citation fields (Gate 6) |

## `input`

```yaml
input:
  path: relative/or/absolute/file.csv
  format: csv   # csv | parquet | excel
  sheet: null   # excel only
```

## `columns`

Map logical fields to source columns (or literals with `literal:` prefix):

```yaml
columns:
  financial_year: fy
  amount_aud: amount
  node_name: category
  locator: cell_ref
```

## `attribution`

Gate 6 requires all of:

- `landing_url` (static or column)
- `original_resource_url` (static or column)
- `cached_copy_path` (path to held file; becomes cached URL in API)
- locator from `columns.locator` (non-empty per row)
- retrieval metadata (`sha256`, `retrieved_at`) computed at load time from the cached file

```yaml
attribution:
  landing_url: https://example.gov.au/page
  original_resource_url: https://example.gov.au/file.csv
  # OR per-row:
  # landing_url_column: landing_url
  # original_resource_url_column: resource_url
  cached_copy_path: tests/fixtures/ingest/synthetic_demo.csv
```

## `fact_key`

Default: `{source_id}|{financial_year}|{node_name}|{measure_type}|{estimate_status}`  
Override with `fact_key_template` using `{field}` placeholders.

## Shared templates

Use `extends: templates/abs_gfs.yaml` to inherit a base mapping and override `source_id` / paths.
