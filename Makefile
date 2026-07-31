.PHONY: setup test test-unit test-integration test-full build-fixture-db rebuild-facts audit frontend-build migrate

PYTHON ?= python
PIP ?= pip

setup:
	$(PIP) install -r requirements-dev.txt 2>/dev/null || $(PIP) install pytest pyyaml ruff mypy
	cd src/frontend && npm ci

migrate:
	$(PYTHON) scripts/ingest/schema_migrate.py --db data/facts.db

build-fixture-db:
	$(PYTHON) scripts/ingest/build_fixture_db.py

test-unit:
	$(PYTHON) -m pytest tests/unit -q

test-integration:
	$(PYTHON) -m pytest tests/integration -q

test:
	$(PYTHON) -m pytest tests/unit tests/integration -q

test-full:
	$(PYTHON) -m pytest -m full_data -q

rebuild-facts:
	@echo "Rebuild production facts via ops playbooks; not run in CI."

audit:
	$(PYTHON) scripts/ingest/ingestion_coverage_lineage.py
	$(PYTHON) scripts/ingest/revenue_reconciliation.py --year 2024-25 || true

frontend-build:
	cd src/frontend && npm ci && npm run lint && npx tsc --noEmit && npm run build
