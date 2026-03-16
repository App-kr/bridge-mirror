"""32x32 + 16x16 RPA 아이콘 생성 — 파란 원형 배경 + 흰색 R."""
import struct
import math


def make_rpa_ico(path):
    sizes = [32, 16]
    images = []

    for size in sizes:
        R_DEF = [
            [1,1,1,1,0],
            [1,0,0,0,1],
            [1,0,0,0,1],
            [1,1,1,1,0],
            [1,0,1,0,0],
            [1,0,0,1,0],
            [1,0,0,0,1],
        ]
        cx, cy = size / 2 - 0.5, size / 2 - 0.5
        radius = size / 2 - 1.5

        if size == 32:
            ox, oy, scale = 8, 5, 3
        else:
            ox, oy, scale = 3, 2, 2

        r_pixels = set()
        for ry, row in enumerate(R_DEF):
            for rx, p in enumerate(row):
                if p:
                    for dy in range(scale):
                        for dx in range(scale):
                            r_pixels.add((ox + rx*scale + dx, oy + ry*scale + dy))

        BLUE  = bytes([227, 113,   0, 255])
        WHITE = bytes([255, 255, 255, 255])
        TRANS = bytes([  0,   0,   0,   0])

        xor_data = bytearray()
        for y in range(size - 1, -1, -1):
            for x in range(size):
                dist = math.sqrt((x - cx)**2 + (y - cy)**2)
                if dist > radius:
                    xor_data += TRANS
                elif (x, y) in r_pixels:
                    xor_data += WHITE
                else:
                    xor_data += BLUE

        # AND 마스크 (투명 처리 — 32bit에서는 alpha로 대체되지만 포맷 준수)
        and_mask = bytes(4 * size)

        bih = struct.pack('<IIIHHIIIIII',
            40, size, size * 2, 1, 32, 0,
            len(xor_data), 0, 0, 0, 0)

        img_data = bih + bytes(xor_data) + and_mask
        images.append(img_data)

    # ICO 헤더 계산
    num = len(images)
    header_size = 6 + 16 * num  # ICONDIR + N * ICONDIRENTRY

    icondir = struct.pack('<HHH', 0, 1, num)

    entries = b""
    offset = header_size
    for i, (sz, img) in enumerate(zip(sizes, images)):
        entries += struct.pack('<BBBBHHII',
            sz, sz, 0, 0, 1, 32,
            len(img), offset)
        offset += len(img)

    with open(path, 'wb') as f:
        f.write(icondir + entries + b"".join(images))

    total = 6 + 16 * num + sum(len(img) for img in images)
    print(f"craig_icon.ico 생성 완료: {total} bytes ({sizes})")


if __name__ == "__main__":
    import os
    out = os.path.join(os.path.dirname(__file__), "..", "images", "craig_icon.ico")
    make_rpa_ico(os.path.abspath(out))
