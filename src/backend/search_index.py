"""Hybrid search over spending FTS + document FTS/embeddings + category embeddings."""

from __future__ import annotations

import math
import os
import re
import sqlite3
import struct
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

DEFAULT_SEARCH_DB = Path(__file__).resolve().parent.parent.parent / "data" / "search.db"
SEARCH_DB_FILE = Path(os.environ.get("SEARCH_DB_PATH", DEFAULT_SEARCH_DB))

Scope = Literal["all", "spending", "documents"]


def search_db_available() -> bool:
    return SEARCH_DB_FILE.exists()


def get_search_connection() -> sqlite3.Connection:
    if not SEARCH_DB_FILE.exists():
        raise FileNotFoundError(
            f"{SEARCH_DB_FILE} not found — run scripts/build_search_index.py"
        )
    conn = sqlite3.connect(f"file:{SEARCH_DB_FILE}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM search_meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def _unpack_f32(blob: bytes, dim: int) -> list[float]:
    return list(struct.unpack(f"{dim}f", blob))


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / math.sqrt(na * nb)


@lru_cache(maxsize=1)
def _embedding_model(model_name: str):
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=model_name)


def embed_query(text: str, model_name: str) -> list[float] | None:
    try:
        model = _embedding_model(model_name)
        for vec in model.embed([text]):
            return list(map(float, vec))
    except Exception:
        return None
    return None


def _fts_query(q: str) -> str:
    """Turn user text into a safe FTS5 query (AND of quoted tokens + prefix)."""
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9'_-]{1,}", q)
    if not tokens:
        return ""
    parts = []
    for t in tokens[:12]:
        safe = t.replace('"', "")
        if len(safe) >= 3:
            parts.append(f'"{safe}" OR {safe}*')
        else:
            parts.append(f'"{safe}"')
    return " AND ".join(f"({p})" for p in parts)


def _query_tokens(q: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[A-Za-z0-9][A-Za-z0-9'_-]{1,}", q) if len(t) >= 2]


def _matched_terms(q: str, text: str) -> list[str]:
    tl = (text or "").lower()
    return [t for t in _query_tokens(q) if t in tl]


def _looks_like_id(segment: str) -> bool:
    s = (segment or "").strip()
    if not s:
        return False
    head = s.split()[0]
    # Agency codes / contract IDs: CED-C, YR-2023-0183, TCCS, CMTEDD-ED
    if re.fullmatch(r"[A-Z]{2,12}(?:-[A-Z0-9]{1,12})*", head):
        return True
    if re.fullmatch(r"[A-Z]{1,6}-\d{2,4}(?:-\d{2,6})+", head):
        return True
    if re.fullmatch(r"\d{4,}", head):
        return True
    return False


def _display_title(node_name: str, q: str, name_snippet: str = "") -> str:
    """Human title: prefer the path segment that matched the query; drop leading IDs."""
    parts = [p.strip() for p in (node_name or "").split(" / ") if p.strip()]
    tokens = _query_tokens(q)

    # Prefer FTS snippet when it marks a match
    if name_snippet and "«" in name_snippet:
        # If snippet is mid-string, still try to pick the best full segment
        for part in reversed(parts):
            pl = part.lower()
            if any(t in pl for t in tokens):
                return part
        cleaned = re.sub(r"[«»]", "", name_snippet).strip(" …")
        if cleaned:
            return cleaned

    for part in reversed(parts):
        pl = part.lower()
        if any(t in pl for t in tokens):
            return part

    if len(parts) >= 2 and _looks_like_id(parts[0]):
        return " / ".join(parts[1:])
    return node_name or "Spending item"


def _highlight_plain(text: str, q: str) -> str:
    """Wrap matched query tokens with « » for the UI highlighter."""
    if not text:
        return text
    tokens = sorted(set(_query_tokens(q)), key=len, reverse=True)
    if not tokens:
        return text
    pattern = re.compile(
        "(" + "|".join(re.escape(t) for t in tokens) + ")",
        re.IGNORECASE,
    )
    return pattern.sub(lambda m: f"«{m.group(0)}»", text)


def _app_path(path: str, params: dict[str, str]) -> str:
    """Build an in-app href with trailing slash before the query string."""
    from urllib.parse import urlencode

    base = path if path.endswith("/") else f"{path}/"
    qs = urlencode({k: v for k, v in params.items() if v})
    return f"{base}?{qs}" if qs else base


def _mode_for_group(group: str | None) -> str | None:
    if not group:
        return None
    if group == "actual_expense":
        return "actuals"
    if group in {"budget_estimate", "estimated_actual", "budget_expense"}:
        return "budget"
    if group == "gfs_liability":
        return "debt"
    if group in {"gfs_revenue", "tax_revenue"}:
        return "revenue"
    if group == "gdp":
        return "gdp"
    return None


def search_spending_fts(
    conn: sqlite3.Connection,
    q: str,
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    fts_q = _fts_query(q)
    if not fts_q:
        return []
    try:
        rows = conn.execute(
            """
            SELECT
                fact_id, node_name, source_title, jurisdiction, level,
                financial_year, measure_type, accounting_basis, estimate_status,
                amount_aud, compatibility_group,
                snippet(spending_fts, 1, '«', '»', '…', 16) AS name_snippet,
                snippet(spending_fts, 2, '«', '»', '…', 12) AS title_snippet,
                bm25(spending_fts) AS rank
            FROM spending_fts
            WHERE spending_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts_q, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        return []

    out = []
    for r in rows:
        bm = float(r["rank"] or 0)
        score = 1.0 / (1.0 + abs(bm))
        mode = _mode_for_group(r["compatibility_group"])
        node_name = r["node_name"] or ""
        name_snip = r["name_snippet"] or ""
        title_snip = r["title_snippet"] or ""
        display = _display_title(node_name, q, name_snip)
        snippet = name_snip if "«" in name_snip else (title_snip if "«" in title_snip else display)
        out.append(
            {
                "kind": "spending",
                "score": score,
                "method": "fts",
                "fact_id": int(r["fact_id"]),
                "node_name": node_name,
                "display_title": display,
                "snippet": snippet,
                "matched_terms": _matched_terms(q, node_name),
                "source_title": r["source_title"],
                "jurisdiction": r["jurisdiction"],
                "level": r["level"],
                "financial_year": r["financial_year"],
                "measure_type": r["measure_type"],
                "accounting_basis": r["accounting_basis"],
                "estimate_status": r["estimate_status"],
                "amount_aud": float(r["amount_aud"] or 0),
                "mode": mode,
                "href": _spending_href(
                    mode=mode,
                    level=r["level"],
                    year=r["financial_year"],
                    fact_id=int(r["fact_id"]),
                    node_name=node_name,
                    group=r["compatibility_group"],
                ),
            }
        )
    return out


def search_spending_semantic(
    conn: sqlite3.Connection,
    q: str,
    *,
    limit: int = 12,
) -> list[dict[str, Any]]:
    model_name = _meta(conn, "embed_model")
    if not model_name or _meta(conn, "embeddings") != "ready":
        return []
    qvec = embed_query(q, model_name)
    if not qvec:
        return []

    rows = conn.execute(
        """
        SELECT v.id, v.label, v.sample_fact_id, v.level, v.amount_aud,
               e.dim, e.vector
        FROM category_vocab v
        JOIN category_embeddings e ON e.vocab_id = v.id
        """
    ).fetchall()
    scored: list[tuple[float, sqlite3.Row]] = []
    for r in rows:
        vec = _unpack_f32(r["vector"], int(r["dim"]))
        scored.append((_cosine(qvec, vec), r))
    scored.sort(key=lambda x: x[0], reverse=True)

    out = []
    for score, r in scored[:limit]:
        if score < 0.35:
            continue
        fact_id = int(r["sample_fact_id"]) if r["sample_fact_id"] is not None else None
        # Enrich from spending_fts if possible
        detail = None
        if fact_id is not None:
            detail = conn.execute(
                """
                SELECT fact_id, node_name, source_title, jurisdiction, level,
                       financial_year, measure_type, accounting_basis, estimate_status,
                       amount_aud, compatibility_group
                FROM spending_fts WHERE fact_id = ? LIMIT 1
                """,
                (fact_id,),
            ).fetchone()
        if detail:
            mode = _mode_for_group(detail["compatibility_group"])
            node_name = detail["node_name"] or r["label"]
            display = _display_title(node_name, q) or r["label"]
            out.append(
                {
                    "kind": "spending",
                    "score": float(score),
                    "method": "embedding",
                    "fact_id": int(detail["fact_id"]),
                    "node_name": node_name,
                    "display_title": display,
                    "snippet": _highlight_plain(display, q),
                    "matched_label": r["label"],
                    "matched_terms": _matched_terms(q, node_name),
                    "source_title": detail["source_title"],
                    "jurisdiction": detail["jurisdiction"],
                    "level": detail["level"],
                    "financial_year": detail["financial_year"],
                    "measure_type": detail["measure_type"],
                    "accounting_basis": detail["accounting_basis"],
                    "estimate_status": detail["estimate_status"],
                    "amount_aud": float(detail["amount_aud"] or 0),
                    "mode": mode,
                    "href": _spending_href(
                        mode=mode,
                        level=detail["level"],
                        year=detail["financial_year"],
                        fact_id=int(detail["fact_id"]),
                        node_name=node_name,
                        group=detail["compatibility_group"],
                    ),
                }
            )
        else:
            label = r["label"]
            out.append(
                {
                    "kind": "spending",
                    "score": float(score),
                    "method": "embedding",
                    "fact_id": fact_id,
                    "node_name": label,
                    "display_title": label,
                    "snippet": _highlight_plain(label, q),
                    "matched_label": label,
                    "matched_terms": _matched_terms(q, label),
                    "level": r["level"],
                    "amount_aud": float(r["amount_aud"] or 0),
                    "mode": "actuals",
                    "href": _spending_href(
                        mode="actuals",
                        level=r["level"] or "federal",
                        year=None,
                        fact_id=fact_id,
                        node_name=label,
                        group=None,
                    ),
                }
            )
    return out


def search_documents_fts(conn: sqlite3.Connection, q: str, *, limit: int = 12) -> list[dict[str, Any]]:
    fts_q = _fts_query(q)
    if not fts_q:
        return []
    try:
        rows = conn.execute(
            """
            SELECT
                c.id AS chunk_id,
                c.source_document_id,
                c.source_key,
                c.title,
                c.publisher,
                c.jurisdiction,
                c.government_level,
                c.landing_url,
                c.local_path,
                c.chunk_index,
                snippet(doc_fts, 4, '«', '»', '…', 24) AS snippet,
                bm25(doc_fts) AS rank
            FROM doc_fts
            JOIN doc_chunks c ON c.id = doc_fts.chunk_id
            WHERE doc_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts_q, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        return []

    return [_doc_hit(r, score=1.0 / (1.0 + abs(float(r["rank"] or 0))), method="fts", q=q) for r in rows]


def search_documents_semantic(
    conn: sqlite3.Connection,
    q: str,
    *,
    limit: int = 12,
) -> list[dict[str, Any]]:
    model_name = _meta(conn, "embed_model")
    if not model_name or _meta(conn, "embeddings") != "ready":
        return []
    qvec = embed_query(q, model_name)
    if not qvec:
        return []

    rows = conn.execute(
        """
        SELECT
            c.id AS chunk_id,
            c.source_document_id,
            c.source_key,
            c.title,
            c.publisher,
            c.jurisdiction,
            c.government_level,
            c.landing_url,
            c.local_path,
            c.chunk_index,
            substr(c.chunk_text, 1, 220) AS snippet,
            e.dim, e.vector
        FROM doc_chunks c
        JOIN doc_embeddings e ON e.chunk_id = c.id
        """
    ).fetchall()
    scored: list[tuple[float, sqlite3.Row]] = []
    for r in rows:
        vec = _unpack_f32(r["vector"], int(r["dim"]))
        scored.append((_cosine(qvec, vec), r))
    scored.sort(key=lambda x: x[0], reverse=True)

    out = []
    for score, r in scored[:limit]:
        if score < 0.28:
            continue
        out.append(_doc_hit(r, score=float(score), method="embedding", q=q))
    return out


def _doc_hit(r: sqlite3.Row, *, score: float, method: str, q: str = "") -> dict[str, Any]:
    source_key = r["source_key"]
    title = r["title"] or source_key
    snippet = r["snippet"] or ""
    if q and "«" not in snippet:
        snippet = _highlight_plain(snippet or title, q)
    return {
        "kind": "document",
        "score": score,
        "method": method,
        "source_document_id": int(r["source_document_id"]),
        "source_key": source_key,
        "title": title,
        "display_title": title,
        "publisher": r["publisher"],
        "jurisdiction": r["jurisdiction"],
        "government_level": r["government_level"],
        "landing_url": r["landing_url"],
        "local_path": r["local_path"],
        "chunk_index": int(r["chunk_index"]),
        "snippet": snippet,
        "matched_terms": _matched_terms(q, f"{title} {snippet}"),
        "href": _app_path(
            "/search",
            {
                "tab": "documents",
                "q": q or title,
                "doc": source_key,
            },
        ),
    }


def _q_enc(s: str) -> str:
    from urllib.parse import quote

    return quote(s)


def _spending_href(
    *,
    mode: str | None,
    level: str | None,
    year: str | None,
    fact_id: int | None,
    node_name: str | None,
    group: str | None,
) -> str:
    # Commitment / contract → contracts explorer
    if group == "commitment":
        return _app_path(
            "/explorers/contracts",
            {
                "year": year or "",
                "fact": str(fact_id or ""),
                "q": node_name or "",
            },
        )

    params: dict[str, str] = {"mode": mode or "actuals"}
    if level:
        params["level"] = level
    if year:
        params["year"] = year
    if fact_id is not None:
        params["fact"] = str(fact_id)
    if node_name:
        params["highlight"] = node_name
    return _app_path("/", params)


def _rrf_merge(
    *lists: list[dict[str, Any]],
    key_fn,
    k: int = 60,
    limit: int = 30,
) -> list[dict[str, Any]]:
    scores: dict[Any, float] = {}
    best: dict[Any, dict[str, Any]] = {}

    def prefer(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
        # Keep FTS highlight/snippet when present — raw embedding scores are larger
        # and would otherwise wipe the matched-term display.
        a_hl = 1 if "«" in str(a.get("snippet") or "") else 0
        b_hl = 1 if "«" in str(b.get("snippet") or "") else 0
        if a_hl != b_hl:
            return a if a_hl > b_hl else b
        if a.get("display_title") and not b.get("display_title"):
            return a
        if b.get("display_title") and not a.get("display_title"):
            return b
        return a if float(a.get("score") or 0) >= float(b.get("score") or 0) else b

    for results in lists:
        for rank, item in enumerate(results):
            key = key_fn(item)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            prev = best.get(key)
            best[key] = item if prev is None else prefer(prev, item)
    merged = []
    for key, rrf in sorted(scores.items(), key=lambda x: -x[1]):
        item = dict(best[key])
        item["score"] = rrf
        item["method"] = "hybrid"
        merged.append(item)
        if len(merged) >= limit:
            break
    return merged


def unified_search(
    q: str,
    *,
    scope: Scope = "all",
    limit: int = 20,
) -> dict[str, Any]:
    q_clean = (q or "").strip()
    if len(q_clean) < 2:
        raise ValueError("q must be at least 2 characters")

    if not search_db_available():
        return {
            "q": q_clean,
            "scope": scope,
            "index_ready": False,
            "spending": [],
            "documents": [],
            "note": "Search index not built. Run scripts/build_search_index.py",
        }

    conn = get_search_connection()
    try:
        spending: list[dict[str, Any]] = []
        documents: list[dict[str, Any]] = []

        if scope in ("all", "spending"):
            fts = search_spending_fts(conn, q_clean, limit=limit)
            sem = search_spending_semantic(conn, q_clean, limit=max(8, limit // 2))
            spending = _rrf_merge(
                fts,
                sem,
                key_fn=lambda x: ("s", x.get("fact_id"), x.get("node_name")),
                limit=limit,
            )

        if scope in ("all", "documents"):
            d_fts = search_documents_fts(conn, q_clean, limit=limit)
            d_sem = search_documents_semantic(conn, q_clean, limit=max(8, limit // 2))
            documents = _rrf_merge(
                d_fts,
                d_sem,
                key_fn=lambda x: ("d", x.get("source_key"), x.get("chunk_index")),
                limit=limit,
            )

        return {
            "q": q_clean,
            "scope": scope,
            "index_ready": True,
            "embed_model": _meta(conn, "embed_model"),
            "spending": spending,
            "documents": documents,
        }
    finally:
        conn.close()
