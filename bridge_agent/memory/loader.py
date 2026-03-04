"""Load project memory from .md files."""

from pathlib import Path

from bridge_agent.config import SOURCE_MEMORY_DIR, MEMORY_DIR, CLAUDE_MD_PATH

MEMORY_FILES = [
    "MEMORY.md",
    "architecture.md",
    "api-endpoints.md",
    "debugging-patterns.md",
    "design-system.md",
    "admin-system.md",
    "deployment.md",
]


def _find_memory_dir() -> Path:
    """Find memory directory — prefer source, fallback to embedded."""
    if SOURCE_MEMORY_DIR.exists():
        return SOURCE_MEMORY_DIR
    return MEMORY_DIR


def load_memory(name: str) -> str:
    """Load a single memory file by name."""
    memory_dir = _find_memory_dir()
    path = memory_dir / name
    if path.exists():
        return path.read_text("utf-8", errors="replace")
    return ""


def load_all_memory() -> dict[str, str]:
    """Load all memory files as {name: content} dict."""
    memory_dir = _find_memory_dir()
    result = {}
    for fname in MEMORY_FILES:
        path = memory_dir / fname
        if path.exists():
            result[fname] = path.read_text("utf-8", errors="replace")
    return result


def load_claude_md() -> str:
    """Load the project CLAUDE.md rules."""
    if CLAUDE_MD_PATH.exists():
        return CLAUDE_MD_PATH.read_text("utf-8", errors="replace")
    return ""


def build_context() -> str:
    """Build combined context from CLAUDE.md + memory files."""
    parts = []

    claude_md = load_claude_md()
    if claude_md:
        parts.append("# Project Rules (CLAUDE.md)\n" + claude_md)

    memory = load_all_memory()
    if memory:
        parts.append("\n# Project Memory")
        for name, content in memory.items():
            parts.append(f"\n## {name}\n{content}")

    return "\n\n".join(parts)
