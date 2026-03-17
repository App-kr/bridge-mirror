"""Rich console — BRIDGE Agent.

Design  : Editorial Minimalism × Apple HIG
Aesthetic: Brutalist editorial — stark, precise, purposeful
Spacing : 4-unit base grid (Apple HIG)
"""

import itertools
import threading

from rich.console import Console
from rich.markdown import Markdown
from rich.padding import Padding
from rich.rule import Rule
from rich.text import Text

from .theme import (
    BRIDGE_THEME,
    AGENT_ICONS,
    AGENT_LABELS,
    AGENT_THINKING_FRAMES,
    AGENT_THINKING_DEFAULT,
)


# ── Animated thinking indicator ────────────────────────────────────────────────

class _AnimatedThinking:
    """Cycles agent emoji frames through a Rich Status while work is running."""

    def __init__(self, status, frames: list[str]):
        self._status = status
        self._iter   = itertools.cycle(frames)
        self._stop   = threading.Event()
        self._thread = None

    def __enter__(self):
        self._stop.clear()
        self._status.__enter__()

        def _cycle():
            while not self._stop.wait(0.28):
                self._status.update(f"[bridge.dim]  {next(self._iter)}[/]")

        self._thread = threading.Thread(target=_cycle, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=0.6)
        return self._status.__exit__(exc_type, exc_val, exc_tb)


# ── Main console class ─────────────────────────────────────────────────────────

class BridgeConsole:
    """Editorial terminal UI for BRIDGE Agent.

    Principles:
    - Apple HIG: 4-unit grid, typographic hierarchy, generous whitespace
    - Brutalist editorial: stark contrast, precision, zero ornament
    - Minimalist: remove everything that does not serve meaning
    """

    def __init__(self):
        self.console = Console(theme=BRIDGE_THEME)

    # ── Banner ─────────────────────────────────────────────────────────────────

    def show_banner(self):
        """Editorial brand header — letterspace + full-width rules."""
        c = self.console
        w = c.width or 80

        brand   = "B · R · I · D · G · E"
        label   = "AGENT SYSTEM"
        tagline = "A career that changes your life."

        # Right-align label: pad between brand and label
        gap = " " * max(w - len(brand) - len(label) - 4, 2)

        c.print()
        c.print(Rule(style="bold white"))
        c.print()
        c.print(f"  [bold white]{brand}[/]{gap}[dim white]{label}[/]")
        c.print()
        c.print(f"  [dim italic white]{tagline}[/]")
        c.print()
        c.print(Rule(style="dim white"))
        c.print()

    # ── Semantic messages ──────────────────────────────────────────────────────

    def info(self, msg: str):
        self.console.print(f"  [bridge.info]→  {msg}[/]")

    def success(self, msg: str):
        self.console.print(f"  [bridge.success]✓  {msg}[/]")

    def error(self, msg: str):
        self.console.print(f"  [bridge.error]✕  {msg}[/]")

    def warning(self, msg: str):
        self.console.print(f"  [bridge.warning]⚠  {msg}[/]")

    # ── Agent communication ────────────────────────────────────────────────────

    def agent_msg(self, agent_name: str, content: str):
        """Agent response — editorial rule header + indented markdown."""
        icon  = AGENT_ICONS.get(agent_name, AGENT_ICONS["_default"])
        label = AGENT_LABELS.get(agent_name, agent_name.upper())

        self.console.print()
        self.console.print(
            Rule(title=f" {icon}  {label} ", style="white", align="left")
        )
        self.console.print()
        self.console.print(Padding(Markdown(content), pad=(0, 0, 1, 4)))

    def tool_call(self, tool_name: str, args: dict):
        """Tool invocation — minimal inline indicator."""
        args_str = "  ".join(f"{k}={repr(v)[:50]}" for k, v in args.items())
        self.console.print(
            f"    [bridge.tool]▶  {tool_name}[/]  [dim]{args_str}[/]"
        )

    def delegate(self, agent_name: str, task: str):
        """Delegation — bold purple indicator."""
        icon  = AGENT_ICONS.get(agent_name, AGENT_ICONS["_default"])
        label = AGENT_LABELS.get(agent_name, agent_name.upper())
        self.console.print(
            f"  [bridge.delegate]◈  DELEGATE  →  {icon}  {label}[/]  "
            f"[dim]{task[:72]}[/]"
        )

    # ── Thinking animation ─────────────────────────────────────────────────────

    def thinking(self, agent_name: str):
        """Animated emoji spinner — context manager, cycles per agent role."""
        frames = AGENT_THINKING_FRAMES.get(agent_name, AGENT_THINKING_DEFAULT)
        status = self.console.status(
            f"[bridge.dim]  {frames[0]}[/]",
            spinner="dots",
            spinner_style="bridge.accent",
        )
        return _AnimatedThinking(status, frames)

    # ── Agent roster ───────────────────────────────────────────────────────────

    def show_agents(self, agents: list[dict]):
        c = self.console
        c.print()
        c.print(Rule(style="bold white"))
        c.print("  [bold white]AGENTS[/]")
        c.print(Rule(style="dim white"))
        c.print()

        for a in agents:
            icon  = AGENT_ICONS.get(a["name"], AGENT_ICONS["_default"])
            label = AGENT_LABELS.get(a["name"], a["name"].upper())
            tin, tout = a["tokens"]

            status_str = (
                "[bold green]●  ACTIVE[/]" if a["active"]
                else "[dim]○  idle[/]"
            )
            token_str = (
                f"[dim]{tin:,} ↑  {tout:,} ↓[/]" if tin > 0
                else "[dim]—[/]"
            )
            ctx_str = "[dim]ctx[/]" if a["has_history"] else "   "

            c.print(
                f"  {icon}  [bold white]{label:<18}[/]  "
                f"{status_str}   {token_str}   {ctx_str}"
            )

        c.print()
        c.print(Rule(style="dim white"))
        c.print()

    # ── Conversation history ───────────────────────────────────────────────────

    def show_conversations(self, conversations: list[dict]):
        c = self.console
        if not conversations:
            self.info("No conversations yet.")
            return

        c.print()
        c.print(Rule(style="bold white"))
        c.print("  [bold white]CONVERSATIONS[/]")
        c.print(Rule(style="dim white"))
        c.print()

        for conv in conversations:
            short_id  = conv["id"][:8]
            icon      = AGENT_ICONS.get(conv["agent"], AGENT_ICONS["_default"])
            model_str = f"{conv['provider']}/{conv['model']}"

            c.print(
                f"  [dim]{short_id}[/]  {icon}  "
                f"[white]{conv['title']:<32}[/]  [dim]{model_str}[/]"
            )

        c.print()
        c.print(Rule(style="dim white"))
        c.print()

    # ── Usage summary ──────────────────────────────────────────────────────────

    def show_usage(self, usage: dict):
        c = self.console
        c.print()
        c.print(Rule(style="bold white"))
        c.print("  [bold white]USAGE[/]")
        c.print(Rule(style="dim white"))
        c.print()

        rows = [
            ("API Calls",    f"{usage.get('calls', 0):,}"),
            ("Tokens In",    f"{usage.get('total_in', 0):,}"),
            ("Tokens Out",   f"{usage.get('total_out', 0):,}"),
            ("Session In",   f"{usage.get('session_in', 0):,}"),
            ("Session Out",  f"{usage.get('session_out', 0):,}"),
            ("Est. Cost",    f"${usage.get('total_cost', 0):.4f}"),
        ]
        for metric, value in rows:
            c.print(f"  [bridge.dim]{metric:<16}[/]  [white]{value}[/]")

        c.print()
        c.print(Rule(style="dim white"))
        c.print()

    # ── Help ───────────────────────────────────────────────────────────────────

    def show_help(self):
        c = self.console
        sections = {
            "NAVIGATION": [
                ("/help",              "Show this reference"),
                ("/agents",            "List all agents"),
                ("/agent <name>",      "Switch agent"),
                ("/team",              "Switch to team-lead"),
                ("/clear",             "Clear screen"),
                ("/exit",              "Exit"),
            ],
            "CONVERSATION": [
                ("/new",               "Start new conversation"),
                ("/history",           "Show conversation history"),
                ("/load <id>",         "Load a conversation"),
                ("/export [id]",       "Export to JSON"),
                ("/import <file>",     "Import from JSON"),
            ],
            "CONFIGURATION": [
                ("/model [name]",      "Show / change model"),
                ("/provider [name]",   "Show / change provider"),
                ("/tokens",            "Show token usage"),
                ("/config",            "Show configuration"),
            ],
        }

        c.print()
        c.print(Rule(style="bold white"))
        c.print("  [bold white]COMMANDS[/]")
        c.print(Rule(style="dim white"))

        for section, commands in sections.items():
            c.print()
            c.print(f"  [dim]{section}[/]")
            for cmd, desc in commands:
                c.print(f"  [bridge.accent]{cmd:<26}[/]  [dim]{desc}[/]")

        c.print()
        c.print(Rule(style="dim white"))
        c.print()

    # ── REPL prompt ────────────────────────────────────────────────────────────

    def prompt(self, agent_name: str) -> str:
        """Agent-aware input prompt with emoji identity."""
        icon  = AGENT_ICONS.get(agent_name, "◈")
        label = AGENT_LABELS.get(agent_name, agent_name.upper())
        try:
            return self.console.input(
                f"\n  {icon}  [bridge.prompt]{label}[/]  [dim]›[/]  "
            )
        except (EOFError, KeyboardInterrupt):
            return "/exit"
