"""
BRIDGE Craig RPA — 귀여운 로봇 아이콘 v2
더 크고 깔끔한 비례, 선명한 배경 그라디언트
"""
from PIL import Image, ImageDraw, ImageFilter
import math

OUT = r"Q:\Claudework\bridge base\images\craig_icon.ico"


def _lerp(a, b, t):
    return int(a + (b - a) * t)


def make_bg_gradient(size: int) -> Image.Image:
    """상단 밝은 파란→하단 짙은 파란/보라 그라디언트 배경."""
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r_bg = size // 5

    # 그라디언트: 줄마다 색상 보간
    top    = (20, 130, 255)
    bottom = (0,  60, 180)
    for y in range(size):
        t   = y / (size - 1)
        col = (_lerp(top[0], bottom[0], t),
               _lerp(top[1], bottom[1], t),
               _lerp(top[2], bottom[2], t), 255)
        draw.line([(0, y), (size - 1, y)], fill=col)

    # 라운드 코너 마스크 적용
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=r_bg, fill=255)

    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(img, mask=mask)
    return result


def make_bot_icon(size: int) -> Image.Image:
    img  = make_bg_gradient(size)
    draw = ImageDraw.Draw(img)
    s    = size
    cx   = s // 2

    # ── 안테나 ──────────────────────────────
    pole_top  = int(s * 0.06)
    pole_base = int(s * 0.25)
    pole_w    = max(3, s // 52)
    draw.line([(cx, pole_base), (cx, pole_top)],
              fill=(255, 255, 255, 210), width=pole_w)
    br = max(7, s // 24)                  # 안테나 볼 반지름 (더 크게)
    draw.ellipse([cx - br, pole_top - br,
                  cx + br, pole_top + br],
                 fill=(255, 214, 10, 255))
    # 볼 하이라이트
    sr = max(2, br // 3)
    draw.ellipse([cx - br + sr, pole_top - br + sr,
                  cx - br + sr * 3, pole_top - br + sr * 3],
                 fill=(255, 246, 140, 220))

    # ── 머리 (더 크고 동그랗게) ─────────────
    hw  = int(s * 0.58)
    hh  = int(s * 0.48)
    hx  = cx - hw // 2
    hy  = int(s * 0.23)
    hr  = max(14, int(hw * 0.22))

    # 살짝 그림자
    draw.rounded_rectangle([hx + 3, hy + 4, hx + hw + 3, hy + hh + 4],
                            radius=hr, fill=(0, 30, 80, 60))
    # 본 머리
    draw.rounded_rectangle([hx, hy, hx + hw, hy + hh],
                            radius=hr, fill=(255, 255, 255, 255))

    # ── 눈 ──────────────────────────────────
    er   = max(6, int(s * 0.082))        # 눈 반지름 (더 크게)
    ey   = hy + int(hh * 0.36)
    ex_l = cx - int(hw * 0.23)
    ex_r = cx + int(hw * 0.23)

    for ex in (ex_l, ex_r):
        # 눈 테두리 (흰 배경이라 경계 필요)
        draw.ellipse([ex - er - 2, ey - er - 2,
                      ex + er + 2, ey + er + 2],
                     fill=(200, 225, 255, 255))
        # 파란 눈
        draw.ellipse([ex - er, ey - er, ex + er, ey + er],
                     fill=(10, 108, 240, 255))
        # 내부 밝은 원
        ir = max(3, int(er * 0.55))
        draw.ellipse([ex - ir, ey - ir, ex + ir, ey + ir],
                     fill=(100, 180, 255, 255))
        # 동공 (작은 진한 원)
        pr = max(2, int(er * 0.28))
        draw.ellipse([ex - pr, ey - pr, ex + pr, ey + pr],
                     fill=(0, 60, 180, 255))
        # 하이라이트 (눈빛)
        hl = max(1, int(er * 0.22))
        draw.ellipse([ex - er + hl * 2, ey - er + hl,
                      ex - er + hl * 2 + hl * 2, ey - er + hl + hl * 2],
                     fill=(255, 255, 255, 240))

    # ── 볼 홍조 ──────────────────────────────
    cr = max(5, int(s * 0.055))
    cy_blush = ey + int(er * 1.2)
    for bx in (ex_l, ex_r):
        blush_img = Image.new("RGBA", (cr * 2, cr * 2), (0, 0, 0, 0))
        bd = ImageDraw.Draw(blush_img)
        bd.ellipse([0, 0, cr * 2, cr * 2], fill=(255, 100, 130, 90))
        blush_blurred = blush_img.filter(ImageFilter.GaussianBlur(cr // 2))
        img.paste(blush_blurred,
                  (bx - cr, cy_blush - cr),
                  blush_blurred)

    # draw 갱신 (paste 이후)
    draw = ImageDraw.Draw(img)

    # ── 입 (미소 호) ─────────────────────────
    my  = hy + int(hh * 0.65)
    mw  = int(hw * 0.33)
    mth = int(mw * 0.5)
    lw  = max(4, s // 44)
    draw.arc([cx - mw, my - mth, cx + mw, my + mth],
             start=205, end=335,
             fill=(10, 90, 220, 255), width=lw)

    return img


if __name__ == "__main__":
    print("Generating craig_icon.ico (v2) ...")
    sizes = [256, 128, 64, 48, 32, 16]
    imgs  = [make_bot_icon(s) for s in sizes]
    imgs[0].save(OUT, format="ICO",
                 sizes=[(s, s) for s in sizes],
                 append_images=imgs[1:])
    print(f"Saved → {OUT}")
