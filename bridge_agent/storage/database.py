"""SQLite conversation database with usage logging."""

import json
import sqlite3
import time
from pathlib import Path
from typing import Optional


class ConversationDB:
    """Stores conversations, messages, and usage stats."""

    def __init__(self, db_path: Path):
        self._path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path))
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    agent TEXT NOT NULL DEFAULT 'team-lead',
                    provider TEXT NOT NULL DEFAULT 'claude',
                    model TEXT NOT NULL DEFAULT '',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    is_deleted INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tool_calls TEXT,
                    tool_results TEXT,
                    tokens_in INTEGER DEFAULT 0,
                    tokens_out INTEGER DEFAULT 0,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                );
                CREATE TABLE IF NOT EXISTS usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    tokens_in INTEGER NOT NULL DEFAULT 0,
                    tokens_out INTEGER NOT NULL DEFAULT 0,
                    cost_usd REAL NOT NULL DEFAULT 0.0,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_messages_conv
                    ON messages(conversation_id);
                CREATE INDEX IF NOT EXISTS idx_conv_updated
                    ON conversations(updated_at DESC);
            """)
            conn.commit()
        finally:
            conn.close()

    # ── Conversations ─────────────────────────────────────────

    def create_conversation(self, conv_id: str, title: str, agent: str,
                            provider: str, model: str) -> dict:
        now = time.time()
        conn = self._conn()
        try:
            conn.execute(
                "INSERT INTO conversations (id, title, agent, provider, model, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (conv_id, title, agent, provider, model, now, now),
            )
            conn.commit()
            return {"id": conv_id, "title": title, "agent": agent,
                    "provider": provider, "model": model,
                    "created_at": now, "updated_at": now}
        finally:
            conn.close()

    def list_conversations(self, limit: int = 20) -> list[dict]:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT id, title, agent, provider, model, created_at, updated_at "
                "FROM conversations WHERE is_deleted = 0 "
                "ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_conversation(self, conv_id: str) -> Optional[dict]:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM conversations WHERE id = ? AND is_deleted = 0",
                (conv_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_conversation(self, conv_id: str, **kwargs):
        conn = self._conn()
        try:
            sets = ", ".join(f"{k} = ?" for k in kwargs)
            vals = list(kwargs.values()) + [time.time(), conv_id]
            conn.execute(
                f"UPDATE conversations SET {sets}, updated_at = ? WHERE id = ?",
                vals,
            )
            conn.commit()
        finally:
            conn.close()

    def delete_conversation(self, conv_id: str):
        conn = self._conn()
        try:
            conn.execute(
                "UPDATE conversations SET is_deleted = 1 WHERE id = ?",
                (conv_id,),
            )
            conn.commit()
        finally:
            conn.close()

    # ── Messages ──────────────────────────────────────────────

    def add_message(self, conversation_id: str, role: str, content: str,
                    tool_calls: str | None = None, tool_results: str | None = None,
                    tokens_in: int = 0, tokens_out: int = 0) -> int:
        now = time.time()
        conn = self._conn()
        try:
            cur = conn.execute(
                "INSERT INTO messages "
                "(conversation_id, role, content, tool_calls, tool_results, "
                " tokens_in, tokens_out, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (conversation_id, role, content, tool_calls, tool_results,
                 tokens_in, tokens_out, now),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def get_messages(self, conversation_id: str) -> list[dict]:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id",
                (conversation_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ── Usage ─────────────────────────────────────────────────

    def log_usage(self, provider: str, model: str,
                  tokens_in: int, tokens_out: int, cost_usd: float = 0.0):
        conn = self._conn()
        try:
            conn.execute(
                "INSERT INTO usage_log (provider, model, tokens_in, tokens_out, cost_usd, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (provider, model, tokens_in, tokens_out, cost_usd, time.time()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_usage_summary(self) -> dict:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT COUNT(*) as calls, "
                "COALESCE(SUM(tokens_in), 0) as total_in, "
                "COALESCE(SUM(tokens_out), 0) as total_out, "
                "COALESCE(SUM(cost_usd), 0.0) as total_cost "
                "FROM usage_log"
            ).fetchone()
            return dict(row)
        finally:
            conn.close()

    # ── Export ─────────────────────────────────────────────────

    def export_conversation(self, conv_id: str) -> dict | None:
        conv = self.get_conversation(conv_id)
        if not conv:
            return None
        messages = self.get_messages(conv_id)
        return {"conversation": conv, "messages": messages}

    def import_conversation(self, data: dict):
        conv = data["conversation"]
        self.create_conversation(
            conv["id"], conv["title"], conv["agent"],
            conv["provider"], conv["model"],
        )
        for msg in data.get("messages", []):
            self.add_message(
                msg["conversation_id"], msg["role"], msg["content"],
                msg.get("tool_calls"), msg.get("tool_results"),
                msg.get("tokens_in", 0), msg.get("tokens_out", 0),
            )
