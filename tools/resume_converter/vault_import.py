"""
vault_import.py — BRIDGE Resume Converter
Google 서비스계정 JSON → 3중 암호화 vault 임포트

암호화 스택:
  L1: Argon2id KDF (t=3, m=65536, p=4) → 32-byte 서브키
  L2: ChaCha20-Poly1305 (32-byte subkey1, 12-byte nonce1)
  L3: AES-256-GCM     (32-byte subkey2, 12-byte nonce2)
  Master key: Windows Credential Manager (keyring) 재사용 (MasterVault와 동일 서비스)

저장: Q:\Claudework\.vault\gc_sa.enc
  포맷: magic(4) + version(1) + salt(32) + nonce1(12) + nonce2(12) + ciphertext

사용법:
  python vault_import.py              # GUI 모드
  python vault_import.py <json경로>   # CLI 모드
  python vault_import.py --test       # 복호화 테스트 (파일명만 출력)
"""

from __future__ import annotations

import ctypes
import json
import os
import secrets
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional

import keyring
from argon2.low_level import hash_secret_raw, Type as Argon2Type
from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305

# ── 상수 ──────────────────────────────────────────────────────────────────
MAGIC        = b"GCS1"      # Google Credentials Sealed v1
VERSION      = b"\x01"
VAULT_DIR    = Path("Q:/Claudework/.vault")
VAULT_FILE   = VAULT_DIR / "gc_sa.enc"

# Argon2id 파라미터 (OWASP 2023 권장 이상)
ARGON2_T      = 3           # time cost
ARGON2_M      = 65_536      # memory cost (64 MB)
ARGON2_P      = 4           # parallelism
ARGON2_HASH_LEN = 64        # 64바이트 → subkey1(32) + subkey2(32) 분리

SALT_BYTES   = 32
NONCE_BYTES  = 12

# MasterVault와 동일 서비스명 (같은 마스터키 재사용)
_KR_SERVICE  = "BRIDGE_MASTER_VAULT_V3"
_KR_ACCOUNT  = "session_master"


# ── 마스터키 로드 ──────────────────────────────────────────────────────────
def _load_master_key() -> bytes:
    """
    Windows Credential Manager에서 MasterVault 마스터키 로드.
    없으면 새로 생성 (MasterVault 초기화 미완료 상태).
    """
    import base64
    stored = keyring.get_password(_KR_SERVICE, _KR_ACCOUNT)
    if stored:
        return base64.b64decode(stored)
    # 새 마스터키 생성 (MasterVault와 동기화)
    mk = secrets.token_bytes(32)
    keyring.set_password(_KR_SERVICE, _KR_ACCOUNT, base64.b64encode(mk).decode())
    return mk


# ── 메모리 소각 ────────────────────────────────────────────────────────────
def _scrub(data: bytes | bytearray) -> None:
    """ctypes 제로필로 메모리 소각 유도."""
    try:
        if isinstance(data, bytearray):
            for i in range(len(data)):
                data[i] = 0
        else:
            buf = (ctypes.c_char * len(data)).from_buffer_copy(data)
            ctypes.memset(buf, 0, len(data))
    except Exception:
        pass


# ── Argon2id 키 파생 ───────────────────────────────────────────────────────
def _derive_keys(master_key: bytes, salt: bytes) -> tuple[bytes, bytes]:
    """
    Argon2id(master_key, salt) → 64바이트
      → subkey1(0:32) for ChaCha20-Poly1305
      → subkey2(32:64) for AES-256-GCM
    """
    derived = hash_secret_raw(
        secret=master_key,
        salt=salt,
        time_cost=ARGON2_T,
        memory_cost=ARGON2_M,
        parallelism=ARGON2_P,
        hash_len=ARGON2_HASH_LEN,
        type=Argon2Type.ID,
    )
    subkey1 = bytes(derived[:32])
    subkey2 = bytes(derived[32:64])
    _scrub(derived)
    return subkey1, subkey2


# ── 3중 암호화 ─────────────────────────────────────────────────────────────
def _encrypt(plaintext: bytes, master_key: bytes) -> bytes:
    """
    plaintext → 3중 암호화 바이너리

    포맷: magic(4) + version(1) + salt(32) + nonce1(12) + nonce2(12) + ciphertext
    """
    salt   = secrets.token_bytes(SALT_BYTES)
    nonce1 = secrets.token_bytes(NONCE_BYTES)
    nonce2 = secrets.token_bytes(NONCE_BYTES)

    subkey1, subkey2 = _derive_keys(master_key, salt)

    try:
        # L2: ChaCha20-Poly1305
        ct1 = ChaCha20Poly1305(subkey1).encrypt(nonce1, plaintext, None)
        # L3: AES-256-GCM
        ct2 = AESGCM(subkey2).encrypt(nonce2, ct1, None)
    finally:
        _scrub(subkey1)
        _scrub(subkey2)

    return MAGIC + VERSION + salt + nonce1 + nonce2 + ct2


# ── 3중 복호화 ─────────────────────────────────────────────────────────────
def _decrypt(data: bytes, master_key: bytes) -> bytes:
    """
    gc_sa.enc 바이너리 → 복호화된 plaintext bytes

    Raises:
        ValueError: magic/version 불일치
        cryptography.exceptions.InvalidTag: 키 또는 데이터 오류
    """
    if not data[:4] == MAGIC:
        raise ValueError(f"잘못된 파일 형식 (magic={data[:4]})")
    if data[4:5] != VERSION:
        raise ValueError(f"지원하지 않는 버전: {data[4:5]}")

    offset = 5
    salt   = data[offset : offset + SALT_BYTES];    offset += SALT_BYTES
    nonce1 = data[offset : offset + NONCE_BYTES];   offset += NONCE_BYTES
    nonce2 = data[offset : offset + NONCE_BYTES];   offset += NONCE_BYTES
    ct2    = data[offset:]

    subkey1, subkey2 = _derive_keys(master_key, salt)
    try:
        ct1   = AESGCM(subkey2).decrypt(nonce2, ct2, None)
        plain = ChaCha20Poly1305(subkey1).decrypt(nonce1, ct1, None)
        return plain
    finally:
        _scrub(subkey1)
        _scrub(subkey2)


# ── 3-pass 원본 삭제 ───────────────────────────────────────────────────────
def _secure_delete(path: Path) -> None:
    """3-pass overwrite → 삭제."""
    if not path.exists():
        return
    size = path.stat().st_size
    with open(str(path), "rb+") as f:
        for pattern in (b"\x00", b"\xff", None):
            f.seek(0)
            f.write(pattern * size if pattern else secrets.token_bytes(size))
            f.flush()
            os.fsync(f.fileno())
    path.unlink()


# ── 임포트 실행 ────────────────────────────────────────────────────────────
def import_service_account(json_path: Path) -> None:
    """
    서비스계정 JSON → gc_sa.enc 저장 + 원본 3-pass 삭제.

    Raises:
        ValueError: 유효하지 않은 JSON
        RuntimeError: 마스터키 없음
    """
    # 1. JSON 읽기 + 검증 (메모리만)
    raw = json_path.read_bytes()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"유효하지 않은 JSON: {e}")

    # 서비스계정 필수 필드 확인
    required = {"type", "project_id", "private_key_id", "private_key", "client_email"}
    missing = required - set(parsed.keys())
    if missing:
        raise ValueError(f"서비스계정 JSON 필수 필드 없음: {missing}")

    if parsed.get("type") != "service_account":
        raise ValueError("type이 'service_account'가 아닙니다")

    # 2. 마스터키 로드
    mk = _load_master_key()
    try:
        # 3. 암호화
        encrypted = _encrypt(raw, mk)
    finally:
        _scrub(mk)
        # raw bytes는 GC에 맡김 (bytearray 아니므로 직접 소각 불가)

    # 4. vault 폴더 생성 + 저장
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    VAULT_FILE.write_bytes(encrypted)

    # 5. 원본 3-pass 삭제
    _secure_delete(json_path)


# ── 런타임 복호화 (sheets_connector 전용) ─────────────────────────────────
_cached_creds: Optional[dict] = None

def load_service_account_dict() -> dict:
    """
    gc_sa.enc 복호화 → dict 반환 (메모리만 존재).
    디스크에 JSON 재생성 없음.

    Returns:
        서비스계정 dict (google.oauth2.service_account.Credentials 직접 주입용)

    Raises:
        FileNotFoundError: gc_sa.enc 없음
        RuntimeError: 복호화 실패
    """
    global _cached_creds
    if _cached_creds is not None:
        return _cached_creds

    if not VAULT_FILE.exists():
        raise FileNotFoundError(
            f"gc_sa.enc 없음: {VAULT_FILE}\n"
            "run_vault_import.bat 을 먼저 실행하세요."
        )

    mk = _load_master_key()
    try:
        raw     = VAULT_FILE.read_bytes()
        plain   = _decrypt(raw, mk)
        result  = json.loads(plain)
        _cached_creds = result
        return result
    except Exception as e:
        raise RuntimeError(f"서비스계정 복호화 실패: {e}")
    finally:
        _scrub(mk)


def clear_cached_creds() -> None:
    """세션 종료 시 메모리 캐시 소각."""
    global _cached_creds
    if _cached_creds is not None:
        # dict 내 민감 필드 덮어쓰기
        for key in ("private_key", "private_key_id", "client_email"):
            if key in _cached_creds:
                try:
                    _cached_creds[key] = "\x00" * len(_cached_creds[key])
                except Exception:
                    pass
        _cached_creds = None


# ── 설정값 저장/로드 (keyring 기반) ────────────────────────────────────────
_KR_CONFIG_SERVICE = "BRIDGE_RC_CONFIG_V1"


def save_config_value(key: str, value: str) -> None:
    """
    소규모 설정값을 Windows Credential Manager에 저장.
    key 예: 'sheet_id', 'anthropic_api_key'
    """
    keyring.set_password(_KR_CONFIG_SERVICE, key, value)


def load_config_value(key: str) -> Optional[str]:
    """Windows Credential Manager에서 설정값 로드. 없으면 None."""
    return keyring.get_password(_KR_CONFIG_SERVICE, key)


# ── GUI 모드 ───────────────────────────────────────────────────────────────
def run_gui() -> None:
    root = tk.Tk()
    root.withdraw()  # 메인 창 숨김

    # 파일 선택
    json_path_str = filedialog.askopenfilename(
        title="Google 서비스계정 JSON 파일 선택",
        filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")],
        initialdir=str(Path.home()),
    )

    if not json_path_str:
        messagebox.showinfo("취소", "파일을 선택하지 않았습니다.")
        return

    json_path = Path(json_path_str)

    try:
        import_service_account(json_path)
        messagebox.showinfo(
            "저장 완료",
            f"✅ 저장 완료. 원본 파일 삭제됨.\n\n"
            f"저장 위치: {VAULT_FILE}\n"
            f"원본: {json_path.name} → 3-pass 삭제 완료\n\n"
            f"이후 프로그램은 gc_sa.enc를 메모리에서만 사용합니다.",
        )
    except FileNotFoundError:
        messagebox.showerror("오류", f"파일을 찾을 수 없습니다:\n{json_path}")
    except ValueError as e:
        messagebox.showerror("JSON 오류", str(e))
    except Exception as e:
        messagebox.showerror("오류", f"임포트 실패:\n{e}")
    finally:
        root.destroy()


# ── CLI 모드 ───────────────────────────────────────────────────────────────
def run_cli(args: list[str]) -> None:
    if "--test" in args:
        # 복호화 테스트 (값 미표시)
        if not VAULT_FILE.exists():
            print(f"[NG] gc_sa.enc 없음: {VAULT_FILE}")
            sys.exit(1)
        try:
            creds = load_service_account_dict()
            print(f"[OK] 복호화 성공")
            print(f"     project_id:   {creds.get('project_id', '?')}")
            print(f"     client_email: {creds.get('client_email', '?')[:20]}...")
            print(f"     type:         {creds.get('type', '?')}")
            clear_cached_creds()
        except Exception as e:
            print(f"[NG] 복호화 실패: {e}")
            sys.exit(1)
        return

    json_path_str = args[0] if args else None
    if not json_path_str:
        print("사용법:")
        print("  python vault_import.py                # GUI 파일 선택")
        print("  python vault_import.py <json경로>     # CLI 직접 지정")
        print("  python vault_import.py --test         # 복호화 테스트")
        sys.exit(0)

    json_path = Path(json_path_str)
    if not json_path.exists():
        print(f"[오류] 파일 없음: {json_path}")
        sys.exit(1)

    try:
        import_service_account(json_path)
        print(f"[OK] 저장 완료: {VAULT_FILE}")
        print(f"[OK] 원본 삭제: {json_path.name}")
    except Exception as e:
        print(f"[오류] {e}")
        sys.exit(1)


# ── 진입점 ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cli_args = sys.argv[1:]
    if cli_args:
        run_cli(cli_args)
    else:
        run_gui()
