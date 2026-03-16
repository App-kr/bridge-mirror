# -*- coding: utf-8 -*-
"""
Bridge Blog Automation - Test Diagnosis
Run: python tools/blog_diag.py
"""
import sys
import os
import subprocess
import shutil
from pathlib import Path

BLOG_DIR = Path("Q:/Claudework/ClaudeBlog")
SEP = "=" * 50

def section(title):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)

def check(label, ok, msg=""):
    icon = "[OK]   " if ok else "[FAIL] "
    print(f"  {icon} {label}" + (f" : {msg}" if msg else ""))

# ── 1. Python environment
section("1. Python Environment")
py_candidates = [
    "C:/Python314/python.exe",
    str(BLOG_DIR / ".venv/Scripts/python.exe"),
    "C:/Users/Scarlett/AppData/Local/Programs/Python/Python313/python.exe",
]
for py in py_candidates:
    if Path(py).exists():
        r = subprocess.run([py, "--version"], capture_output=True, text=True)
        enc_r = subprocess.run([py, "-c", "import encodings; print('enc_ok')"], capture_output=True, text=True)
        ver = (r.stdout + r.stderr).strip()
        enc_ok = "enc_ok" in enc_r.stdout
        check(Path(py).parent.parent.name, enc_ok, f"{ver} | encodings={'OK' if enc_ok else 'BROKEN'}")

# ── 2. Packages (C:\Python314 = primary runtime)
section("2. Required Packages (C:\\Python314)")
py314 = "C:/Python314/python.exe"
pkgs = [
    ("anthropic",   "Anthropic API"),
    ("google.genai","Google Gemini"),
    ("selenium",    "Selenium WebDriver"),
    ("PIL",         "Pillow (image)"),
    ("schedule",    "Schedule"),
    ("pyperclip",   "Pyperclip"),
    ("json_repair", "json-repair"),
    ("cryptography","Cryptography"),
    ("keyring",     "Keyring"),
    ("dotenv",      "python-dotenv"),
]
if Path(py314).exists():
    for mod, name in pkgs:
        r = subprocess.run([py314, "-c", f"import {mod}"], capture_output=True, text=True)
        check(name, r.returncode == 0, mod)
else:
    print("  [SKIP] C:\\Python314 not found")

# ── 3. secrets & keyring
section("3. Secrets & API Keys")
secrets_enc = BLOG_DIR / "secrets.enc"
check("secrets.enc", secrets_enc.exists())

if Path(py314).exists():
    r = subprocess.run(
        [py314, "-c",
         "import keyring; k=keyring.get_password('BridgeBlogAuto','master_key'); print('SET' if k else 'EMPTY')"],
        capture_output=True, text=True
    )
    keyring_val = r.stdout.strip()
    check("Keyring master_key", keyring_val == "SET", keyring_val)

# config.json API keys placeholder check
import json
cfg_path = BLOG_DIR / "config.json"
if cfg_path.exists():
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    gemini_keys = cfg.get("api", {}).get("gemini_api_keys", [])
    real_keys = [k for k in gemini_keys if isinstance(k, dict) and "여기입력" not in k.get("key", "")]
    check(f"Gemini API keys in config.json", len(real_keys) > 0,
          f"{len(real_keys)}/{len(gemini_keys)} real keys")

# ── 4. Image folders
section("4. Image Folders")
img_base = BLOG_DIR / "images"
for folder in img_base.iterdir():
    if folder.is_dir() and not folder.name.startswith("_"):
        exts = {".jpg", ".jpeg", ".png", ".webp", ".JPG", ".JPEG", ".PNG"}
        imgs = [p for p in folder.rglob("*") if p.suffix in exts]
        check(f"images/{folder.name}", len(imgs) > 0, f"{len(imgs)} images")

# _tmp_resized leftover
tmp = img_base / "_tmp_resized"
if tmp.exists():
    files = list(tmp.glob("*"))
    size_mb = sum(f.stat().st_size for f in files if f.is_file()) / 1024 / 1024
    if files:
        print(f"  [WARN]  _tmp_resized — {len(files)} leftover files ({size_mb:.1f}MB) → cleanup needed")
    else:
        print("  [OK]    _tmp_resized — clean")

# ── 5. Database
section("5. Database & Logs")
db = BLOG_DIR / "logs/blog_history.db"
check("blog_history.db", db.exists(), f"{db.stat().st_size//1024}KB" if db.exists() else "missing")
log = BLOG_DIR / "logs/auto_post.log"
check("auto_post.log", log.exists())

# ── 6. Recent dry outputs
section("6. Recent dry_outputs")
dry_dir = BLOG_DIR / "dry_outputs"
if dry_dir.exists():
    dry_files = sorted(dry_dir.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
    if dry_files:
        for f in dry_files:
            import datetime
            mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime)
            print(f"  {f.name}  [{mtime.strftime('%Y-%m-%d %H:%M')}]")
    else:
        print("  None")

# ── 7. Test files
section("7. Test Files")
tests_dir = BLOG_DIR / "tests"
if tests_dir.exists():
    for t in tests_dir.iterdir():
        print(f"  {t.name}")
        # Check if test has mock / no-api mode
        content = t.read_text(encoding="utf-8", errors="ignore")
        has_mock = "mock" in content.lower() or "Mock" in content
        has_api_call = "_call_llm" in content or "generate(" in content
        print(f"    has_api_call: {has_api_call} | has_mock: {has_mock}")
else:
    print("  tests/ directory not found")

# ── 8. Known issues from log
section("8. Log Error Summary (last 50 lines)")
if log.exists():
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()[-50:]
    errors = [l for l in lines if "ERROR" in l or "FATAL" in l or "WinError" in l or "Errno" in l]
    if errors:
        for e in errors[-5:]:
            print(f"  {e.strip()[:120]}")
    else:
        print("  No recent errors")

print(f"\n{SEP}")
print("  DIAGNOSIS COMPLETE")
print(SEP)
