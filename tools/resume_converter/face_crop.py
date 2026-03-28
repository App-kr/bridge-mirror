"""
face_crop.py — BRIDGE Resume Converter
얼굴 인식 + 증명사진 자동 크롭 (OpenCV Haar Cascade)

출력: 300x400px (3:4), 150dpi, EXIF 제거
"""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ExifTags

# ── Haar Cascade 로드 ─────────────────────────────────────────────────────
_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
_face_cascade: Optional[cv2.CascadeClassifier] = None

def _get_cascade() -> cv2.CascadeClassifier:
    global _face_cascade
    if _face_cascade is None:
        _face_cascade = cv2.CascadeClassifier(_CASCADE_PATH)
    return _face_cascade


# ── 커스텀 예외 ────────────────────────────────────────────────────────────
class FaceNotFoundError(Exception):
    pass

class MultipleDecodeError(Exception):
    pass


# ── HEIC 처리 ──────────────────────────────────────────────────────────────
def _load_image_pil(path: Path) -> Image.Image:
    """PIL로 이미지 열기. HEIC는 pillow-heif 폴백."""
    try:
        img = Image.open(str(path))
        img.load()
        return img
    except Exception:
        # pillow-heif 설치된 경우 HEIC 지원
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
            return Image.open(str(path))
        except ImportError:
            raise IOError(f"HEIC 파일 열기 실패: {path} (pillow-heif 미설치)")


# ── EXIF 제거 ──────────────────────────────────────────────────────────────
def _strip_exif(img: Image.Image) -> Image.Image:
    """EXIF 메타데이터 전체 제거."""
    data = img.tobytes()
    clean = Image.frombytes(img.mode, img.size, data)
    return clean


# ── 얼굴 감지 ─────────────────────────────────────────────────────────────
def detect_faces(img: Image.Image) -> list[Tuple[int, int, int, int]]:
    """
    얼굴 좌표 목록 반환. [(x, y, w, h), ...]
    감지된 순서는 면적 내림차순 정렬.
    """
    arr  = np.array(img.convert("RGB"))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    cas  = _get_cascade()

    faces = cas.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80),
    )

    if len(faces) == 0:
        # 파라미터 완화 재시도
        faces = cas.detectMultiScale(
            gray,
            scaleFactor=1.05,
            minNeighbors=3,
            minSize=(50, 50),
        )

    if len(faces) == 0:
        return []

    # 면적 내림차순 정렬
    faces_list = [(x, y, w, h) for x, y, w, h in faces]
    faces_list.sort(key=lambda f: f[2] * f[3], reverse=True)
    return faces_list


# ── 크롭 여백 계산 ─────────────────────────────────────────────────────────
def _calc_crop_box(
    x: int, y: int, w: int, h: int,
    img_w: int, img_h: int,
) -> Tuple[int, int, int, int]:
    """
    얼굴 bounding box 기준 여백 적용:
      위 40% / 아래 180% / 좌우 60%
    3:4 비율 강제.
    """
    pad_top    = int(h * 0.40)
    pad_bottom = int(h * 1.80)
    pad_side   = int(w * 0.60)

    cx = x + w // 2
    cy = y + h // 2

    # 세로 우선
    half_h = (h + pad_top + pad_bottom) // 2
    half_w = int(half_h * 3 / 4)  # 3:4 비율 → w = h * 3/4

    top    = max(0, cy - pad_top)
    bottom = min(img_h, cy + pad_bottom)
    left   = max(0, cx - half_w)
    right  = min(img_w, cx + half_w)

    # 비율 재조정
    crop_h = bottom - top
    crop_w = right  - left
    target_w = int(crop_h * 3 / 4)
    if crop_w != target_w:
        diff = target_w - crop_w
        left  = max(0, left - diff // 2)
        right = min(img_w, left + target_w)

    return int(left), int(top), int(right), int(bottom)


# ── 메인 크롭 함수 ─────────────────────────────────────────────────────────
def crop_face(
    src_path: Path,
    out_path: Path | None = None,
    manual_box: Tuple[int, int, int, int] | None = None,
) -> bytes:
    """
    얼굴 크롭 + 리사이즈 + EXIF 제거.

    Returns:
        bytes: 300x400px JPEG (150dpi)

    Raises:
        FaceNotFoundError: 얼굴 미감지 (manual_box 없을 때)
    """
    img = _load_image_pil(src_path)

    # EXIF orientation 반영
    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == "Orientation":
                break
        exif = dict(img._getexif().items()) if hasattr(img, "_getexif") and img._getexif() else {}
        orient = exif.get(orientation, 1)
        rotate_map = {3: 180, 6: 270, 8: 90}
        if orient in rotate_map:
            img = img.rotate(rotate_map[orient], expand=True)
    except Exception:
        pass

    img_w, img_h = img.size

    if manual_box:
        # 수동 영역 선택
        left, top, right, bottom = manual_box
    else:
        faces = detect_faces(img)
        if not faces:
            raise FaceNotFoundError(
                f"얼굴을 감지하지 못했습니다: {src_path.name}"
            )
        x, y, w, h = faces[0]  # 가장 큰 얼굴
        left, top, right, bottom = _calc_crop_box(x, y, w, h, img_w, img_h)

    cropped = img.crop((left, top, right, bottom))
    resized = cropped.resize((300, 400), Image.LANCZOS)
    clean   = _strip_exif(resized.convert("RGB"))

    buf = io.BytesIO()
    clean.save(buf, format="JPEG", quality=92, dpi=(150, 150))
    data = buf.getvalue()

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(data)

    return data


# ── bytes 입력 크롭 (PDF 내장 이미지용) ───────────────────────────────────
def crop_face_from_bytes(
    image_bytes: bytes,
    out_path: Path | None = None,
) -> bytes:
    """
    bytes로 전달된 이미지에서 얼굴 크롭.
    PDF 내장 이미지 처리에 사용.

    Returns:
        bytes: 300x400px JPEG (150dpi)

    Raises:
        FaceNotFoundError: 얼굴 미감지
    """
    img = Image.open(io.BytesIO(image_bytes))
    img.load()
    img = img.convert("RGB")
    img_w, img_h = img.size

    faces = detect_faces(img)
    if not faces:
        raise FaceNotFoundError("얼굴을 감지하지 못했습니다 (내장 이미지)")

    x, y, w, h = faces[0]
    left, top, right, bottom = _calc_crop_box(x, y, w, h, img_w, img_h)

    cropped = img.crop((left, top, right, bottom))
    resized = cropped.resize((300, 400), Image.LANCZOS)
    clean   = _strip_exif(resized)

    buf = io.BytesIO()
    clean.save(buf, format="JPEG", quality=92, dpi=(150, 150))
    data = buf.getvalue()

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(data)

    return data


# ── CLI ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("사용법: python face_crop.py <이미지 경로> [출력경로]")
        sys.exit(1)

    src = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else src.parent / f"{src.stem}_crop.jpg"

    try:
        data = crop_face(src, out)
        print(f"크롭 완료: {out} ({len(data)//1024}KB)")
    except FaceNotFoundError as e:
        print(f"[ERROR] {e}")
        print("수동 영역 선택이 필요합니다.")
        sys.exit(2)
