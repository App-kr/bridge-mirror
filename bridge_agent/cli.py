"""BRIDGE Agent — Interactive CLI REPL."""

import uuid
import sys
from pathlib import Path

from rich.live import Live
from rich.spinner import Spinner
from rich.console import Console

from bridge_agent.config import Config, DATA_DIR, VAULT_PATH, DB_PATH
from bridge_agent.storage.key_vault import KeyVault
from bridge_agent.storage.database import ConversationDB
from bridge_agent.storage.export_import import export_conversation, import_conversation
from bridge_agent.llm.registry import create_provider, list_providers
from bridge_agent.agents.orchestrator import Orchestrator
from bridge_agent.ui.console import BridgeConsole


def _first_run_setup(console: BridgeConsole, config: Config, vault: KeyVault) -> bool:
    """Interactive first-run setup. Returns True if setup completed."""
    console.show_banner()
    console.info("First-time setup. Let's configure your API keys.\n")

    providers = list_providers()

    # Choose provider
    console.console.print("[bridge.header]Available providers:[/]")
    for name, info in providers.items():
        console.console.print(f"  [bold]{name}[/] — {info['display']}")
        for m in info["models"]:
            console.console.print(f"    - {m}")

    console.console.print()

    provider = console.console.input(
        "[bridge.prompt]Choose provider (claude/gemini): [/]"
    ).strip().lower()

    if provider not in providers:
        console.error(f"Unknown provider: {provider}. Using 'claude'.")
        provider = "claude"

    config.provider = provider

    # API key
    key_name = providers[provider]["key_name"]
    api_key = console.console.input(
        f"[bridge.prompt]Enter {providers[provider]['display']} API key: [/]"
    ).strip()

    if not api_key:
        console.error("API key is required.")
        return False

    vault.set(key_name, api_key)
    console.success(f"API key saved (encrypted).")

    # Model selection
    models = providers[provider]["models"]
    console.console.print(f"\n[bridge.header]Available models for {provider}:[/]")
    for i, m in enumerate(models):
        default = " (default)" if i == (1 if provider == "claude" else 0) else ""
        console.console.print(f"  {i + 1}. {m}{default}")

    model_input = console.console.input(
        "[bridge.prompt]Choose model (number or name, Enter for default): [/]"
    ).strip()

    if model_input.isdigit():
        idx = int(model_input) - 1
        if 0 <= idx < len(models):
            config.model = models[idx]
    elif model_input in models:
        config.model = model_input
    # else: keep default

    # Project root
    default_root = config.project_root
    root_input = console.console.input(
        f"[bridge.prompt]Project root [{default_root}]: [/]"
    ).strip()

    if root_input:
        config.project_root = Path(root_input)

    console.success(f"\nSetup complete!")
    console.info(f"  Provider: {config.provider}")
    console.info(f"  Model: {config.model}")
    console.info(f"  Project: {config.project_root}")
    console.console.print()

    return True


def _handle_command(
    cmd: str,
    args: str,
    console: BridgeConsole,
    config: Config,
    vault: KeyVault,
    db: ConversationDB,
    orchestrator: Orchestrator,
    conv_id: str,
) -> tuple[bool, str]:
    """
    Handle a slash command.
    Returns (should_continue, updated_conv_id).
    """

    if cmd == "/help":
        console.show_help()

    elif cmd == "/agents":
        console.show_agents(orchestrator.list_agents())

    elif cmd == "/agent":
        if not args:
            console.info(f"Current agent: {orchestrator.current_agent_name}")
            console.info("Usage: /agent <name>")
            return True, conv_id
        try:
            orchestrator.switch_agent(args)
            console.success(f"Switched to agent: {args}")
        except ValueError as e:
            console.error(str(e))

    elif cmd == "/team":
        orchestrator.switch_agent("team-lead")
        console.success("Switched to team-lead (delegation enabled)")

    elif cmd == "/new":
        conv_id = str(uuid.uuid4())
        orchestrator.reset_all()
        db.create_conversation(
            conv_id, "New Conversation",
            orchestrator.current_agent_name,
            config.provider, config.model,
        )
        console.success("New conversation started.")

    elif cmd == "/history":
        convs = db.list_conversations()
        console.show_conversations(convs)

    elif cmd == "/load":
        if not args:
            console.info("Usage: /load <conversation-id-prefix>")
            return True, conv_id
        convs = db.list_conversations(limit=100)
        match = None
        for c in convs:
            if c["id"].startswith(args):
                match = c
                break
        if match:
            conv_id = match["id"]
            orchestrator.reset_all()
            msgs = db.get_messages(conv_id)
            console.success(f"Loaded conversation: {match['title']} ({len(msgs)} messages)")
            # Restore agent
            orchestrator.switch_agent(match["agent"])
        else:
            console.error(f"No conversation found matching: {args}")

    elif cmd == "/export":
        target = args if args else conv_id
        convs = db.list_conversations(limit=100)
        match_id = None
        for c in convs:
            if c["id"].startswith(target):
                match_id = c["id"]
                break
        if not match_id:
            match_id = conv_id

        out_path = DATA_DIR / "exports" / f"conv_{match_id[:8]}.json"
        if export_conversation(db, match_id, out_path):
            console.success(f"Exported to: {out_path}")
        else:
            console.error("Export failed. Conversation not found.")

    elif cmd == "/import":
        if not args:
            console.info("Usage: /import <path-to-json>")
            return True, conv_id
        path = Path(args)
        imported_id = import_conversation(db, path)
        if imported_id:
            conv_id = imported_id
            console.success(f"Imported conversation: {imported_id[:8]}")
        else:
            console.error(f"Import failed: {path}")

    elif cmd == "/model":
        if not args:
            console.info(f"Current model: {config.model}")
            providers = list_providers()
            p = providers.get(config.provider, {})
            console.info(f"Available: {', '.join(p.get('models', []))}")
        else:
            config.model = args
            console.success(f"Model changed to: {args}")
            console.warning("Restart agents to use new model: /new")

    elif cmd == "/provider":
        if not args:
            console.info(f"Current provider: {config.provider}")
        else:
            if args in list_providers():
                config.provider = args
                key_name = list_providers()[args]["key_name"]
                if not vault.has(key_name):
                    api_key = console.console.input(
                        f"[bridge.prompt]Enter {args} API key: [/]"
                    ).strip()
                    if api_key:
                        vault.set(key_name, api_key)
                console.success(f"Provider changed to: {args}")
                console.warning("Restart agents to use new provider: /new")
            else:
                console.error(f"Unknown provider: {args}")

    elif cmd == "/tokens":
        tin, tout = orchestrator.get_total_tokens()
        usage = db.get_usage_summary()
        usage["session_in"] = tin
        usage["session_out"] = tout
        console.show_usage(usage)
        console.info(f"Session tokens: {tin:,} in / {tout:,} out")

    elif cmd == "/config":
        console.info(f"Provider: {config.provider}")
        console.info(f"Model: {config.model}")
        console.info(f"Project root: {config.project_root}")
        console.info(f"Data dir: {DATA_DIR}")
        console.info(f"Keys stored: {', '.join(vault.list_keys())}")

    elif cmd == "/clear":
        console.console.clear()

    elif cmd == "/exit":
        # Save usage before exit
        tin, tout = orchestrator.get_total_tokens()
        if tin > 0 or tout > 0:
            db.log_usage(config.provider, config.model, tin, tout)
        console.info("Goodbye!")
        return False, conv_id

    else:
        console.error(f"Unknown command: {cmd}. Type /help for available commands.")

    return True, conv_id


def main():
    """Main entry point for BRIDGE Agent CLI."""
    console = BridgeConsole()
    config = Config()

    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    vault = KeyVault(VAULT_PATH)
    db = ConversationDB(DB_PATH)

    # Check if first run (no API keys configured)
    providers = list_providers()
    has_any_key = any(vault.has(p["key_name"]) for p in providers.values())

    if not has_any_key:
        if not _first_run_setup(console, config, vault):
            console.error("Setup incomplete. Run again to configure.")
            sys.exit(1)
    else:
        console.show_banner()
        console.info(f"Provider: {config.provider} | Model: {config.model}")
        console.info(f"Project: {config.project_root}")
        console.console.print()

    # Create LLM provider
    provider_info = providers.get(config.provider, {})
    key_name = provider_info.get("key_name", "anthropic_api_key")
    api_key = vault.get(key_name)

    if not api_key:
        console.error(f"No API key found for {config.provider}. Run /config to set up.")
        sys.exit(1)

    try:
        provider = create_provider(config.provider, api_key, config.model)
    except Exception as e:
        console.error(f"Failed to create provider: {e}")
        sys.exit(1)

    # Create orchestrator
    orchestrator = Orchestrator(
        provider=provider,
        project_root=config.project_root,
        on_agent_switch=lambda name: console.info(f"Agent: {name}"),
        on_tool_call=lambda name, args: console.tool_call(name, args),
        on_delegate=lambda agent, task: console.delegate(agent, task),
    )

    # Start conversation
    conv_id = str(uuid.uuid4())
    db.create_conversation(
        conv_id, "Session",
        orchestrator.current_agent_name,
        config.provider, config.model,
    )

    console.info("Type /help for commands. Start chatting!\n")

    # REPL loop
    while True:
        try:
            user_input = console.prompt(orchestrator.current_agent_name)
        except (EOFError, KeyboardInterrupt):
            user_input = "/exit"

        user_input = user_input.strip()
        if not user_input:
            continue

        # Handle slash commands
        if user_input.startswith("/"):
            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

            should_continue, conv_id = _handle_command(
                cmd, args, console, config, vault, db, orchestrator, conv_id,
            )
            if not should_continue:
                break
            continue

        # Save user message
        db.add_message(conv_id, "user", user_input)

        # Get agent response with spinner
        try:
            with console.console.status(
                "[bridge.info]Thinking...[/]",
                spinner="dots",
            ):
                response = orchestrator.chat(user_input)

            # Display response
            console.agent_msg(orchestrator.current_agent_name, response)

            # Save assistant message
            db.add_message(
                conv_id, "assistant", response,
                tokens_in=orchestrator.current_agent.total_tokens[0],
                tokens_out=orchestrator.current_agent.total_tokens[1],
            )

        except KeyboardInterrupt:
            console.warning("\nInterrupted.")
        except Exception as e:
            console.error(f"Error: {e}")


if __name__ == "__main__":
    main()
