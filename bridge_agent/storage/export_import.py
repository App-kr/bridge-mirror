"""Export/Import conversations as JSON files."""

import json
from pathlib import Path

from .database import ConversationDB


def export_conversation(db: ConversationDB, conv_id: str, output_path: Path) -> bool:
    """Export a conversation to a JSON file."""
    data = db.export_conversation(conv_id)
    if not data:
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return True


def import_conversation(db: ConversationDB, input_path: Path) -> str | None:
    """Import a conversation from a JSON file. Returns conversation ID or None."""
    if not input_path.exists():
        return None

    try:
        data = json.loads(input_path.read_text("utf-8"))
        if "conversation" not in data:
            return None

        db.import_conversation(data)
        return data["conversation"]["id"]
    except (json.JSONDecodeError, KeyError, Exception):
        return None


def export_all(db: ConversationDB, output_dir: Path) -> int:
    """Export all conversations to a directory. Returns count."""
    convs = db.list_conversations(limit=1000)
    output_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for conv in convs:
        path = output_dir / f"conv_{conv['id'][:8]}.json"
        if export_conversation(db, conv["id"], path):
            count += 1
    return count
