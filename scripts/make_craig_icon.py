"""
BRIDGE Craig RPA — 아이콘 생성기
심플: 옅은 보라 둥근 사각형 + 흰 R
"""
from PIL import Image, ImageDraw, ImageFont

OUT = r"Q:\Claudework\bridge base\images\craig_icon.ico"

# 옅은 보라 (pastel purple)
BG_COLOR = (148, 108, 210, 255)


def make_r_icon(size: int) -> Image.Image:
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 둥근 사각형 배경
    r = size // 6
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=BG_COLOR)

    # 흰 R — 볼드 폰트 시도 순서
    font_paths = [
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/Arial Bold.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    font_size = int(size * 0.60)
    font = None
    for fp in font_paths:
        try:
            font = ImageFont.truetype(fp, font_size)
            break
        except Exception:
            pass
    if font is None:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), "R", font=font)
    tw   = bbox[2] - bbox[0]
    th   = bbox[3] - bbox[1]
    tx   = (size - tw) // 2 - bbox[0]
    ty   = (size - th) // 2 - bbox[1]
    draw.text((tx, ty), "R", fill=(255, 255, 255, 255), font=font)

    return img


if __name__ == "__main__":
    print("Generating craig_icon.ico (simple R) ...")
    sizes = [256, 128, 64, 48, 32, 16]
    imgs  = [make_r_icon(s) for s in sizes]
    imgs[0].save(OUT, format="ICO",
                 sizes=[(s, s) for s in sizes],
                 append_images=imgs[1:])
    print(f"Saved -> {OUT}")
