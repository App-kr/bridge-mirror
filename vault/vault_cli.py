"""
BRIDGE Secret Vault — CLI Interface
=====================================
- Passphrase input: hidden (no screen display)
- Decrypt output: clipboard only (never printed)
- Auto-clear clipboard after 15 seconds
- Session auto-lock after 5 minutes
"""

import sys
import os
import getpass
import time
import threading

# Add parent for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vault_core import SecretVault

VAULT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
PYTHON = sys.executable


def _get_passphrases() -> tuple:
    """Get both passphrases with hidden input."""
    print("\n--- BRIDGE Vault Unlock ---")
    pa = getpass.getpass("Passphrase A (inner): ").encode("utf-8")
    pb = getpass.getpass("Passphrase B (outer): ").encode("utf-8")
    if len(pa) < 8 or len(pb) < 8:
        print("[!] Passphrases must be at least 8 characters each")
        sys.exit(1)
    return pa, pb


def _clipboard_set(text: str):
    """Copy to clipboard using Windows clip command."""
    import subprocess
    p = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
    p.communicate(text.encode("utf-16-le"))


def _clipboard_clear_delayed(seconds: int = 15):
    """Clear clipboard after delay."""
    def _clear():
        time.sleep(seconds)
        import subprocess
        p = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
        p.communicate(b"")
        print(f"\n[*] Clipboard cleared ({seconds}s)")
    t = threading.Thread(target=_clear, daemon=True)
    t.start()


def cmd_init():
    """Initialize a new vault."""
    vault = SecretVault(VAULT_DIR)
    if os.path.exists(os.path.join(VAULT_DIR, "vault_index.enc")):
        ans = input("Vault already exists. Reinitialize? (type YES): ")
        if ans != "YES":
            print("Aborted.")
            return
    pa, pb = _get_passphrases()
    # Confirm passphrases
    pa2 = getpass.getpass("Confirm Passphrase A: ").encode("utf-8")
    pb2 = getpass.getpass("Confirm Passphrase B: ").encode("utf-8")
    if pa != pa2 or pb != pb2:
        print("[!] Passphrases do not match")
        sys.exit(1)
    vault.init_vault(pa, pb)
    print("[OK] Vault initialized at:", VAULT_DIR)


def cmd_add():
    """Add a secret entry."""
    pa, pb = _get_passphrases()
    vault = SecretVault(VAULT_DIR)
    vault.unlock(pa, pb)

    entry_id = input("Entry ID (e.g. gmail_app_password): ").strip()
    if not entry_id:
        print("[!] Entry ID required")
        return
    label = input("Label (description): ").strip()
    secret = getpass.getpass("Secret value (hidden): ")
    secret2 = getpass.getpass("Confirm secret: ")
    if secret != secret2:
        print("[!] Secrets do not match")
        return

    vault.add(entry_id, secret, label)
    vault.lock()
    print(f"[OK] Entry '{entry_id}' saved (double-encrypted)")


def cmd_get():
    """Retrieve a secret to clipboard only."""
    pa, pb = _get_passphrases()
    vault = SecretVault(VAULT_DIR)
    vault.unlock(pa, pb)

    entry_id = input("Entry ID to retrieve: ").strip()
    try:
        secret = vault.get(entry_id)
    except KeyError:
        print(f"[!] Entry '{entry_id}' not found")
        vault.lock()
        return

    _clipboard_set(secret)
    print(f"[OK] Secret copied to clipboard (auto-clear in 15s)")
    _clipboard_clear_delayed(15)
    # Wipe from memory
    secret = None  # noqa
    vault.lock()
    # Keep alive for clipboard clear
    time.sleep(16)


def cmd_list():
    """List all entries (no secrets shown)."""
    pa, pb = _get_passphrases()
    vault = SecretVault(VAULT_DIR)
    vault.unlock(pa, pb)

    entries = vault.list_entries()
    vault.lock()

    if not entries:
        print("(vault is empty)")
        return

    print(f"\n{'ID':<30} {'Label'}")
    print("-" * 60)
    for eid, label in entries.items():
        print(f"{eid:<30} {label}")
    print(f"\nTotal: {len(entries)} entries")


def cmd_delete():
    """Securely delete an entry."""
    pa, pb = _get_passphrases()
    vault = SecretVault(VAULT_DIR)
    vault.unlock(pa, pb)

    entry_id = input("Entry ID to delete: ").strip()
    confirm = input(f"Delete '{entry_id}'? (type YES): ")
    if confirm != "YES":
        print("Aborted.")
        vault.lock()
        return

    vault.delete(entry_id)
    vault.lock()
    print(f"[OK] Entry '{entry_id}' securely deleted")


def cmd_verify():
    """Verify vault integrity."""
    pa, pb = _get_passphrases()
    vault = SecretVault(VAULT_DIR)
    vault.unlock(pa, pb)

    if vault.verify_integrity():
        print("[OK] Vault integrity verified — no tampering detected")
    else:
        print("[!!] INTEGRITY CHECK FAILED — vault may be tampered!")
    vault.lock()


def cmd_audit():
    """Scan Q drive for plaintext passwords/secrets."""
    import re
    print("\n--- Q Drive Plaintext Secret Audit ---\n")

    patterns = [
        (r'(?:PASSWORD|PASSWD|PASS)\s*=\s*(?!ENC:|pbkdf2:|\$2[aby]\$)\S+', "PASSWORD"),
        (r'(?:API_KEY|APIKEY|SECRET_KEY)\s*=\s*\S+', "API_KEY"),
        (r'(?:TOKEN)\s*=\s*\S+', "TOKEN"),
        (r'(?:APP_PASSWORD)\s*=\s*\S+', "APP_PASSWORD"),
    ]

    scan_dirs = ["Q:/Claudework/bridge base", "Q:/Claudework/ClaudeBlog"]
    scan_exts = {".env", ".ini", ".cfg", ".yaml", ".yml", ".toml", ".json", ".py", ".conf"}
    skip_dirs = {"node_modules", ".git", "__pycache__", ".next", "backups", "vault"}

    findings = []

    for scan_root in scan_dirs:
        for root, dirs, files in os.walk(scan_root):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for fname in files:
                fpath = os.path.join(root, fname)
                _, ext = os.path.splitext(fname)
                if ext.lower() not in scan_exts:
                    continue
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for i, line in enumerate(f, 1):
                            for pat, cat in patterns:
                                if re.search(pat, line, re.IGNORECASE):
                                    # Skip encrypted values
                                    if "ENC:" in line or "pbkdf2:" in line:
                                        continue
                                    # Skip placeholder/example values
                                    val = line.strip()
                                    if any(x in val.lower() for x in
                                           ["여기에", "입력", "example", "placeholder", "your_"]):
                                        continue
                                    findings.append((fpath, i, cat, val[:80]))
                except (PermissionError, OSError):
                    pass

    if findings:
        print(f"[!!] {len(findings)} plaintext secrets found:\n")
        for fpath, line, cat, val in findings:
            rel = os.path.relpath(fpath, "Q:/Claudework")
            print(f"  {cat:<15} {rel}:{line}")
            print(f"  {'':15} {val[:60]}...")
            print()
    else:
        print("[OK] No plaintext secrets detected")

    return findings


def main():
    print("=" * 50)
    print("  BRIDGE Secret Vault v1.0")
    print("  Double-Encryption: ChaCha20 + AES-256-GCM")
    print("  KDF: Argon2id (128MB)")
    print("=" * 50)

    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        commands = {
            "init": cmd_init, "add": cmd_add, "get": cmd_get,
            "list": cmd_list, "delete": cmd_delete,
            "verify": cmd_verify, "audit": cmd_audit,
        }
        if cmd in commands:
            commands[cmd]()
            return

    print("\nCommands:")
    print("  [1] init    — Initialize new vault")
    print("  [2] add     — Add secret entry")
    print("  [3] get     — Retrieve to clipboard")
    print("  [4] list    — List entries (no secrets)")
    print("  [5] delete  — Securely delete entry")
    print("  [6] verify  — Check vault integrity")
    print("  [7] audit   — Scan for plaintext secrets")
    print("  [Q] quit")

    while True:
        choice = input("\n> ").strip().lower()
        if choice in ("1", "init"):
            cmd_init()
        elif choice in ("2", "add"):
            cmd_add()
        elif choice in ("3", "get"):
            cmd_get()
        elif choice in ("4", "list"):
            cmd_list()
        elif choice in ("5", "delete"):
            cmd_delete()
        elif choice in ("6", "verify"):
            cmd_verify()
        elif choice in ("7", "audit"):
            cmd_audit()
        elif choice in ("q", "quit"):
            break
        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()
