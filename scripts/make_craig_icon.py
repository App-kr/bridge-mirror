"""
BRIDGE Craig RPA — 귀여운 로봇 아이콘 생성기
iOS 앱 아이콘 스타일: 파란 둥근 사각형 + 흰색 로봇
"""
from PIL import Image, ImageDraw
import math, sys

OUT = r"Q:\Claudework\bridge base\images\craig_icon.ico"


def make_bot_icon(size: int) -> Image.Image:
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    s    = size

    # ── 배경: iOS 블루 둥근 사각형 ──
    r_bg = s // 5
    draw.rounded_rectangle([0, 0, s - 1, s - 1], radius=r_bg,
                            fill=(10, 108, 240, 255))

    # 상단에 약간 밝은 글로우 오버레이
    draw.rounded_rectangle([0, 0, s - 1, s // 2], radius=r_bg,
                            fill=(80, 160, 255, 40))

    cx = s // 2

    # ── 안테나 ──
    pole_w   = max(2, s // 55)
    ant_base = int(s * 0.24)
    ant_top  = int(s * 0.06)
    draw.line([cx, ant_base, cx, ant_top], fill=(255, 255, 255, 200), width=pole_w)
    br = max(5, s // 30)         # ball radius
    draw.ellipse([cx - br, ant_top - br, cx + br, ant_top + br],
                 fill=(255, 214, 10, 255))            # 노란 공
    shine_br = max(2, br // 3)
    draw.ellipse([cx - br + shine_br, ant_top - br + shine_br,
                  cx - br + shine_br * 3, ant_top - br + shine_br * 3],
                 fill=(255, 240, 140, 200))

    # ── 머리 ──
    hw   = int(s * 0.52)
    hh   = int(s * 0.41)
    hx   = cx - hw // 2
    hy   = int(s * 0.23)
    hr   = max(10, int(hw * 0.18))
    draw.rounded_rectangle([hx, hy, hx + hw, hy + hh],
                            radius=hr, fill=(255, 255, 255, 255))

    # 머리 아래 그림자
    draw.rounded_rectangle([hx + 2, hy + hh - hr, hx + hw - 2, hy + hh + 2],
                            radius=hr // 2, fill=(200, 220, 255, 60))

    # ── 눈 ──
    er   = max(4, int(s * 0.067))
    ey   = hy + int(hh * 0.37)
    ex_l = cx - int(hw * 0.22)
    ex_r = cx + int(hw * 0.22)

    for ex in (ex_l, ex_r):
        # 파란 눈
        draw.ellipse([ex - er, ey - er, ex + er, ey + er],
                     fill=(10, 108, 240, 255))
        # 내부 밝은 원
        ir = max(2, er * 3 // 5)
        draw.ellipse([ex - ir, ey - ir, ex + ir, ey + ir],
                     fill=(80, 170, 255, 255))
        # 하이라이트
        sr = max(1, er // 4)
        draw.ellipse([ex - er + sr * 2, ey - er + sr,
                      ex - er + sr * 2 + sr * 2, ey - er + sr + sr * 2],
                     fill=(255, 255, 255, 210))

    # ── 입 (미소) ──
    mw  = int(hw * 0.34)
    my  = hy + int(hh * 0.66)
    mth = int(mw * 0.45)
    lw  = max(3, s // 48)
    draw.arc([cx - mw, my - mth, cx + mw, my + mth],
             start=205, end=335, fill=(10, 108, 240, 255), width=lw)

    # ── 몸통 ──
    tw = int(hw * 0.60)
    th = int(s * 0.11)
    tx = cx - tw // 2
    ty = hy + hh + max(3, s // 60)
    draw.rounded_rectangle([tx, ty, tx + tw, ty + th],
                            radius=max(4, th // 4),
                            fill=(255, 255, 255, 230))

    # 가슴 LED (초록)
    lr = max(3, s // 44)
    lcy = ty + th // 2
    draw.ellipse([cx - lr, lcy - lr, cx + lr, lcy + lr],
                 fill=(48, 209, 88, 255))
    draw.ellipse([cx - lr + 1, lcy - lr + 1, cx, lcy],
                 fill=(180, 255, 180, 160))

    return img


if __name__ == "__main__":
    print("Generating craig_icon.ico ...")
    sizes  = [256, 128, 64, 48, 32, 16]
    imgs   = [make_bot_icon(s) for s in sizes]
    imgs[0].save(OUT, format="ICO",
                 sizes=[(s, s) for s in sizes],
                 append_images=imgs[1:])
    print(f"Saved → {OUT}")
    print("Sizes:", sizes)
