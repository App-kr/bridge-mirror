"""
BRIDGE Agent — PyInstaller build script + GitHub Release
=========================================================
Usage:
  python build_agent.py          # Build .exe only
  python build_agent.py --release  # Build + create GitHub release
  python build_agent.py --icon-only  # Generate icon only
"""

import subprocess
import sys
import shutil
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
DIST_DIR = APP_DIR / "dist"
EXE_NAME = "BRIDGEAgent"


def create_icon():
    """Create BRIDGE Agent icon (blue BA logo)."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("[INFO] Pillow not installed — building without icon.")
        return False

    sizes = [16, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        pad = max(1, size // 16)
        draw.rounded_rectangle(
            [pad, pad, size - pad, size - pad],
            radius=size // 4,
            fill=(0, 113, 227),
        )

        font_size = int(size * 0.45)
        try:
            font = ImageFont.truetype("segoeui.ttf", font_size)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except (OSError, IOError):
                font = ImageFont.load_default()

        text = "BA"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (size - tw) / 2 - bbox[0]
        y = (size - th) / 2 - bbox[1]
        draw.text((x, y), text, fill="white", font=font)

        images.append(img)

    icon_path = APP_DIR / "bridge_agent.ico"
    images[0].save(str(icon_path), format="ICO",
                   sizes=[(s, s) for s in sizes],
                   append_images=images[1:])
    print(f"[OK] Icon created: {icon_path}")
    return True


def prepare_bundle_data():
    """Copy skills, memory, CLAUDE.md into a temp bundle dir for --add-data."""
    bundle_dir = APP_DIR / "build_temp" / "bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    # Copy CLAUDE.md
    claude_md = PROJECT_ROOT / "CLAUDE.md"
    if claude_md.exists():
        shutil.copy2(str(claude_md), str(bundle_dir / "CLAUDE.md"))
        print(f"  Bundled: CLAUDE.md")

    # Copy skills
    skills_src = PROJECT_ROOT / ".claude" / "skills"
    skills_dst = bundle_dir / "skills"
    if skills_src.exists():
        if skills_dst.exists():
            shutil.rmtree(str(skills_dst))
        shutil.copytree(str(skills_src), str(skills_dst))
        count = len(list(skills_dst.glob("*.md")))
        print(f"  Bundled: {count} skill files")

    # Copy memory
    memory_src = PROJECT_ROOT / ".memory"
    memory_dst = bundle_dir / "memory"
    if memory_src.exists():
        if memory_dst.exists():
            shutil.rmtree(str(memory_dst))
        shutil.copytree(str(memory_src), str(memory_dst),
                       ignore=shutil.ignore_patterns("session_*"))
        count = len(list(memory_dst.glob("*.md")))
        print(f"  Bundled: {count} memory files")

    return bundle_dir


def build_exe():
    """Build standalone .exe with PyInstaller."""
    print("\n[BUILD] Starting PyInstaller build...")

    # Prepare bundled data
    print("\n[BUNDLE] Preparing embedded data...")
    bundle_dir = prepare_bundle_data()

    icon_path = APP_DIR / "bridge_agent.ico"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--console",
        f"--name={EXE_NAME}",
        f"--distpath={DIST_DIR}",
        f"--workpath={APP_DIR / 'build_temp' / 'pyinstaller'}",
        f"--specpath={APP_DIR}",
        # Hidden imports for all providers
        "--hidden-import=anthropic",
        "--hidden-import=anthropic._streaming",
        "--hidden-import=google.generativeai",
        "--hidden-import=rich",
        "--hidden-import=rich.markdown",
        "--hidden-import=rich.table",
        "--hidden-import=rich.panel",
        "--hidden-import=rich.syntax",
        "--hidden-import=rich.live",
        "--hidden-import=rich.spinner",
        "--hidden-import=httpx",
        "--hidden-import=httpx._transports",
        "--hidden-import=cryptography",
        "--hidden-import=cryptography.hazmat.primitives.ciphers.aead",
        "--hidden-import=dotenv",
        # Collect submodules
        "--collect-submodules=anthropic",
        "--collect-submodules=google.generativeai",
        "--collect-submodules=rich",
    ]

    if icon_path.exists():
        cmd.append(f"--icon={icon_path}")

    # Add bundled data
    skills_dir = bundle_dir / "skills"
    memory_dir = bundle_dir / "memory"
    claude_md = bundle_dir / "CLAUDE.md"

    if skills_dir.exists():
        cmd.append(f"--add-data={skills_dir};skills")
    if memory_dir.exists():
        cmd.append(f"--add-data={memory_dir};memory")
    if claude_md.exists():
        cmd.append(f"--add-data={claude_md};.")

    # Entry point
    cmd.append(str(APP_DIR / "__main__.py"))

    print(f"\n  PyInstaller command ({len(cmd)} args)...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    exe_path = DIST_DIR / f"{EXE_NAME}.exe"

    if result.returncode == 0 and exe_path.exists():
        size_mb = exe_path.stat().st_size / 1024 / 1024
        print(f"\n[OK] Build successful!")
        print(f"  Executable: {exe_path}")
        print(f"  Size: {size_mb:.1f} MB")
        return True
    else:
        print(f"\n[ERROR] Build failed:")
        if result.stderr:
            print(result.stderr[-2000:])
        if result.stdout:
            # Look for errors in stdout too
            for line in result.stdout.split("\n"):
                if "error" in line.lower() or "Error" in line:
                    print(f"  {line.strip()}")
        return False


def create_release():
    """Create a GitHub release with the .exe attached."""
    exe_path = DIST_DIR / f"{EXE_NAME}.exe"
    if not exe_path.exists():
        print("[ERROR] .exe not found. Build first.")
        return False

    version = "v1.0.0"
    size_mb = exe_path.stat().st_size / 1024 / 1024

    release_notes = f"""## BRIDGE Agent CLI {version}

Bridge Base 프로젝트의 AI 에이전트 팀을 독립 실행 가능한 CLI 도구로 패키징.

### Features
- **4 Agents**: team-lead, security-check, feature-dev, qa-test
- **LLM Providers**: Claude (Opus/Sonnet/Haiku) + Gemini (Flash/Lite)
- **7 Tools**: bash, file_read/write/search, git, db_query, http_request
- **Storage**: Encrypted API keys (AES-256-GCM) + SQLite conversation DB
- **Export/Import**: JSON 포맷으로 대화 이동 가능

### Usage
1. `BRIDGEAgent.exe` 다운로드
2. 실행 → API 키 입력 (첫 실행 시)
3. 대화 시작!

### Commands
`/help`, `/agents`, `/agent <name>`, `/team`, `/new`, `/export`, `/import`, `/model`, `/provider`, `/tokens`

### Size
{size_mb:.1f} MB (standalone, no Python required)
"""

    print(f"\n[RELEASE] Creating GitHub release {version}...")

    # Create release with gh CLI
    result = subprocess.run(
        [
            "gh", "release", "create", version,
            str(exe_path),
            "--title", f"BRIDGE Agent {version}",
            "--notes", release_notes,
        ],
        capture_output=True, text=True,
        cwd=str(PROJECT_ROOT),
    )

    if result.returncode == 0:
        print(f"[OK] Release created: {result.stdout.strip()}")
        return True
    else:
        print(f"[ERROR] Release failed: {result.stderr}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("BRIDGE Agent Builder")
    print("=" * 60)

    has_icon = create_icon()

    if "--icon-only" in sys.argv:
        print("\nIcon generation complete.")
        sys.exit(0)

    try:
        import PyInstaller
    except ImportError:
        print("\n[INFO] PyInstaller not installed.")
        print("  Install: pip install pyinstaller")
        print(f"\n  Or run directly: python -m bridge_agent")
        sys.exit(1)

    success = build_exe()

    if success and "--release" in sys.argv:
        create_release()
    elif success:
        print(f"\n  Run: {DIST_DIR / EXE_NAME}.exe")
        print(f"  Or: python build_agent.py --release  (to upload to GitHub)")
