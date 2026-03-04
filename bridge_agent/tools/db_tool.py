"""SQLite database query tool (read-only by default)."""

import sqlite3
from pathlib import Path

from .base import BaseTool, ToolResult


class DBTool(BaseTool):
    """Execute SQLite queries against master.db (read-only by default)."""

    def __init__(self, project_root: Path, readonly: bool = True):
        self._root = project_root
        self._readonly = readonly

    def name(self) -> str:
        return "db_query"

    def description(self) -> str:
        mode = "read-only" if self._readonly else "read-write"
        return f"Execute SQLite queries against the project database ({mode}). Uses parameterized queries."

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "SQL query to execute. Use ? for parameters."},
                "params": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Query parameters (for ? placeholders).",
                    "default": [],
                },
                "db_file": {
                    "type": "string",
                    "description": "Database file name (default: master.db).",
                    "default": "master.db",
                },
            },
            "required": ["query"],
        }

    def execute(self, query: str = "", params: list | None = None,
                db_file: str = "master.db", **kwargs) -> ToolResult:
        if not query:
            return ToolResult(success=False, output="", error="No query provided")

        # Block write operations in read-only mode
        if self._readonly:
            q_upper = query.strip().upper()
            if any(q_upper.startswith(kw) for kw in
                   ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "REPLACE"]):
                return ToolResult(
                    success=False, output="",
                    error="Write operations blocked in read-only mode",
                )

        db_path = self._root / db_file
        if not db_path.exists():
            return ToolResult(success=False, output="", error=f"Database not found: {db_file}")

        conn = None
        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.row_factory = sqlite3.Row

            cursor = conn.execute(query, params or [])

            if query.strip().upper().startswith("SELECT"):
                rows = cursor.fetchall()
                if not rows:
                    return ToolResult(success=True, output="(no rows)")
                cols = [desc[0] for desc in cursor.description]
                lines = ["\t".join(cols)]
                for row in rows[:100]:
                    lines.append("\t".join(str(row[c]) for c in cols))
                return ToolResult(success=True, output="\n".join(lines))
            else:
                conn.commit()
                return ToolResult(success=True, output=f"OK. Rows affected: {cursor.rowcount}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
        finally:
            if conn:
                conn.close()
