"""
security.py — BRIDGE Resume Converter
- processing\ 임시파일: AES-256-GCM 암호화
- 처리 완료 후 임시파일 3-pass overwrite 삭제
- 로그: timestamp/teacher_id/file_count/status 만 기록 (PII 절대 미기록)
"""

from __future__ import annotations

import os
import json
import struct
import hashlib
import logging
import secrets
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

log = logging.getLogger("security")

# ── 키 로드 ────────────────────────────────────────────────────────────────
_KEY_PATHS = [
    Path("Q:/Claudework/bridge base/.bridge.key"),
    Path(__file__).parent / ".rc_key",
]

def _load_key() -> bytes:
    """기존 .bridge.key 재사용 → 없으면 새 키 생성 후 .rc_key 저장."""
    for kp in _KEY_PATHS:
        if kp.exists():
            raw = kp.read_bytes()
            if len(raw) >= 32:
                return raw[:32]

    # 새 키 생성
    key = secrets.token_bytes(32)
    rc_key = Path(__file__).parent / ".rc_key"
    rc_key.write_bytes(key)
    rc_key.chmod(0o600)
    log.info(f"새 암호화 키 생성: {rc_key}")
    return key

_KEY: bytes = _load_key()


# ── AES-256-GCM 암호화 ────────────────────────────────────────────────────
_MAGIC = b"RC01"  # Resume Converter v1

def encrypt_file(src: Path, dst: Optional[Path] = None) -> Path:
    """
    src 파일을 AES-256-GCM으로 암호화.
    dst가 없으면 src.enc 생성.
    """
    if dst is None:
        dst = src.with_suffix(src.suffix + ".enc")

    plaintext = src.read_bytes()
    aesgcm    = AESGCM(_KEY)
    nonce     = secrets.token_bytes(12)
    ct        = aesgcm.encrypt(nonce, plaintext, None)

    # 포맷: magic(4) + nonce(12) + ciphertext
    dst.write_bytes(_MAGIC + nonce + ct)
    log.debug(f"암호화: {src.name} → {dst.name}")
    return dst

def decrypt_file(src: Path, dst: Optional[Path] = None) -> Path:
    """AES-256-GCM 복호화."""
    data = src.read_bytes()
    if not data.startswith(_MAGIC):
        raise ValueError(f"잘못된 암호화 파일: {src.name}")

    nonce     = data[4:16]
    ct        = data[16:]
    aesgcm    = AESGCM(_KEY)
    plaintext = aesgcm.decrypt(nonce, ct, None)

    if dst is None:
        stem = src.stem  # .enc 제거
        dst  = src.parent / stem

    dst.write_bytes(plaintext)
    log.debug(f"복호화: {src.name} → {dst.name}")
    return dst

def encrypt_bytes(plaintext: bytes) -> bytes:
    """bytes 암호화 → bytes."""
    aesgcm = AESGCM(_KEY)
    nonce  = secrets.token_bytes(12)
    ct     = aesgcm.encrypt(nonce, plaintext, None)
    return _MAGIC + nonce + ct

def decrypt_bytes(data: bytes) -> bytes:
    """bytes 복호화 → bytes."""
    if not data.startswith(_MAGIC):
        raise ValueError("잘못된 암호화 데이터")
    nonce = data[4:16]
    ct    = data[16:]
    return AESGCM(_KEY).decrypt(nonce, ct, None)


# ── 3-pass 삭제 ────────────────────────────────────────────────────────────
def secure_delete(path: Path) -> bool:
    """
    3-pass overwrite + 파일 삭제.
    Pass 1: 0x00 / Pass 2: 0xFF / Pass 3: 랜덤
    """
    if not path.exists():
        return False

    try:
        size = path.stat().st_size
        with open(str(path), "rb+") as f:
            for pattern in (b"\x00", b"\xff", None):
                f.seek(0)
                if pattern:
                    f.write(pattern * size)
                else:
                    f.write(secrets.token_bytes(size))
                f.flush()
                os.fsync(f.fileno())
        path.unlink()
        log.debug(f"안전 삭제: {path.name}")
        return True
    except Exception as e:
        log.error(f"안전 삭제 실패 {path}: {e}")
        return False

def secure_delete_dir(dir_path: Path) -> int:
    """폴더 내 모든 파일 안전 삭제. 삭제된 파일 수 반환."""
    count = 0
    if not dir_path.exists():
        return 0
    for f in dir_path.rglob("*"):
        if f.is_file():
            if secure_delete(f):
                count += 1
    try:
        dir_path.rmdir()
    except Exception:
        pass
    return count


# ── 처리 로그 (PII-free) ───────────────────────────────────────────────────
_LOG_PATH = Path(__file__).parent / "logs" / "processing.jsonl"
_LOG_PATH.parent.mkdir(exist_ok=True)

def log_processing(
    teacher_id:     str,
    file_count:     int,
    status:         str,
    pii_removed:    int = 0,
    output_size_kb: int = 0,
):
    """PII 없이 처리 이벤트 기록 (JSONL)."""
    from datetime import datetime
    record = {
        "ts":            datetime.now().isoformat(timespec="seconds"),
        "teacher_id":    teacher_id,
        "file_count":    file_count,
        "status":        status,
        "pii_removed":   pii_removed,
        "output_size_kb": output_size_kb,
    }
    with open(str(_LOG_PATH), "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ── SHA-256 무결성 해시 ────────────────────────────────────────────────────
def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(str(path), "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ── CLI ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys, tempfile
    if len(sys.argv) < 2:
        print("사용법: python security.py <파일경로>")
        sys.exit(1)

    src = Path(sys.argv[1])
    enc = encrypt_file(src)
    print(f"암호화: {enc}")

    dec = decrypt_file(enc, src.parent / ("dec_" + src.name))
    print(f"복호화: {dec}")

    # 복호화 결과 검증
    assert src.read_bytes() == dec.read_bytes(), "복호화 불일치!"
    print("검증 OK")

    # 안전 삭제 테스트
    test = Path(tempfile.mktemp(suffix=".tmp"))
    test.write_bytes(b"test data" * 1000)
    secure_delete(test)
    print(f"안전삭제 OK: {test.exists()}")
