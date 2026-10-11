"""Persist AI responses in SQLite with a one-hour default TTL."""

import json
from contextlib import closing
from datetime import datetime, timedelta

import database

# TTL (Time-To-Live) cache dalam detik
CACHE_TTL_SECONDS = 3600  # 1 jam


def init_cache_table():
    """Buat tabel ai_cache jika belum ada. Dipanggil sekali saat startup."""
    with closing(database.get_connection()) as conn:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_cache (
                    cache_key   TEXT PRIMARY KEY,
                    result_json TEXT NOT NULL,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at  TIMESTAMP NOT NULL
                )
            """)


def get_cached(cache_key: str) -> dict | None:
    """
    Ambil hasil dari cache. Return None jika tidak ada atau sudah expired.
    """
    with closing(database.get_connection()) as conn:
        row = conn.execute(
            "SELECT result_json, expires_at FROM ai_cache WHERE cache_key = ?",
            (cache_key,)
        ).fetchone()

        if row is None:
            return None

        # Cek apakah masih berlaku
        expires_at = datetime.fromisoformat(row["expires_at"])
        if datetime.utcnow() > expires_at:
            # Cache expired, hapus
            invalidate(cache_key)
            return None

        try:
            return json.loads(row["result_json"])
        except (json.JSONDecodeError, TypeError):
            return None


def set_cache(cache_key: str, result: dict, ttl_seconds: int = CACHE_TTL_SECONDS):
    """
    Simpan hasil analisis ke cache dengan TTL tertentu.
    Upsert: kalau key sudah ada, timpa dengan data baru.
    """
    expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
    result_json = json.dumps(result, ensure_ascii=False)

    with closing(database.get_connection()) as conn:
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO ai_cache (cache_key, result_json, created_at, expires_at)
                VALUES (?, ?, CURRENT_TIMESTAMP, ?)
            """, (cache_key, result_json, expires_at))


def invalidate(cache_key: str):
    """Hapus satu entri cache (misal setelah data user berubah)."""
    with closing(database.get_connection()) as conn:
        with conn:
            conn.execute("DELETE FROM ai_cache WHERE cache_key = ?", (cache_key,))


def invalidate_all():
    """
    Hapus semua cache AI. Berguna saat seed data diulang atau
    admin minta refresh manual dari dashboard.
    """
    with closing(database.get_connection()) as conn:
        with conn:
            conn.execute("DELETE FROM ai_cache")


def cleanup_expired():
    """Bersihkan entri yang sudah expired. Opsional, bisa dijadwal berkala."""
    with closing(database.get_connection()) as conn:
        with conn:
            conn.execute("DELETE FROM ai_cache WHERE expires_at < ?", (datetime.utcnow().isoformat(),))


def get_cache_stats() -> dict:
    """Kembalikan statistik cache untuk debugging/monitoring."""
    with closing(database.get_connection()) as conn:
        total = conn.execute("SELECT COUNT(*) FROM ai_cache").fetchone()[0]
        valid = conn.execute(
            "SELECT COUNT(*) FROM ai_cache WHERE expires_at > ?",
            (datetime.utcnow().isoformat(),)
        ).fetchone()[0]
        return {"total_entries": total, "valid_entries": valid, "expired": total - valid}

