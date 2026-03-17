"""Rich theme and visual identity — BRIDGE Agent.

Design system : Editorial Minimalism × Apple HIG
Palette       : Apple System Colors (near-black / off-white / blues)
Spacing       : 4-unit base grid  (4 / 8 / 16 / 24 px)
Aesthetic     : Brutalist editorial — function as form, zero ornament
"""

from rich.theme import Theme

# ── Color Palette (Apple System Colors) ───────────────────────────────────────
PALETTE = {
    # Base
    "black":    "#1A1A1A",   # Near-black (primary bg)
    "white":    "#F5F5F7",   # Apple off-white (primary text)
    # Actions
    "blue":     "#0071E3",   # Apple Blue — primary
    "blue_hi":  "#2997FF",   # Apple Blue — highlight
    # Semantic
    "red":      "#FF3B30",   # Apple Red — destructive
    "green":    "#30D158",   # Apple Green — success
    "amber":    "#FF9F0A",   # Apple Amber — warning
    "purple":   "#BF5AF2",   # Apple Purple — delegate
    # Neutral scale
    "n1":       "#6E6E73",   # Secondary label
    "n2":       "#AEAEB2",   # Tertiary label
    "n3":       "#D1D1D6",   # Separator
}

# ── Rich Theme ─────────────────────────────────────────────────────────────────
BRIDGE_THEME = Theme({
    # Typography hierarchy (Apple HIG)
    "display":          f"bold {PALETTE['white']}",
    "headline":         f"bold {PALETTE['white']}",
    "body":             PALETTE["white"],
    "caption":          PALETTE["n1"],

    # Brand
    "bridge.brand":     f"bold {PALETTE['white']}",
    "bridge.header":    f"bold {PALETTE['blue']}",
    "bridge.accent":    PALETTE["blue_hi"],

    # Semantic states
    "bridge.success":   f"bold {PALETTE['green']}",
    "bridge.error":     f"bold {PALETTE['red']}",
    "bridge.warning":   PALETTE["amber"],
    "bridge.info":      PALETTE["n2"],
    "bridge.dim":       PALETTE["n1"],

    # Agent communication
    "bridge.agent":     f"bold {PALETTE['white']}",
    "bridge.tool":      PALETTE["n1"],
    "bridge.delegate":  f"bold {PALETTE['purple']}",
    "bridge.prompt":    f"bold {PALETTE['blue']}",
    "bridge.code":      "#A8D8A8",
})

# ── Spacing scale (Apple HIG 4-unit grid) ─────────────────────────────────────
PADDING_XS = (0, 1)    # 4px  — tight
PADDING_SM = (0, 2)    # 8px  — compact
PADDING_MD = (1, 2)    # 16px — default
PADDING_LG = (1, 4)    # 24px — spacious

# ── Agent Identity (Apple office aesthetic) ───────────────────────────────────
AGENT_ICONS = {
    "team-lead":       "👔",   # Manager
    "security-check":  "🔒",   # Security
    "feature-dev":     "💻",   # Developer
    "qa-test":         "🧪",   # QA
    "_default":        "◈",
}

AGENT_LABELS = {
    "team-lead":       "TEAM LEAD",
    "security-check":  "SECURITY",
    "feature-dev":     "DEVELOPER",
    "qa-test":         "QA",
}

# ── Animated frames per agent (Apple office / workspace feel) ─────────────────
AGENT_THINKING_FRAMES = {
    "team-lead": [
        "👔  Strategizing...",
        "💼  Planning...",
        "🏢  Organizing...",
        "📋  Reviewing...",
        "🗂️  Analyzing...",
        "💼  Delegating...",
    ],
    "security-check": [
        "🔒  Scanning...",
        "🛡️  Analyzing...",
        "🔐  Securing...",
        "🔍  Examining...",
        "🧭  Mapping...",
        "🛡️  Verifying...",
    ],
    "feature-dev": [
        "💻  Building...",
        "⚡  Coding...",
        "🔨  Crafting...",
        "⚙️  Compiling...",
        "🌊  Flowing...",
        "🚀  Shipping...",
    ],
    "qa-test": [
        "🧪  Testing...",
        "✅  Validating...",
        "🔍  Examining...",
        "📊  Measuring...",
        "🏁  Checking...",
        "✅  Passing...",
    ],
}

AGENT_THINKING_DEFAULT = [
    "◈   Thinking...",
    "◈   Processing...",
    "◈   Reasoning...",
    "◈   Generating...",
]
