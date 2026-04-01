"""
BRIDGE DB 암호화 백업 도구 v1.0
master.db ↔ master.db.enc (AES-256-GCM)

사용법:
  # 암호화 (백업 생성)
  "Q:/Phtyon 3/python.exe" tools/db_backup_enc.py encrypt

  # 복호화 (복원)
  "Q:/Phtyon 3/python.exe" tools/db_backup_enc.py decrypt

  # 무결성 검증
  "Q:/Phtyon 3/python.exe" tools/db_backup_enc.py verify

암호화 키: BRIDGE_FIELD_KEY (BX 크리덴셜 스토어에서 자동 로드)
출력 파일: master.db.enc (git 추적 대상)
원본 파일: master.db (.gitignore — git 미추적)
"""

import sys
import os
import hashlib
import struct
import json
from pathlib import Path

# ── 경로 설정 ──────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent.parent
DB_PATH    = BASE_DIR / "master.db"
ENC_PATH   = BASE_DIR / "master.db.enc"
META_PATH  = BASE_DIR / "master.db.enc.meta"

# ── 암호화 포맷 ────────────────────────────────────────────────
# magic(4) + version(1) + salt(16) + nonce(12) + sha256(32) + ciphertext
MAGIC   = b"BRGE"
VERSION = 1


def _get_key() -> bytes:
    """BRIDGE_FIELD_KEY 로드 (BX → 환경변수 → 입력 순서)"""
    # 1) BX 크리덴셜 스토어
    try:
        bx_path = BASE_DIR / "tools" / "bx.py"
        if bx_path.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("bx", bx_path)
            bx = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bx)
            val = bx.get("BRIDGE_FIELD_KEY")
            if val:
                return val.encode() if isinstance(val, str) else val
    except Exception:
        pass

    # 2) 환경변수
    val = os.environ.get("BRIDGE_FIELD_KEY", "")
    if val:
        return val.encode()

    # 3) 직접 입력
    import getpass
    val = getpass.getpass("BRIDGE_FIELD_KEY 입력: ").strip()
    if not val:
        print("❌ 키가 없습니다. 중단합니다.")
        sys.exit(1)
    return val.encode()


def _derive_key(raw_key: bytes, salt: bytes) -> bytes:
    """PBKDF2-HMAC-SHA256 키 유도 (600,000 iterations)"""
    return hashlib.pbkdf2_hmac("sha256", raw_key, salt, 600_000, dklen=32)


def cmd_encrypt(_=None):
    """master.db → master.db.enc"""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if not DB_PATH.exists():
        print(f"❌ {DB_PATH} 없음")
        sys.exit(1)

    raw_key = _get_key()
    salt    = os.urandom(16)
    nonce   = os.urandom(12)
    aes_key = _derive_key(raw_key, salt)

    plaintext = DB_PATH.read_bytes()
    sha256    = hashlib.sha256(plaintext).digest()   # 무결성용
    ciphertext = AESGCM(aes_key).encrypt(nonce, plaintext, None)

    with open(ENC_PATH, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("B", VERSION))
        f.write(salt)
        f.write(nonce)
        f.write(sha256)
        f.write(ciphertext)

    # 메타 파일 (평문 — 복원 안내용)
    meta = {
        "created": __import__("datetime").datetime.now().isoformat(),
        "db_size": len(plaintext),
        "enc_size": ENC_PATH.stat().st_size,
        "sha256_hex": sha256.hex(),
        "format": "BRGE-v1-AES256GCM-PBKDF2-600k",
    }
    META_PATH.write_text(json.dumps(meta, indent=2, ensure_ascii=False))

    print(f"✅ 암호화 완료")
    print(f"   원본: {DB_PATH} ({len(plaintext):,} bytes)")
    print(f"   출력: {ENC_PATH} ({ENC_PATH.stat().st_size:,} bytes)")
    print(f"   SHA256: {sha256.hex()[:16]}…")


def cmd_decrypt(_=None):
    """master.db.enc → master.db (복원)"""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if not ENC_PATH.exists():
        print(f"❌ {ENC_PATH} 없음")
        sys.exit(1)

    raw_key = _get_key()

    data = ENC_PATH.read_bytes()
    if data[:4] != MAGIC:
        print("❌ 파일 포맷 오류 (MAGIC 불일치)")
        sys.exit(1)

    version = data[4]
    if version != VERSION:
        print(f"❌ 버전 불일치: 예상 {VERSION}, 실제 {version}")
        sys.exit(1)

    salt       = data[5:21]
    nonce      = data[21:33]
    sha256_ref = data[33:65]
    ciphertext = data[65:]

    aes_key = _derive_key(raw_key, salt)

    try:
        plaintext = AESGCM(aes_key).decrypt(nonce, ciphertext, None)
    except Exception:
        print("❌ 복호화 실패 — 키가 틀렸거나 파일이 손상됐습니다")
        sys.exit(1)

    # 무결성 검증
    sha256_actual = hashlib.sha256(plaintext).digest()
    if sha256_actual != sha256_ref:
        print("❌ SHA256 불일치 — 파일 손상 가능성")
        sys.exit(1)

    # 기존 DB 백업
    if DB_PATH.exists():
        bak = DB_PATH.with_suffix(".db.restore_bak")
        DB_PATH.rename(bak)
        print(f"   기존 DB 백업: {bak}")

    DB_PATH.write_bytes(plaintext)
    print(f"✅ 복원 완료")
    print(f"   출력: {DB_PATH} ({len(plaintext):,} bytes)")
    print(f"   SHA256 검증: OK")


def cmd_verify(_=None):
    """master.db.enc 무결성 확인 (복호화 없이 헤더만 검증)"""
    if not ENC_PATH.exists():
        print(f"❌ {ENC_PATH} 없음")
        sys.exit(1)

    data = ENC_PATH.read_bytes()
    ok = data[:4] == MAGIC and data[4] == VERSION
    size = ENC_PATH.stat().st_size

    print(f"{'✅' if ok else '❌'} MAGIC: {'OK' if ok else 'FAIL'}")
    print(f"   버전: {data[4] if len(data) > 4 else '?'}")
    print(f"   크기: {size:,} bytes")

    if META_PATH.exists():
        meta = json.loads(META_PATH.read_text())
        print(f"   생성일: {meta.get('created','?')}")
        print(f"   원본 SHA256: {meta.get('sha256_hex','?')[:16]}…")

    if not ok:
        sys.exit(1)


COMMANDS = {
    "encrypt": cmd_encrypt,
    "decrypt": cmd_decrypt,
    "verify":  cmd_verify,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("사용법: db_backup_enc.py [encrypt|decrypt|verify]")
        sys.exit(1)
    COMMANDS[sys.argv[1]](sys.argv[2:])
