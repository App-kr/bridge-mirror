"""Rich theme and color definitions for BRIDGE Agent."""

from rich.theme import Theme

BRIDGE_THEME = Theme({
    "bridge.header": "bold #0071E3",      # Apple blue
    "bridge.success": "bold green",
    "bridge.error": "bold red",
    "bridge.warning": "bold yellow",
    "bridge.info": "dim cyan",
    "bridge.agent": "bold magenta",
    "bridge.tool": "dim #FFA500",
    "bridge.prompt": "bold #0071E3",
    "bridge.dim": "dim white",
    "bridge.code": "#A8D8A8",
    "bridge.delegate": "bold #FF6B6B",
})

BANNER = r"""
 ____  ____  ___ ____   ____ _____
| __ )|  _ \|_ _|  _ \ / ___| ____|
|  _ \| |_) || || | | | |  _|  _|
| |_) |  _ < | || |_| | |_| | |___
|____/|_| \_\___|____/ \____|_____|
           Agent CLI v1.0
"""

AGENT_ICONS = {
    "team-lead": "[bold blue]TL[/]",
    "security-check": "[bold red]SC[/]",
    "feature-dev": "[bold green]FD[/]",
    "qa-test": "[bold yellow]QA[/]",
}
