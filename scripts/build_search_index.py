#!/usr/bin/env python3
"""Build hybrid search index: FTS5 (spending + docs) + FastEmbed vectors for document chunks.

Output: data/search.db (separate from read-only facts.db).
Re-run after ingesting new sources.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sqlite3
import struct
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_FACTS = REPO / "data" / "facts.db"
DEFAULT_OUT = REPO / "data" / "search.db"
DEFAULT_RAW = REPO / "data" / "raw"

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
CHUNK_CHARS = 1200
CHUNK_OVERLAP = 150
MAX_PDF_CHARS = 400_000
MAX_CHUNKS_PER_DOC = 80
CATEGORY_VOCAB_LIMIT = 8_000


def _connect(path: Path, *, rw: bool) -> sqlite3.Connection:
    if rw:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    else:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _pack_f32(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def _chunk_text(text: str, size: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return []
    if len(text) <= size:
        return [text]
    out: list[str] = []
    i = 0
    while i < len(text) and len(out) < MAX_CHUNKS_PER_DOC:
        out.append(text[i : i + size])
        i += max(1, size - overlap)
    return out


def _extract_pdf(path: Path) -> str:
    try:
        result = subprocess.run(
            ["pdftotext", "-q", "-layout", str(path), "-"],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout[:MAX_PDF_CHARS]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        parts = []
        for page in reader.pages[:80]:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)[:MAX_PDF_CHARS]
    except Exception:
        return ""


def _extract_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:MAX_PDF_CHARS]
    except Exception:
        return ""


def _extract_xlsx_labels(path: Path) -> str:
    try:
        import openpyxl

        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        labels: list[str] = [f"Workbook {path.name}"]
        for sheet in wb.worksheets[:12]:
            labels.append(f"Sheet {sheet.title}")
            for i, row in enumerate(sheet.iter_rows(max_row=30, max_col=8, values_only=True)):
                cells = [str(c).strip() for c in row if c is not None and str(c).strip()]
                if cells:
                    labels.append(" | ".join(cells))
                if i > 25:
                    break
        wb.close()
        return "\n".join(labels)[:MAX_PDF_CHARS]
    except Exception:
        return f"Spreadsheet {path.name}"


def extract_file_text(path: Path) -> str:
    if not path.is_file():
        return ""
    suf = path.suffix.lower()
    if suf == ".pdf":
        return _extract_pdf(path)
    if suf in {".txt", ".md", ".csv", ".json", ".jsonl", ".xml", ".html", ".htm"}:
        return _extract_text_file(path)
    if suf in {".xlsx", ".xlsm"}:
        return _extract_xlsx_labels(path)
    return ""


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS spending_fts;
        DROP TABLE IF EXISTS category_vocab;
        DROP TABLE IF EXISTS category_embeddings;
        DROP TABLE IF EXISTS doc_chunks;
        DROP TABLE IF EXISTS doc_fts;
        DROP TABLE IF EXISTS doc_embeddings;
        DROP TABLE IF EXISTS search_meta;

        CREATE TABLE search_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE VIRTUAL TABLE spending_fts USING fts5(
            fact_id UNINDEXED,
            node_name,
            source_title,
            jurisdiction UNINDEXED,
            level UNINDEXED,
            financial_year UNINDEXED,
            measure_type UNINDEXED,
            accounting_basis UNINDEXED,
            estimate_status UNINDEXED,
            amount_aud UNINDEXED,
            compatibility_group UNINDEXED,
            tokenize = 'porter unicode61'
        );

        CREATE TABLE category_vocab (
            id INTEGER PRIMARY KEY,
            label TEXT NOT NULL UNIQUE,
            sample_fact_id INTEGER,
            level TEXT,
            amount_aud REAL
        );

        CREATE TABLE category_embeddings (
            vocab_id INTEGER PRIMARY KEY REFERENCES category_vocab(id),
            dim INTEGER NOT NULL,
            vector BLOB NOT NULL
        );

        CREATE TABLE doc_chunks (
            id INTEGER PRIMARY KEY,
            source_document_id INTEGER NOT NULL,
            source_key TEXT NOT NULL,
            title TEXT NOT NULL,
            publisher TEXT,
            jurisdiction TEXT,
            government_level TEXT,
            landing_url TEXT,
            local_path TEXT,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            content_sha TEXT NOT NULL
        );

        CREATE VIRTUAL TABLE doc_fts USING fts5(
            chunk_id UNINDEXED,
            source_key,
            title,
            publisher,
            chunk_text,
            tokenize = 'porter unicode61'
        );

        CREATE TABLE doc_embeddings (
            chunk_id INTEGER PRIMARY KEY REFERENCES doc_chunks(id),
            dim INTEGER NOT NULL,
            vector BLOB NOT NULL
        );
        """
    )


def build_spending_fts(facts: sqlite3.Connection, out: sqlite3.Connection) -> int:
    rows = facts.execute(
        """
        SELECT
            f.id AS fact_id,
            n.name AS node_name,
            d.title AS source_title,
            d.jurisdiction,
            CASE d.government_level WHEN 'national' THEN 'federal'
                ELSE d.government_level END AS level,
            f.financial_year,
            f.measure_type,
            f.accounting_basis,
            f.estimate_status,
            f.amount_aud,
            m.compatibility_group
        FROM facts f
        JOIN measure_definitions m ON m.measure_type = f.measure_type
        JOIN source_documents d ON d.id = f.source_document_id
        JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
        JOIN nodes n ON n.id = fn.node_id
        """
    )
    batch = []
    n = 0
    for r in rows:
        batch.append(
            (
                int(r["fact_id"]),
                r["node_name"] or "",
                r["source_title"] or "",
                r["jurisdiction"] or "",
                r["level"] or "",
                r["financial_year"] or "",
                r["measure_type"] or "",
                r["accounting_basis"] or "",
                r["estimate_status"] or "",
                float(r["amount_aud"] or 0),
                r["compatibility_group"] or "",
            )
        )
        if len(batch) >= 5000:
            out.executemany(
                """
                INSERT INTO spending_fts(
                    fact_id, node_name, source_title, jurisdiction, level,
                    financial_year, measure_type, accounting_basis, estimate_status,
                    amount_aud, compatibility_group
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                batch,
            )
            n += len(batch)
            batch.clear()
    if batch:
        out.executemany(
            """
            INSERT INTO spending_fts(
                fact_id, node_name, source_title, jurisdiction, level,
                financial_year, measure_type, accounting_basis, estimate_status,
                amount_aud, compatibility_group
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            batch,
        )
        n += len(batch)
    out.commit()
    return n


def build_category_vocab(facts: sqlite3.Connection, out: sqlite3.Connection) -> list[tuple[int, str]]:
    """Compact vocabulary of high-value path labels for semantic spending search."""
    rows = facts.execute(
        """
        SELECT
            n.name AS node_name,
            f.id AS fact_id,
            CASE d.government_level WHEN 'national' THEN 'federal'
                ELSE d.government_level END AS level,
            SUM(f.amount_aud) AS amount_aud
        FROM facts f
        JOIN source_documents d ON d.id = f.source_document_id
        JOIN fact_nodes fn ON fn.fact_id = f.id AND fn.dimension_role = 'primary'
        JOIN nodes n ON n.id = fn.node_id
        GROUP BY n.name
        ORDER BY amount_aud DESC
        LIMIT ?
        """,
        (CATEGORY_VOCAB_LIMIT,),
    ).fetchall()

    labels: dict[str, tuple[int, str, float]] = {}
    for r in rows:
        name = (r["node_name"] or "").strip()
        if not name:
            continue
        # Prefer short path segments for semantic matching ("Health", "Aged care")
        parts = [p.strip() for p in name.split(" / ") if p.strip()]
        candidates = parts[-2:] if parts else [name]
        for label in candidates:
            if len(label) < 3:
                continue
            prev = labels.get(label)
            amount = float(r["amount_aud"] or 0)
            if prev is None or amount > prev[2]:
                labels[label] = (int(r["fact_id"]), r["level"] or "", amount)

    vocab_rows = []
    for label, (fact_id, level, amount) in sorted(labels.items(), key=lambda x: -x[1][2]):
        vocab_rows.append((label, fact_id, level, amount))

    out.executemany(
        """
        INSERT INTO category_vocab(label, sample_fact_id, level, amount_aud)
        VALUES (?,?,?,?)
        """,
        vocab_rows,
    )
    out.commit()
    return [
        (int(r["id"]), r["label"])
        for r in out.execute("SELECT id, label FROM category_vocab ORDER BY id").fetchall()
    ]


def build_doc_chunks(facts: sqlite3.Connection, out: sqlite3.Connection, raw_root: Path) -> list[tuple[int, str]]:
    docs = facts.execute(
        """
        SELECT
            d.id AS source_document_id,
            d.source_key,
            d.title,
            d.publisher,
            d.jurisdiction,
            d.government_level,
            d.landing_url,
            r.local_path
        FROM source_documents d
        LEFT JOIN source_retrievals r ON r.id = (
            SELECT r2.id FROM source_retrievals r2
            WHERE r2.source_document_id = d.id AND r2.retrieval_status = 'ok'
            ORDER BY r2.retrieved_at DESC LIMIT 1
        )
        """
    ).fetchall()

    chunk_rows = []
    for d in docs:
        local = d["local_path"]
        path = Path(local) if local else None
        if path and not path.is_absolute():
            path = (REPO / path).resolve()
        text_parts = [
            d["title"] or "",
            d["publisher"] or "",
            d["source_key"] or "",
            d["landing_url"] or "",
        ]
        extracted = extract_file_text(path) if path else ""
        if extracted:
            text_parts.append(extracted)
        full = "\n".join(p for p in text_parts if p)
        chunks = _chunk_text(full) or [d["title"] or d["source_key"] or "document"]
        for i, chunk in enumerate(chunks):
            sha = hashlib.sha256(chunk.encode("utf-8")).hexdigest()[:16]
            chunk_rows.append(
                (
                    int(d["source_document_id"]),
                    d["source_key"],
                    d["title"] or d["source_key"],
                    d["publisher"],
                    d["jurisdiction"],
                    d["government_level"],
                    d["landing_url"],
                    str(path) if path else None,
                    i,
                    chunk,
                    sha,
                )
            )

    out.executemany(
        """
        INSERT INTO doc_chunks(
            source_document_id, source_key, title, publisher, jurisdiction,
            government_level, landing_url, local_path, chunk_index, chunk_text, content_sha
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """,
        chunk_rows,
    )
    for r in out.execute("SELECT id, source_key, title, publisher, chunk_text FROM doc_chunks").fetchall():
        out.execute(
            """
            INSERT INTO doc_fts(chunk_id, source_key, title, publisher, chunk_text)
            VALUES (?,?,?,?,?)
            """,
            (r["id"], r["source_key"], r["title"], r["publisher"] or "", r["chunk_text"]),
        )
    out.commit()
    return [(int(r["id"]), r["chunk_text"]) for r in out.execute("SELECT id, chunk_text FROM doc_chunks").fetchall()]


def embed_texts(texts: list[str], model_name: str) -> list[list[float]]:
    from fastembed import TextEmbedding

    model = TextEmbedding(model_name=model_name)
    return [list(map(float, v)) for v in model.embed(texts)]


def store_embeddings(
    out: sqlite3.Connection,
    table: str,
    id_col: str,
    pairs: list[tuple[int, list[float]]],
) -> None:
    rows = [(i, len(v), _pack_f32(v)) for i, v in pairs]
    out.executemany(
        f"INSERT INTO {table}({id_col}, dim, vector) VALUES (?,?,?)",
        rows,
    )
    out.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facts-db", type=Path, default=DEFAULT_FACTS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--model", default=EMBED_MODEL)
    parser.add_argument("--skip-embeddings", action="store_true")
    args = parser.parse_args()

    if not args.facts_db.exists():
        print(f"facts db missing: {args.facts_db}", file=sys.stderr)
        return 1

    print(f"Building search index → {args.out}")
    facts = _connect(args.facts_db, rw=False)
    if args.out.exists():
        args.out.unlink()
    out = _connect(args.out, rw=True)
    init_schema(out)

    n_spend = build_spending_fts(facts, out)
    print(f"  spending FTS rows: {n_spend}")

    vocab = build_category_vocab(facts, out)
    print(f"  category vocab: {len(vocab)}")

    chunks = build_doc_chunks(facts, out, args.raw_root)
    print(f"  document chunks: {len(chunks)}")

    out.execute(
        "INSERT INTO search_meta(key, value) VALUES (?, ?)",
        ("embed_model", args.model),
    )
    out.execute(
        "INSERT INTO search_meta(key, value) VALUES (?, ?)",
        ("built_from_facts", str(args.facts_db)),
    )

    if not args.skip_embeddings:
        print(f"  embedding with {args.model} …")
        cat_vecs = embed_texts([t for _, t in vocab], args.model) if vocab else []
        store_embeddings(
            out,
            "category_embeddings",
            "vocab_id",
            [(vid, vec) for (vid, _), vec in zip(vocab, cat_vecs)],
        )
        print(f"  category embeddings: {len(cat_vecs)}")

        doc_vecs = embed_texts([t for _, t in chunks], args.model) if chunks else []
        store_embeddings(
            out,
            "doc_embeddings",
            "chunk_id",
            [(cid, vec) for (cid, _), vec in zip(chunks, doc_vecs)],
        )
        print(f"  document embeddings: {len(doc_vecs)}")
        out.execute(
            "INSERT INTO search_meta(key, value) VALUES (?, ?)",
            ("embeddings", "ready"),
        )
    else:
        out.execute(
            "INSERT INTO search_meta(key, value) VALUES (?, ?)",
            ("embeddings", "skipped"),
        )

    out.commit()
    facts.close()
    out.close()
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
