"""Tool registry — create tool sets for agents."""

from pathlib import Path

from .base import BaseTool
from .bash_tool import BashTool
from .file_tool import FileReadTool, FileWriteTool, FileSearchTool
from .git_tool import GitTool
from .db_tool import DBTool
from .http_tool import HTTPTool


def create_all_tools(project_root: Path) -> list[BaseTool]:
    """Create all available tools."""
    return [
        BashTool(cwd=project_root),
        FileReadTool(project_root),
        FileWriteTool(project_root),
        FileSearchTool(project_root),
        GitTool(project_root),
        DBTool(project_root, readonly=True),
        HTTPTool(),
    ]


def create_readonly_tools(project_root: Path) -> list[BaseTool]:
    """Create read-only tools (for QA agent)."""
    return [
        BashTool(cwd=project_root),
        FileReadTool(project_root),
        FileSearchTool(project_root),
        GitTool(project_root),
        DBTool(project_root, readonly=True),
        HTTPTool(),
    ]


def create_tools_for_agent(agent_name: str, project_root: Path) -> list[BaseTool]:
    """Create appropriate tool set for an agent."""
    if agent_name == "qa-test":
        return create_readonly_tools(project_root)
    return create_all_tools(project_root)


def tools_to_dicts(tools: list[BaseTool]) -> list[dict]:
    """Convert tools to LLM function-call format."""
    return [t.to_dict() for t in tools]


def find_tool(tools: list[BaseTool], name: str) -> BaseTool | None:
    """Find a tool by name."""
    for t in tools:
        if t.name() == name:
            return t
    return None
