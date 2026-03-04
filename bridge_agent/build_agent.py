"""
BRIDGE Agent — PyInstaller build script
========================================
Usage: python build_agent.py
"""

import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent


def create_icon():
    """Create BRIDGE Agent icon."""
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


def build_exe():
    """Build .exe with PyInstaller."""
    print("\n[BUILD] Starting PyInstaller build...")

    icon_path = APP_DIR / "bridge_agent.ico"
    icon_opt = f"--icon={icon_path}" if icon_path.exists() else ""

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--console",
        "--name=BRIDGEAgent",
        f"--distpath={APP_DIR / 'dist'}",
        f"--workpath={APP_DIR / 'build_temp'}",
        f"--specpath={APP_DIR}",
        "--hidden-import=anthropic",
        "--hidden-import=google.generativeai",
        "--hidden-import=rich",
        "--hidden-import=httpx",
        "--hidden-import=cryptography",
    ]

    if icon_opt:
        cmd.append(icon_opt)

    # Add data files (skills and memory)
    skills_dir = PROJECT_ROOT / ".claude" / "skills"
    memory_dir = PROJECT_ROOT / ".memory"

    if skills_dir.exists():
        cmd.append(f"--add-data={skills_dir};skills")
    if memory_dir.exists():
        cmd.append(f"--add-data={memory_dir};memory")

    cmd.append(str(APP_DIR / "__main__.py"))

    print(f"  Command: {' '.join(cmd[:6])}...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        exe_path = APP_DIR / "dist" / "BRIDGEAgent.exe"
        print(f"\n[OK] Build successful!")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / 1024 / 1024
            print(f"  Executable: {exe_path}")
            print(f"  Size: {size_mb:.1f} MB")
    else:
        print(f"\n[ERROR] Build failed:")
        print(result.stderr[-1000:] if result.stderr else "No error output")

    return result.returncode == 0


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
        build_exe()
    except ImportError:
        print("\n[INFO] PyInstaller not installed.")
        print("  Install: pip install pyinstaller")
        print(f"\n  Or run directly: python -m bridge_agent")
