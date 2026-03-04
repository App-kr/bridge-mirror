"""Quick setup script — set API keys without running the full CLI."""

import sys
from pathlib import Path

from bridge_agent.config import Config, DATA_DIR, VAULT_PATH
from bridge_agent.storage.key_vault import KeyVault


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    vault = KeyVault(VAULT_PATH)
    config = Config()

    print("BRIDGE Agent — API Key Setup")
    print("=" * 40)

    if len(sys.argv) >= 3:
        # Command line: python setup_keys.py claude sk-ant-xxx
        provider = sys.argv[1].lower()
        key = sys.argv[2]
        key_names = {"claude": "anthropic_api_key", "gemini": "google_api_key"}
        kn = key_names.get(provider)
        if kn:
            vault.set(kn, key)
            config.provider = provider
            print(f"  {provider} key saved (encrypted)")
        else:
            print(f"  Unknown provider: {provider}")
        return

    # Interactive
    print("\n1. Claude (Anthropic)")
    print("2. Gemini (Google)")
    print("3. Both")

    choice = input("\nChoose [1/2/3]: ").strip()

    if choice in ("1", "3"):
        key = input("Anthropic API key (sk-ant-...): ").strip()
        if key:
            vault.set("anthropic_api_key", key)
            config.provider = "claude"
            print("  Claude key saved!")

    if choice in ("2", "3"):
        key = input("Google API key (AIza...): ").strip()
        if key:
            vault.set("google_api_key", key)
            if choice == "2":
                config.provider = "gemini"
            print("  Gemini key saved!")

    print(f"\nDone! Keys stored in: {VAULT_PATH}")
    print(f"Current provider: {config.provider}")
    print(f"Current model: {config.model}")


if __name__ == "__main__":
    main()
