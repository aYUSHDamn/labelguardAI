"""SQLite persistence (plain sqlite3, one file, no ORM)."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator, Optional

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS household (
    id            INTEGER PRIMARY KEY CHECK (id = 1),   -- single household for the demo
    raw_text      TEXT,
    profile_json  TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

-- Extraction cache: repeat scans of the same image / barcode cost zero tokens.
CREATE TABLE IF NOT EXISTS extraction_cache (
    cache_key        TEXT PRIMARY KEY,                  -- 'img:<sha256>' or 'bar:<barcode>'
    extraction_json  TEXT NOT NULL,
    source           TEXT NOT NULL,                     -- gemini_vision | open_food_facts | manual
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scans (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    image_hash       TEXT,
    barcode          TEXT,
    product_name     TEXT,
    brand            TEXT,
    category         TEXT,
    score            INTEGER NOT NULL,                  -- profile-independent health score
    extraction_json  TEXT NOT NULL,
    source           TEXT NOT NULL,
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS intake_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id     INTEGER NOT NULL REFERENCES scans(id),
    member      TEXT NOT NULL,
    grams       REAL NOT NULL,
    sugar_g     REAL,
    sodium_mg   REAL,
    sat_fat_g   REAL,
    logged_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alt_feedback (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id       INTEGER,
    product_code  TEXT NOT NULL,
    product_name  TEXT,
    brand         TEXT,
    vote          INTEGER NOT NULL,                     -- +1 / -1
    reason        TEXT,
    created_at    TEXT NOT NULL
);

-- Generic key/value cache for LLM text outputs (profile parse, explanations).
CREATE TABLE IF NOT EXISTS llm_cache (
    cache_key   TEXT PRIMARY KEY,
    value_json  TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

-- Open Food Facts HTTP response cache (respects their rate limits).
CREATE TABLE IF NOT EXISTS off_cache (
    cache_key      TEXT PRIMARY KEY,
    response_json  TEXT NOT NULL,
    fetched_at     TEXT NOT NULL
);

-- Every LLM call is logged so you can show token usage in the viva.
CREATE TABLE IF NOT EXISTS llm_calls (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    purpose        TEXT NOT NULL,                       -- profile_parse | extraction | explanation
    model          TEXT,
    ok             INTEGER NOT NULL,
    input_tokens   INTEGER,
    output_tokens  INTEGER,
    latency_ms     INTEGER,
    error          TEXT,
    created_at     TEXT NOT NULL
);

-- Shopping list (items from alternatives, explorer or scans).
CREATE TABLE IF NOT EXISTS shopping_list (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name  TEXT NOT NULL,
    brand         TEXT,
    code          TEXT,
    score         INTEGER,
    note          TEXT,
    done          INTEGER NOT NULL DEFAULT 0,
    added_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scans_created ON scans(created_at);
CREATE INDEX IF NOT EXISTS idx_logs_member ON intake_logs(member, logged_at);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


# ----------------------------------------------------------------- household
def get_household() -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT profile_json, raw_text, updated_at FROM household WHERE id = 1").fetchone()
    if not row:
        return None
    return {"profile": json.loads(row["profile_json"]), "raw_text": row["raw_text"], "updated_at": row["updated_at"]}


def save_household(profile: dict, raw_text: Optional[str] = None) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO household (id, raw_text, profile_json, updated_at) VALUES (1, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET raw_text = COALESCE(excluded.raw_text, household.raw_text), "
            "profile_json = excluded.profile_json, updated_at = excluded.updated_at",
            (raw_text, json.dumps(profile), now_iso()),
        )


# ----------------------------------------------------------- extraction cache
def cache_get_extraction(key: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT extraction_json, source FROM extraction_cache WHERE cache_key = ?", (key,)).fetchone()
    return {"extraction": json.loads(row["extraction_json"]), "source": row["source"]} if row else None


def cache_put_extraction(key: str, extraction: dict, source: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO extraction_cache (cache_key, extraction_json, source, created_at) VALUES (?, ?, ?, ?)",
            (key, json.dumps(extraction), source, now_iso()),
        )


# ---------------------------------------------------------------------- scans
def insert_scan(extraction: dict, score: int, source: str, image_hash: Optional[str]) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO scans (image_hash, barcode, product_name, brand, category, score, extraction_json, source, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (image_hash, extraction.get("barcode"), extraction.get("product_name"), extraction.get("brand"),
             extraction.get("category"), score, json.dumps(extraction), source, now_iso()),
        )
        return int(cur.lastrowid)


def get_scan(scan_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["extraction"] = json.loads(d.pop("extraction_json"))
    return d


def list_scans(limit: int = 50) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, product_name, brand, category, score, source, created_at FROM scans ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


# ----------------------------------------------------------------- intake logs
def insert_log(scan_id: int, member: str, grams: float, sugar_g, sodium_mg, sat_fat_g) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO intake_logs (scan_id, member, grams, sugar_g, sodium_mg, sat_fat_g, logged_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (scan_id, member, grams, sugar_g, sodium_mg, sat_fat_g, now_iso()),
        )
        return int(cur.lastrowid)


def logs_since(since_iso: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT l.*, s.product_name, s.score, s.category FROM intake_logs l JOIN scans s ON s.id = l.scan_id "
            "WHERE l.logged_at >= ? ORDER BY l.logged_at DESC",
            (since_iso,),
        ).fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------------------- feedback
def insert_feedback(scan_id, product_code, product_name, brand, vote, reason) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO alt_feedback (scan_id, product_code, product_name, brand, vote, reason, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (scan_id, product_code, product_name, brand, vote, reason, now_iso()),
        )
        return int(cur.lastrowid)


def all_feedback() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM alt_feedback ORDER BY id").fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------------ llm / off caches
def kv_get(table: str, key: str, max_age_hours: Optional[float] = None) -> Optional[Any]:
    assert table in ("llm_cache", "off_cache")
    col, tcol = ("value_json", "created_at") if table == "llm_cache" else ("response_json", "fetched_at")
    with get_conn() as conn:
        row = conn.execute(f"SELECT {col} AS v, {tcol} AS t FROM {table} WHERE cache_key = ?", (key,)).fetchone()
    if not row:
        return None
    if max_age_hours is not None:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(row["t"])
        if age.total_seconds() > max_age_hours * 3600:
            return None
    return json.loads(row["v"])


def kv_put(table: str, key: str, value: Any) -> None:
    assert table in ("llm_cache", "off_cache")
    col, tcol = ("value_json", "created_at") if table == "llm_cache" else ("response_json", "fetched_at")
    with get_conn() as conn:
        conn.execute(f"INSERT OR REPLACE INTO {table} (cache_key, {col}, {tcol}) VALUES (?, ?, ?)",
                     (key, json.dumps(value), now_iso()))


def log_llm_call(purpose: str, model: str, ok: bool, input_tokens=None, output_tokens=None,
                 latency_ms=None, error: Optional[str] = None) -> None:
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO llm_calls (purpose, model, ok, input_tokens, output_tokens, latency_ms, error, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (purpose, model, int(ok), input_tokens, output_tokens, latency_ms, (error or "")[:300], now_iso()),
            )
    except sqlite3.Error:
        pass  # usage logging must never break a request


def llm_usage_summary() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT purpose, COUNT(*) AS calls, SUM(ok) AS ok_calls, "
            "COALESCE(SUM(input_tokens), 0) AS input_tokens, COALESCE(SUM(output_tokens), 0) AS output_tokens, "
            "CAST(AVG(latency_ms) AS INTEGER) AS avg_latency_ms FROM llm_calls GROUP BY purpose"
        ).fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------------- deletes / reset
def delete_log(log_id: int) -> bool:
    with get_conn() as conn:
        return conn.execute("DELETE FROM intake_logs WHERE id = ?", (log_id,)).rowcount > 0


def delete_scan(scan_id: int) -> bool:
    with get_conn() as conn:
        conn.execute("DELETE FROM intake_logs WHERE scan_id = ?", (scan_id,))
        return conn.execute("DELETE FROM scans WHERE id = ?", (scan_id,)).rowcount > 0


def reset_history() -> None:
    """Demo helper: clear scans, logs, feedback and the shopping list (keeps profile + caches)."""
    with get_conn() as conn:
        for t in ("intake_logs", "scans", "alt_feedback", "shopping_list"):
            conn.execute(f"DELETE FROM {t}")
        conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('intake_logs','scans','alt_feedback','shopping_list')")


def all_scans_full(limit: int = 200) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM scans ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["extraction"] = json.loads(d.pop("extraction_json"))
        out.append(d)
    return out


# --------------------------------------------------------------- shopping list
def shopping_list() -> list[dict]:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM shopping_list ORDER BY done, id DESC").fetchall()]


def shopping_add(product_name, brand=None, code=None, score=None, note=None) -> int:
    with get_conn() as conn:
        if code:
            row = conn.execute("SELECT id FROM shopping_list WHERE code = ? AND done = 0", (code,)).fetchone()
            if row:
                return int(row["id"])
        cur = conn.execute(
            "INSERT INTO shopping_list (product_name, brand, code, score, note, added_at) VALUES (?, ?, ?, ?, ?, ?)",
            (product_name, brand, code, score, note, now_iso()))
        return int(cur.lastrowid)


def shopping_update(item_id: int, done: bool) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE shopping_list SET done = ? WHERE id = ?", (int(done), item_id))


def shopping_delete(item_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM shopping_list WHERE id = ?", (item_id,))
