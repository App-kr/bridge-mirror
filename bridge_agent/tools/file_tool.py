"""File read/write/search tool with path restriction."""

import fnmatch
import os
from pathlib import Path

from .base import BaseTool, ToolResult


class FileReadTool(BaseTool):
    """Read file contents."""

    def __init__(self, project_root: Path):
        self._root = project_root.resolve()

    def name(self) -> str:
        return "file_read"

    def description(self) -> str:
        return "Read the contents of a file. Path must be within the project directory."

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path (relative to project root or absolute)."},
                "offset": {"type": "integer", "description": "Start line (0-indexed). Default 0."},
                "limit": {"type": "integer", "description": "Max lines to read. Default all."},
            },
            "required": ["path"],
        }

    def _resolve(self, path: str) -> Path | None:
        p = Path(path)
        if not p.is_absolute():
            p = self._root / p
        p = p.resolve()
        # Security: must be within project root
        try:
            p.relative_to(self._root)
            return p
        except ValueError:
            return None

    def execute(self, path: str = "", offset: int = 0, limit: int = 0, **kwargs) -> ToolResult:
        if not path:
            return ToolResult(success=False, output="", error="No path provided")

        resolved = self._resolve(path)
        if not resolved:
            return ToolResult(success=False, output="", error=f"Path outside project root: {path}")
        if not resolved.exists():
            return ToolResult(success=False, output="", error=f"File not found: {path}")
        if not resolved.is_file():
            return ToolResult(success=False, output="", error=f"Not a file: {path}")

        try:
            content = resolved.read_text("utf-8", errors="replace")
            lines = content.splitlines(keepends=True)
            if offset > 0:
                lines = lines[offset:]
            if limit > 0:
                lines = lines[:limit]
            numbered = [f"{i + offset + 1:>5}\t{line}" for i, line in enumerate(lines)]
            return ToolResult(success=True, output="".join(numbered)[:50000])
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class FileWriteTool(BaseTool):
    """Write content to a file."""

    def __init__(self, project_root: Path):
        self._root = project_root.resolve()

    def name(self) -> str:
        return "file_write"

    def description(self) -> str:
        return "Write content to a file. Creates parent dirs if needed. Path must be within project."

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path."},
                "content": {"type": "string", "description": "Content to write."},
            },
            "required": ["path", "content"],
        }

    def _resolve(self, path: str) -> Path | None:
        p = Path(path)
        if not p.is_absolute():
            p = self._root / p
        p = p.resolve()
        try:
            p.relative_to(self._root)
            return p
        except ValueError:
            return None

    def execute(self, path: str = "", content: str = "", **kwargs) -> ToolResult:
        if not path:
            return ToolResult(success=False, output="", error="No path provided")

        resolved = self._resolve(path)
        if not resolved:
            return ToolResult(success=False, output="", error=f"Path outside project root: {path}")

        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content, "utf-8")
            return ToolResult(success=True, output=f"Written {len(content)} bytes to {resolved.relative_to(self._root)}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class FileSearchTool(BaseTool):
    """Search for files by glob pattern and content by regex."""

    def __init__(self, project_root: Path):
        self._root = project_root.resolve()

    def name(self) -> str:
        return "file_search"

    def description(self) -> str:
        return "Search for files by glob pattern or search content with a text pattern."

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "glob_pattern": {"type": "string", "description": "Glob pattern like '**/*.py' or 'src/**/*.ts'."},
                "content_pattern": {"type": "string", "description": "Text to search for in file contents."},
                "max_results": {"type": "integer", "description": "Max results (default 50).", "default": 50},
            },
        }

    def execute(self, glob_pattern: str = "", content_pattern: str = "",
                max_results: int = 50, **kwargs) -> ToolResult:
        results = []

        if glob_pattern:
            for p in self._root.rglob(glob_pattern):
                if p.is_file() and ".git" not in p.parts and "node_modules" not in p.parts:
                    results.append(str(p.relative_to(self._root)))
                    if len(results) >= max_results:
                        break

        if content_pattern and not results:
            # Search content of common file types
            for p in self._root.rglob("*"):
                if not p.is_file() or ".git" in p.parts or "node_modules" in p.parts:
                    continue
                if p.suffix not in (".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".json", ".sql", ".css"):
                    continue
                try:
                    text = p.read_text("utf-8", errors="ignore")
                    if content_pattern.lower() in text.lower():
                        # Find matching lines
                        for i, line in enumerate(text.splitlines(), 1):
                            if content_pattern.lower() in line.lower():
                                results.append(f"{p.relative_to(self._root)}:{i}: {line.strip()[:200]}")
                                if len(results) >= max_results:
                                    break
                except Exception:
                    continue
                if len(results) >= max_results:
                    break

        if not results:
            return ToolResult(success=True, output="No matches found.")

        return ToolResult(success=True, output="\n".join(results))
