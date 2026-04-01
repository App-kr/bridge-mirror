#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BRIDGE RPA Desktop Icon Generator — suspension bridge + RPA branding"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math, os

# ── 색 팔레트 ──────────────────────────────────────────────────────────────────
BG_DARK   = (8, 18, 40, 255)       # 진한 네이비
BG_GRAD   = (14, 32, 68, 180)      # 그라디언트 레이어
BRIDGE_C  = (200, 218, 248)        # 밝은 스틸블루 (다리 구조)
CABLE_C   = (130, 168, 220)        # 케이블
SUSP_C    = (100, 140, 200)        # 수직 케이블
GREEN     = (34, 197, 94)          # #22c55e — RPA 텍스트
LABEL_C   = (140, 170, 220)        # "BRIDGE" 서브텍스트
WHITE     = (255, 255, 255, 255)
GLOW_C    = (80, 130, 220, 60)     # 블루 글로우

FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"
FONT_REG  = "C:/Windows/Fonts/arial.ttf"

# ── 아이콘 1장 생성 ────────────────────────────────────────────────────────────
def make_icon(size: int) -> Image.Image:
    s = size / 256.0  # 스케일 팩터

    # ── 배경 (rounded rect) ──────────────────────────────────────────────────
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bd   = ImageDraw.Draw(base)
    r    = int(size * 0.18)
    bd.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=BG_DARK)
    # 상단 그라디언트 레이어
    grad = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd   = ImageDraw.Draw(grad)
    for i in range(int(size * 0.55)):
        alpha = int(60 * (1 - i / (size * 0.55)))
        gd.rectangle([0, i, size, i + 1], fill=(20, 60, 120, alpha))
    grad_mask = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gm = ImageDraw.Draw(grad_mask)
    gm.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=(255, 255, 255, 255))
    base = Image.alpha_composite(base, Image.composite(grad, Image.new("RGBA", (size, size), (0,0,0,0)), grad_mask))

    draw = ImageDraw.Draw(base)

    # ── 치수 계산 ────────────────────────────────────────────────────────────
    deck_y   = int(156 * s)
    deck_x1  = int(22 * s)
    deck_x2  = int(234 * s)
    deck_h   = max(2, int(5 * s))
    tw       = max(2, int(9 * s))    # tower 폭
    lt_x     = int(70 * s)           # 왼쪽 타워 x
    rt_x     = int(186 * s)          # 오른쪽 타워 x
    t_top    = int(78 * s)           # 타워 상단 y
    t_cap_w  = int(20 * s)           # 타워 상단 캡 폭
    t_cap_h  = max(2, int(6 * s))    # 타워 캡 높이
    mid_x    = (lt_x + rt_x) // 2
    cab_low  = int(140 * s)          # 케이블 최저점 y

    # ── 글로우 레이어 (블러 처리) ─────────────────────────────────────────────
    if size >= 48:
        glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        gd2  = ImageDraw.Draw(glow)
        gd2.rectangle([deck_x1, deck_y, deck_x2, deck_y + deck_h],
                      fill=(80, 140, 255, 80))
        for tx in [lt_x, rt_x]:
            gd2.rectangle([tx - tw - 3, t_top, tx + tw + 3, deck_y + deck_h],
                          fill=(80, 140, 255, 60))
        blur_r = max(2, int(4 * s))
        glow   = glow.filter(ImageFilter.GaussianBlur(radius=blur_r))
        base   = Image.alpha_composite(base, glow)
        draw   = ImageDraw.Draw(base)

    # ── 도로 (deck) ──────────────────────────────────────────────────────────
    draw.rectangle([deck_x1, deck_y, deck_x2, deck_y + deck_h], fill=BRIDGE_C)
    # 도로 하이라이트
    if size >= 48:
        draw.rectangle([deck_x1, deck_y, deck_x2, deck_y + max(1, int(1.5*s))],
                       fill=(230, 240, 255))

    # ── 타워 ──────────────────────────────────────────────────────────────────
    for tx in [lt_x, rt_x]:
        draw.rectangle([tx - tw//2, t_top, tx + tw//2, deck_y + deck_h], fill=BRIDGE_C)
        # 타워 캡 (상단 넓은 바)
        draw.rectangle([tx - t_cap_w//2, t_top - t_cap_h//2,
                        tx + t_cap_w//2, t_top + t_cap_h//2], fill=BRIDGE_C)
        # 타워 중간 횡단바
        if size >= 32:
            cross_y = int((t_top + deck_y) * 0.52)
            cw2     = int(14 * s)
            ch2     = max(1, int(3 * s))
            draw.rectangle([tx - cw2//2, cross_y - ch2, tx + cw2//2, cross_y + ch2],
                           fill=BRIDGE_C)

    # ── 메인 케이블 (포물선) ──────────────────────────────────────────────────
    # y = a*(x-mid_x)^2 + cab_low
    a_coef = (t_top - cab_low) / ((lt_x - mid_x) ** 2)
    cable_pts = []
    steps = max(30, int(60 * s))
    for i in range(steps + 1):
        cx = lt_x + i * (rt_x - lt_x) / steps
        cy = a_coef * (cx - mid_x) ** 2 + cab_low
        cable_pts.append((int(cx), int(cy)))
    lw_cable = max(2, int(2.5 * s))
    draw.line(cable_pts, fill=CABLE_C, width=lw_cable)
    # 앵커 케이블 (타워→가장자리)
    if size >= 32:
        draw.line([(lt_x, t_top), (deck_x1 + int(8*s), deck_y)], fill=CABLE_C, width=max(1, int(2*s)))
        draw.line([(rt_x, t_top), (deck_x2 - int(8*s), deck_y)], fill=CABLE_C, width=max(1, int(2*s)))

    # ── 수직 케이블 (suspenders) ──────────────────────────────────────────────
    if size >= 32:
        num = 5 if size < 64 else 7
        for i in range(1, num + 1):
            t    = i / (num + 1)
            sx   = lt_x + t * (rt_x - lt_x)
            sy   = a_coef * (sx - mid_x) ** 2 + cab_low
            draw.line([(int(sx), int(sy)), (int(sx), deck_y)],
                      fill=SUSP_C, width=max(1, int(1.2 * s)))

    # ── 텍스트 ────────────────────────────────────────────────────────────────
    if size >= 48:
        try:
            rpa_sz   = max(11, int(26 * s))
            rpa_font = ImageFont.truetype(FONT_BOLD, rpa_sz)
            bbox     = draw.textbbox((0, 0), "RPA", font=rpa_font)
            tw2 = bbox[2] - bbox[0]
            tx_pos = (size - tw2) // 2
            ty_pos = deck_y + deck_h + max(3, int(6 * s))
            # 텍스트 그림자
            draw.text((tx_pos + 1, ty_pos + 1), "RPA", fill=(0, 80, 20, 180), font=rpa_font)
            draw.text((tx_pos, ty_pos), "RPA", fill=GREEN, font=rpa_font)
        except Exception as e:
            pass

    if size >= 128:
        try:
            br_sz   = max(8, int(13 * s))
            br_font = ImageFont.truetype(FONT_REG, br_sz)
            bbox2   = draw.textbbox((0, 0), "BRIDGE", font=br_font)
            tw3 = bbox2[2] - bbox2[0]
            tx3 = (size - tw3) // 2
            ty3 = size - int(22 * s)
            draw.text((tx3, ty3), "BRIDGE", fill=LABEL_C, font=br_font)
        except Exception as e:
            pass

    return Image.alpha_composite(img, base)

# ── 멀티 사이즈 ICO 저장 ──────────────────────────────────────────────────────
def build_ico(out_path: str):
    sizes  = [256, 128, 64, 48, 32, 16]
    images = [make_icon(s) for s in sizes]
    images[0].save(
        out_path, format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:]
    )
    print(f"[OK] 아이콘 저장: {out_path}")
    return out_path

if __name__ == "__main__":
    out = r"Q:\Claudework\bridge base\rpa_icon.ico"
    build_ico(out)
    # 미리보기 PNG (확인용)
    preview = make_icon(256)
    preview.save(r"Q:\Claudework\bridge base\rpa_icon_preview.png")
    print("[OK] 미리보기: rpa_icon_preview.png")

