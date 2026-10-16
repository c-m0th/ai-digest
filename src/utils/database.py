"""SQLite 近期投递历史；默认只比较最近 72 小时，不调用 AI。"""
import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.utils.dedup import fingerprints

DB_PATH = Path(__file__).parent.parent.parent / "data" / "digest.db"
_recent_keys = None
_days = 3


@contextmanager
def _get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def _now():
    return datetime.now(timezone.utc)


def _stamp(value):
    return value.strftime("%Y-%m-%d %H:%M:%S")


def init_db(days=3):
    global _recent_keys, _days
    try:
        _days = max(1, min(30, int(days)))
    except (ValueError, TypeError):
        _days = 3
    _recent_keys = None
    with _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS processed_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url_hash TEXT UNIQUE NOT NULL,
                url TEXT, title TEXT, source_name TEXT, platform TEXT,
                processed_at TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_processed_at ON processed_items(processed_at);
            CREATE TABLE IF NOT EXISTS delivered_fingerprints (
                fingerprint TEXT PRIMARY KEY,
                sent_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_fingerprint_sent_at
                ON delivered_fingerprints(sent_at);
            CREATE TABLE IF NOT EXISTS digest_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TEXT NOT NULL, items_count INTEGER DEFAULT 0,
                email_sent INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        conn.execute("DELETE FROM delivered_fingerprints WHERE sent_at < ?",
                     (_stamp(_now() - timedelta(days=_days)),))


def get_recent_fingerprints():
    global _recent_keys
    if _recent_keys is None:
        cutoff = _stamp(_now() - timedelta(days=_days))
        with _get_conn() as conn:
            _recent_keys = {row[0] for row in conn.execute(
                "SELECT fingerprint FROM delivered_fingerprints WHERE sent_at >= ?", (cutoff,))}
            # 用旧数据库最近三天的 URL 和标题构建身份，无需人工迁移。
            for row in conn.execute(
                    "SELECT url, title FROM processed_items WHERE processed_at >= ?", (cutoff,)):
                _recent_keys.update(fingerprints(dict(row)))
    return _recent_keys


def is_processed(url: str) -> bool:
    """抓取阶段先用 URL/可识别的论文 ID 快速跳过近期条目。"""
    return bool(fingerprints({"url": url}) & get_recent_fingerprints())


def mark_delivered(items):
    """仅在邮件成功发送后调用；一笔事务保存整批及其跨来源别名。"""
    global _recent_keys
    stamp = _stamp(_now())
    with _get_conn() as conn:
        for item in items:
            keys = fingerprints(item) | set(item.get("_dedup_keys", []))
            conn.executemany("""INSERT INTO delivered_fingerprints(fingerprint, sent_at)
                VALUES (?, ?) ON CONFLICT(fingerprint) DO UPDATE SET sent_at=excluded.sent_at""",
                             ((key, stamp) for key in keys))
            url = item.get("url", "")
            if url:
                conn.execute("""INSERT INTO processed_items
                    (url_hash, url, title, source_name, platform, processed_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(url_hash) DO UPDATE SET
                    title=excluded.title, processed_at=excluded.processed_at""",
                    (hashlib.sha256(url.encode()).hexdigest(), url, item.get("title", ""),
                     item.get("source_name", ""), item.get("platform", ""), stamp))
    _recent_keys = None


def mark_processed(url: str, title: str, source_name: str, platform: str):
    """兼容旧调用方；新的主流程使用 mark_delivered 一次记录整批。"""
    mark_delivered([{"url": url, "title": title, "source_name": source_name, "platform": platform}])


def record_run(items_count: int, email_sent: bool):
    with _get_conn() as conn:
        conn.execute("INSERT INTO digest_runs (run_date, items_count, email_sent) VALUES (?, ?, ?)",
                     (_now().strftime("%Y-%m-%d"), items_count, int(email_sent)))
