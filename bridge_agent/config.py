"""Configuration management for BRIDGE Agent."""

import json
import sys
import os
from pathlib import Path
from typing import Optional


def _get_app_dir() -> Path:
    """Get application directory — works for both script and PyInstaller .exe."""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller .exe
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _get_data_dir() -> Path:
    """Get data directory — uses %APPDATA%/BRIDGEAgent for portability."""
    app_data = os.environ.get("APPDATA")
    if app_data:
        return Path(app_data) / "BRIDGEAgent"
    # Fallback: next to executable/script
    return _get_app_dir() / "data"


# Default paths
APP_DIR = _get_app_dir()
PROJECT_ROOT = APP_DIR.parent  # Q:/Claudework/bridge base/ (dev mode)
DATA_DIR = _get_data_dir()
DB_PATH = DATA_DIR / "conversations.db"
VAULT_PATH = DATA_DIR / "keys.vault"

# Skills / Memory source dirs (embedded copies)
SKILLS_DIR = APP_DIR / "skills"
MEMORY_DIR = APP_DIR / "memory"

# Source dirs for copying (dev mode — from project root)
SOURCE_SKILLS_DIR = PROJECT_ROOT / ".claude" / "skills"
SOURCE_MEMORY_DIR = PROJECT_ROOT / ".memory"
SOURCE_AGENTS_DIR = PROJECT_ROOT / ".claude" / "agents"
CLAUDE_MD_PATH = PROJECT_ROOT / "CLAUDE.md"

# If running as .exe, check for bundled resources
if getattr(sys, 'frozen', False):
    _bundle_dir = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else APP_DIR
    if (_bundle_dir / "skills").exists():
        SOURCE_SKILLS_DIR = _bundle_dir / "skills"
        SKILLS_DIR = _bundle_dir / "skills"
    if (_bundle_dir / "memory").exists():
        SOURCE_MEMORY_DIR = _bundle_dir / "memory"
        MEMORY_DIR = _bundle_dir / "memory"
    if (_bundle_dir / "CLAUDE.md").exists():
        CLAUDE_MD_PATH = _bundle_dir / "CLAUDE.md"

# Defaults
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-6"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
MAX_TOOL_ITERATIONS = 10
MAX_CONVERSATION_TOKENS = 100_000


class Config:
    """Runtime configuration loaded from JSON file."""

    def __init__(self):
        self._path = DATA_DIR / "config.json"
        self._data: dict = {}
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text("utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def save(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), "utf-8")

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value
        self.save()

    @property
    def provider(self) -> str:
        return self._data.get("provider", "claude")

    @provider.setter
    def provider(self, value: str):
        self._data["provider"] = value
        self.save()

    @property
    def model(self) -> str:
        if self.provider == "claude":
            return self._data.get("claude_model", DEFAULT_CLAUDE_MODEL)
        return self._data.get("gemini_model", DEFAULT_GEMINI_MODEL)

    @model.setter
    def model(self, value: str):
        if self.provider == "claude":
            self._data["claude_model"] = value
        else:
            self._data["gemini_model"] = value
        self.save()

    @property
    def project_root(self) -> Path:
        p = self._data.get("project_root")
        return Path(p) if p else PROJECT_ROOT

    @project_root.setter
    def project_root(self, value: Path):
        self._data["project_root"] = str(value)
        self.save()
