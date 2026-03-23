"""
secure_backup.py — AES-256-GCM 파일 암호화 백업/복원
====================================================
security_vault.py 의 암호화 엔진을 재사용하여
민감한 파일을 암호화된 상태로 백업.

암호화 키: .env BRIDGE_FIELD_KEY (SHA-256 → 32byte)

사용법:
  # 암호화 백업 (파일 → .enc)
  python tools/secure_backup.py encrypt <source_file> <dest_file.enc>

  # 복호화 복원 (.enc → 파일)
  python tools/secure_backup.py decrypt <source_file.enc> <dest_file>

  # 전체 민감 파일 일괄 백업
  python tools/secure_backup.py backup-all [--dest Q:/Claudework/bridge backup/env]

  # 일괄 복원
  python tools/secure_backup.py restore-all [--src Q:/Claudework/bridge backup/env]
"""

import os
import sys
import base64
import hashlib
import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

NONCE_SIZE = 12

# ── 암호화 대상 민감 파일 목록 ────────────────────────────────────────────
SENSITIVE_FILES = [
    PROJECT_ROOT / ".env",
    PROJECT_ROOT / ".bridge.key",
    PROJECT_ROOT / ".secrets.enc.json",
    PROJECT_ROOT / "web_frontend" / ".env.local",
    PROJECT_ROOT / "web_frontend" / ".env.production",
]

DEFAULT_BACKUP_DIR = Path("Q:/Claudework/bridge backup/env")


def _derive_key() -> bytes:
    raw = os.environ.get("BRIDGE_FIELD_KEY", "").strip()
    if not raw:
        raise EnvironmentError(
            "BRIDGE_FIELD_KEY is not set or empty. Check your .env file."
        )
    return hashlib.sha256(raw.encode("utf-8")).digest()


def encrypt_file(src: Path, dst: Path):
    """파일을 읽어서 AES-256-GCM 암호화 후 저장."""
    data = src.read_bytes()
    key = _derive_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(NONCE_SIZE)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    # 헤더: BRIDGE_ENC_V1 매직바이트 + 원본 파일명 길이 + 원본 파일명
    fname = src.name.encode("utf-8")
    header = b"BRIDGE_ENC_V1\x00" + len(fname).to_bytes(2, "big") + fname
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(header + nonce + ciphertext)
    return len(data), len(header + nonce + ciphertext)


def decrypt_file(src: Path, dst: Path):
    """암호화된 파일을 복호화 후 저장."""
    raw = src.read_bytes()
    # 헤더 파싱
    magic = b"BRIDGE_ENC_V1\x00"
    if not raw.startswith(magic):
        raise ValueError(f"Invalid encrypted file: missing BRIDGE_ENC_V1 header")
    pos = len(magic)
    fname_len = int.from_bytes(raw[pos:pos + 2], "big")
    pos += 2
    original_name = raw[pos:pos + fname_len].decode("utf-8")
    pos += fname_len
    # 암호화 데이터
    nonce = raw[pos:pos + NONCE_SIZE]
    ciphertext = raw[pos + NONCE_SIZE:]
    key = _derive_key()
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(plaintext)
    return original_name, len(plaintext)


def backup_all(dest_dir: Path = DEFAULT_BACKUP_DIR):
    """모든 민감 파일을 암호화하여 백업."""
    ts = datetime.datetime.now().strftime("%Y%m%d")
    dest_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for src in SENSITIVE_FILES:
        if not src.exists():
            results.append((src.name, "SKIP (not found)"))
            continue
        stem = src.name.replace(".", "_")
        dst = dest_dir / f"{stem}_{ts}.enc"
        orig_size, enc_size = encrypt_file(src, dst)
        results.append((src.name, f"OK ({orig_size}B → {enc_size}B) → {dst.name}"))
    return results


def restore_all(src_dir: Path = DEFAULT_BACKUP_DIR, dest_dir: Path = None):
    """암호화된 백업 파일을 복호화하여 복원."""
    if dest_dir is None:
        dest_dir = PROJECT_ROOT
    results = []
    for enc_file in sorted(src_dir.glob("*.enc")):
        try:
            original_name, size = decrypt_file(enc_file, dest_dir / "restored" / enc_file.stem)
            results.append((enc_file.name, f"OK → {original_name} ({size}B)"))
        except Exception as e:
            results.append((enc_file.name, f"FAIL: {e}"))
    return results


def verify_encrypted(path: Path) -> bool:
    """암호화된 파일의 무결성 검증 (복호화 시도)."""
    raw = path.read_bytes()
    magic = b"BRIDGE_ENC_V1\x00"
    if not raw.startswith(magic):
        return False
    try:
        pos = len(magic)
        fname_len = int.from_bytes(raw[pos:pos + 2], "big")
        pos += 2 + fname_len
        nonce = raw[pos:pos + NONCE_SIZE]
        ciphertext = raw[pos + NONCE_SIZE:]
        key = _derive_key()
        aesgcm = AESGCM(key)
        aesgcm.decrypt(nonce, ciphertext, None)
        return True
    except Exception:
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python secure_backup.py encrypt <src> <dst.enc>")
        print("  python secure_backup.py decrypt <src.enc> <dst>")
        print("  python secure_backup.py backup-all [--dest DIR]")
        print("  python secure_backup.py restore-all [--src DIR]")
        print("  python secure_backup.py verify <file.enc>")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "encrypt" and len(sys.argv) >= 4:
        src, dst = Path(sys.argv[2]), Path(sys.argv[3])
        orig, enc = encrypt_file(src, dst)
        print(f"Encrypted: {src.name} ({orig}B) → {dst.name} ({enc}B)")

    elif cmd == "decrypt" and len(sys.argv) >= 4:
        src, dst = Path(sys.argv[2]), Path(sys.argv[3])
        name, size = decrypt_file(src, dst)
        print(f"Decrypted: {src.name} → {name} ({size}B)")

    elif cmd == "backup-all":
        dest = Path(sys.argv[3]) if len(sys.argv) >= 4 and sys.argv[2] == "--dest" else DEFAULT_BACKUP_DIR
        print(f"Encrypting sensitive files → {dest}\n")
        for name, status in backup_all(dest):
            print(f"  {name:30s} {status}")
        print(f"\nDone. Verify with: python secure_backup.py verify <file.enc>")

    elif cmd == "restore-all":
        src = Path(sys.argv[3]) if len(sys.argv) >= 4 and sys.argv[2] == "--src" else DEFAULT_BACKUP_DIR
        print(f"Decrypting from {src}\n")
        for name, status in restore_all(src):
            print(f"  {name:30s} {status}")

    elif cmd == "verify" and len(sys.argv) >= 3:
        path = Path(sys.argv[2])
        if verify_encrypted(path):
            print(f"VALID: {path.name} — decryption OK")
        else:
            print(f"INVALID: {path.name} — cannot decrypt")
            sys.exit(1)

    else:
        print("Unknown command. Use: encrypt | decrypt | backup-all | restore-all | verify")
        sys.exit(1)


if __name__ == "__main__":
    main()
