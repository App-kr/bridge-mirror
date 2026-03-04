"""Bash command execution tool with safety checks."""

import subprocess
from pathlib import Path

from .base import BaseTool, ToolResult

# Commands that are blocked for safety
BLOCKED_COMMANDS = [
    "rm -rf /", "rm -rf ~", "rm -rf .",
    "mkfs", "dd if=", ":(){", "fork bomb",
    "shutdown", "reboot", "halt",
    "format c:", "del /f /s /q",
]

BLOCKED_PREFIXES = [
    "rm -rf /",
    "sudo rm -rf",
    "kill -9 1",
]


class BashTool(BaseTool):
    """Execute bash/shell commands in the project directory."""

    def __init__(self, cwd: Path | None = None):
        self._cwd = cwd

    def name(self) -> str:
        return "bash"

    def description(self) -> str:
        return (
            "Execute a shell command. Use for git, npm, python, curl, and other CLI tools. "
            "Dangerous commands (rm -rf /, format, shutdown) are blocked."
        )

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default 120).",
                    "default": 120,
                },
            },
            "required": ["command"],
        }

    def _is_blocked(self, command: str) -> str | None:
        cmd_lower = command.lower().strip()
        for blocked in BLOCKED_COMMANDS:
            if blocked in cmd_lower:
                return f"Blocked dangerous command: {blocked}"
        for prefix in BLOCKED_PREFIXES:
            if cmd_lower.startswith(prefix):
                return f"Blocked dangerous command prefix: {prefix}"
        return None

    def execute(self, command: str = "", timeout: int = 120, **kwargs) -> ToolResult:
        if not command:
            return ToolResult(success=False, output="", error="No command provided")

        blocked = self._is_blocked(command)
        if blocked:
            return ToolResult(success=False, output="", error=blocked)

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(self._cwd) if self._cwd else None,
                timeout=timeout,
            )
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]: {result.stderr}" if output else result.stderr

            return ToolResult(
                success=result.returncode == 0,
                output=output[:30000],  # cap output
                error="" if result.returncode == 0 else f"Exit code: {result.returncode}",
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error=f"Command timed out after {timeout}s")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
