"""Load skill definitions from .md files."""

from pathlib import Path

from bridge_agent.config import SOURCE_SKILLS_DIR, SKILLS_DIR

SKILL_FILES = [
    "security.md",
    "code-style.md",
    "design.md",
    "workflow.md",
    "recruiting.md",
    "korean-ux.md",
]


def _find_skills_dir() -> Path:
    """Find skills directory — prefer source, fallback to embedded."""
    if SOURCE_SKILLS_DIR.exists():
        return SOURCE_SKILLS_DIR
    return SKILLS_DIR


def load_skill(name: str) -> str:
    """Load a single skill by name (without .md extension)."""
    skills_dir = _find_skills_dir()
    path = skills_dir / f"{name}.md"
    if path.exists():
        return path.read_text("utf-8", errors="replace")
    return ""


def load_all_skills() -> dict[str, str]:
    """Load all skills as {name: content} dict."""
    skills_dir = _find_skills_dir()
    result = {}
    for fname in SKILL_FILES:
        path = skills_dir / fname
        if path.exists():
            name = fname.replace(".md", "")
            result[name] = path.read_text("utf-8", errors="replace")
    return result


def skills_summary() -> str:
    """Return a compact summary of all loaded skills."""
    skills = load_all_skills()
    if not skills:
        return "(no skills loaded)"
    lines = ["## Loaded Skills"]
    for name, content in skills.items():
        first_line = content.strip().split("\n")[0][:80]
        lines.append(f"- **{name}**: {first_line}")
    return "\n".join(lines)
