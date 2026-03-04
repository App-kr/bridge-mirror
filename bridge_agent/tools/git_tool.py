"""Git operations tool."""

import subprocess
from pathlib import Path

from .base import BaseTool, ToolResult


class GitTool(BaseTool):
    """Git operations — status, diff, log, commit."""

    def __init__(self, project_root: Path):
        self._root = project_root

    def name(self) -> str:
        return "git"

    def description(self) -> str:
        return (
            "Run git commands: status, diff, log, add, commit. "
            "Destructive commands (push --force, reset --hard, clean -f) are blocked."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "subcommand": {
                    "type": "string",
                    "description": "Git subcommand: status, diff, log, add, commit, branch, checkout",
                },
                "args": {
                    "type": "string",
                    "description": "Additional arguments for the git command.",
                    "default": "",
                },
            },
            "required": ["subcommand"],
        }

    _BLOCKED = ["push --force", "reset --hard", "clean -f", "clean -fd", "branch -D"]

    def execute(self, subcommand: str = "", args: str = "", **kwargs) -> ToolResult:
        if not subcommand:
            return ToolResult(success=False, output="", error="No git subcommand provided")

        full_cmd = f"git {subcommand} {args}".strip()

        for blocked in self._BLOCKED:
            if blocked in full_cmd:
                return ToolResult(success=False, output="", error=f"Blocked: {blocked}")

        try:
            result = subprocess.run(
                full_cmd, shell=True, capture_output=True, text=True,
                cwd=str(self._root), timeout=30,
            )
            output = result.stdout
            if result.stderr:
                output += f"\n{result.stderr}" if output else result.stderr
            return ToolResult(
                success=result.returncode == 0,
                output=output[:20000],
                error="" if result.returncode == 0 else f"Exit code: {result.returncode}",
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error="Git command timed out")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
