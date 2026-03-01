"""
BRIDGE Admin App 아이콘 생성 + PyInstaller 빌드 스크립트
=======================================================
실행: python build_app.py

1단계: bridge_icon.ico 생성 (Pillow 필요)
2단계: PyInstaller로 .exe 빌드
"""

import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent


def create_icon():
    """귀여운 BRIDGE 아이콘 생성 (다리 + B 심볼)."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("[INFO] Pillow 미설치 — pip install Pillow")
        print("[INFO] 아이콘 없이 빌드합니다.")
        return False

    sizes = [16, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 배경: 둥근 사각형 (파란색 그라데이션 느낌)
        pad = max(1, size // 16)
        draw.rounded_rectangle(
            [pad, pad, size - pad, size - pad],
            radius=size // 4,
            fill=(0, 113, 227),  # Apple blue
        )

        # "B" 글자
        font_size = int(size * 0.55)
        try:
            font = ImageFont.truetype("segoeui.ttf", font_size)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except (OSError, IOError):
                font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), "B", font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (size - tw) / 2 - bbox[0]
        y = (size - th) / 2 - bbox[1]
        draw.text((x, y), "B", fill="white", font=font)

        # 작은 다리 심볼 (하단)
        if size >= 48:
            bridge_y = int(size * 0.78)
            bridge_w = int(size * 0.4)
            cx = size // 2
            lw = max(1, size // 32)
            draw.line([(cx - bridge_w // 2, bridge_y), (cx + bridge_w // 2, bridge_y)],
                      fill=(255, 255, 255, 180), width=lw)
            # 아치
            arc_h = int(size * 0.08)
            draw.arc(
                [cx - bridge_w // 4, bridge_y - arc_h * 2, cx + bridge_w // 4, bridge_y],
                start=180, end=0, fill=(255, 255, 255, 150), width=lw,
            )

        images.append(img)

    # .ico 파일 저장
    icon_path = APP_DIR / "bridge_icon.ico"
    images[0].save(str(icon_path), format="ICO",
                   sizes=[(s, s) for s in sizes],
                   append_images=images[1:])
    print(f"[OK] 아이콘 생성: {icon_path}")
    return True


def build_exe():
    """PyInstaller로 .exe 빌드."""
    print("\n[BUILD] PyInstaller 빌드 시작...")

    icon_path = APP_DIR / "bridge_icon.ico"
    icon_opt = f"--icon={icon_path}" if icon_path.exists() else ""

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        f"--name=BRIDGEAdmin",
        f"--distpath={APP_DIR / 'dist'}",
        f"--workpath={APP_DIR / 'build_temp'}",
        f"--specpath={APP_DIR}",
    ]
    if icon_opt:
        cmd.append(icon_opt)
    cmd.append(str(APP_DIR / "bridge_admin.py"))

    print(f"  Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        exe_path = APP_DIR / "dist" / "BRIDGEAdmin.exe"
        print(f"\n[OK] 빌드 성공!")
        print(f"  실행 파일: {exe_path}")
        print(f"  크기: {exe_path.stat().st_size / 1024 / 1024:.1f} MB" if exe_path.exists() else "")
    else:
        print(f"\n[ERROR] 빌드 실패:")
        print(result.stderr[-500:] if result.stderr else "No error output")

    return result.returncode == 0


if __name__ == "__main__":
    print("=" * 60)
    print("BRIDGE Admin App Builder")
    print("=" * 60)

    has_icon = create_icon()

    if "--icon-only" in sys.argv:
        print("\n아이콘만 생성 완료.")
        sys.exit(0)

    try:
        import PyInstaller
        build_exe()
    except ImportError:
        print("\n[INFO] PyInstaller 미설치")
        print("  설치: pip install pyinstaller")
        print("  설치 후 다시 실행: python build_app.py")
        print(f"\n  또는 직접 실행: python {APP_DIR / 'bridge_admin.py'}")
