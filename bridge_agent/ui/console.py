"""Rich console wrapper for BRIDGE Agent."""

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

from .theme import BRIDGE_THEME, BANNER, AGENT_ICONS


class BridgeConsole:
    """Wrapper around Rich console with BRIDGE styling."""

    def __init__(self):
        self.console = Console(theme=BRIDGE_THEME)

    def show_banner(self):
        self.console.print(BANNER, style="bridge.header")

    def info(self, msg: str):
        self.console.print(f"[bridge.info]{msg}[/]")

    def success(self, msg: str):
        self.console.print(f"[bridge.success]{msg}[/]")

    def error(self, msg: str):
        self.console.print(f"[bridge.error]{msg}[/]")

    def warning(self, msg: str):
        self.console.print(f"[bridge.warning]{msg}[/]")

    def agent_msg(self, agent_name: str, content: str):
        icon = AGENT_ICONS.get(agent_name, "[bold]??[/]")
        self.console.print(f"\n{icon} [{agent_name}]", style="bridge.agent")
        self.console.print(Markdown(content))

    def tool_call(self, tool_name: str, args: dict):
        args_str = ", ".join(f"{k}={repr(v)[:60]}" for k, v in args.items())
        self.console.print(f"  [bridge.tool]> {tool_name}({args_str})[/]")

    def delegate(self, agent_name: str, task: str):
        icon = AGENT_ICONS.get(agent_name, "??")
        self.console.print(f"  [bridge.delegate]DELEGATE -> {icon} {agent_name}: {task[:80]}[/]")

    def show_agents(self, agents: list[dict]):
        table = Table(title="Available Agents", show_header=True)
        table.add_column("Agent", style="bridge.agent")
        table.add_column("Active", justify="center")
        table.add_column("History")
        table.add_column("Tokens (in/out)")

        for a in agents:
            active = "[green]>>>[/]" if a["active"] else ""
            history = "yes" if a["has_history"] else "-"
            tin, tout = a["tokens"]
            tokens = f"{tin:,}/{tout:,}" if tin > 0 else "-"
            table.add_row(a["name"], active, history, tokens)

        self.console.print(table)

    def show_conversations(self, conversations: list[dict]):
        if not conversations:
            self.info("No conversations yet.")
            return

        table = Table(title="Recent Conversations", show_header=True)
        table.add_column("ID", style="dim")
        table.add_column("Title")
        table.add_column("Agent")
        table.add_column("Provider/Model")

        for c in conversations:
            short_id = c["id"][:8]
            table.add_row(short_id, c["title"], c["agent"], f"{c['provider']}/{c['model']}")

        self.console.print(table)

    def show_usage(self, usage: dict):
        table = Table(title="Usage Summary", show_header=True)
        table.add_column("Metric")
        table.add_column("Value", justify="right")

        table.add_row("API Calls", f"{usage.get('calls', 0):,}")
        table.add_row("Tokens In", f"{usage.get('total_in', 0):,}")
        table.add_row("Tokens Out", f"{usage.get('total_out', 0):,}")
        table.add_row("Est. Cost", f"${usage.get('total_cost', 0):.4f}")

        self.console.print(table)

    def show_help(self):
        help_text = """
## BRIDGE Agent CLI Commands

| Command | Description |
|---------|-------------|
| `/help` | Show this help |
| `/agents` | List all agents |
| `/agent <name>` | Switch to agent (team-lead, security-check, feature-dev, qa-test) |
| `/team` | Switch to team-lead (with delegation) |
| `/new` | Start new conversation |
| `/history` | Show conversation history |
| `/load <id>` | Load a conversation |
| `/export [id]` | Export conversation to JSON |
| `/import <file>` | Import conversation from JSON |
| `/model [name]` | Show/change model |
| `/provider [name]` | Show/change provider |
| `/tokens` | Show token usage |
| `/config` | Show configuration |
| `/clear` | Clear screen |
| `/exit` | Exit the program |
"""
        self.console.print(Markdown(help_text))

    def prompt(self, agent_name: str) -> str:
        icon = AGENT_ICONS.get(agent_name, "")
        try:
            return self.console.input(f"\n{icon} [bridge.prompt]bridge ({agent_name}) >[/] ")
        except (EOFError, KeyboardInterrupt):
            return "/exit"
