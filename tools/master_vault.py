"""
MasterVault v3.0 — Session-Ephemeral Zero-Plaintext Vault
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
보안 계층:
  1. 마스터 키 → Windows Credential Manager (디스크 절대 미저장)
  2. 세션 키 → PBKDF2-SHA256 (600,000 iterations) + 32-byte 랜덤 salt
  3. 시크릿 → AES-256-GCM + 12-byte 랜덤 nonce (매 호출 다른 ciphertext)
  4. 세션 회전 → 매 초기화마다 새 salt → vault 파일이 세션마다 완전히 달라짐
  5. 메모리 소각 → ctypes 제로필

사용법:
  from tools.master_vault import get_secret, MasterVault
  key = get_secret("BRIDGE_FIELD_KEY")   # env var 우선, 없으면 vault

CLI:
  python tools/master_vault.py setup        # 전체 키 초기 등록
  python tools/master_vault.py seal KEY     # 단일 키 등록
  python tools/master_vault.py list         # 키 목록
  python tools/master_vault.py rotate       # 강제 재암호화
  python tools/master_vault.py test KEY     # 키 테스트 (값 미표시)
  python tools/master_vault.py delete KEY   # 키 삭제
"""

import os
import json
import base64
import ctypes
import secrets
import getpass
import sys
from pathlib import Path
from typing import Optional

try:
    import keyring
    _KEYRING = True
except ImportError:
    _KEYRING = False

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# ── 상수 ────────────────────────────────────────────────────────────────────
VAULT_SERVICE  = "BRIDGE_MASTER_VAULT_V3"
VAULT_ACCOUNT  = "session_master"
VAULT_FILE     = Path(__file__).resolve().parent.parent / ".vault.enc.json"
KDF_ITERATIONS = 600_000      # NIST SP 800-132 2023 권장
NONCE_BYTES    = 12           # AES-GCM 96-bit nonce (NIST 권장)
SALT_BYTES     = 32           # 256-bit session salt
FALLBACK_SALT  = b"BRIDGE_MV3_FALLBACK_SALT_2026"


class MasterVault:
    """
    세션 에페머럴 제로평문 볼트.

    매 __init__마다:
      - 새 32-byte session_salt 생성
      - 새 PBKDF2 파생키로 기존 vault 복호화 → 재암호화
      → vault 파일이 세션마다 완전히 다른 암호문
    """

    def __init__(self):
        self._sk:    Optional[bytes] = None   # 현재 session key
        self._salt:  Optional[bytes] = None   # 현재 session salt
        self._cache: dict = {}                # 복호화된 평문 (메모리만 존재)
        self._init_session()

    # ── 세션 초기화 ─────────────────────────────────────────────────────────

    def _init_session(self):
        """마스터키 로드 → 새 salt 생성 → 기존 vault 복호화 → 재암호화"""
        mk = self._load_master_key()
        new_salt = secrets.token_bytes(SALT_BYTES)
        new_sk   = self._kdf(mk, new_salt)

        old_data = self._read_vault()
        if old_data and "d" in old_data and "s" in old_data:
            old_salt = base64.b64decode(old_data["s"])
            old_sk   = self._kdf(mk, old_salt)
            for k, blob in old_data["d"].items():
                try:
                    self._cache[k] = self._dec(old_sk, blob)
                except Exception:
                    pass  # 손상된 엔트리 무시
            self._scrub(old_sk)

        self._sk   = new_sk
        self._salt = new_salt
        self._write_vault()
        self._scrub(mk)

    # ── 마스터키 로드/생성 ───────────────────────────────────────────────────

    def _load_master_key(self) -> bytes:
        """Windows Credential Manager → 없으면 자동 생성 저장"""
        if _KEYRING:
            stored = keyring.get_password(VAULT_SERVICE, VAULT_ACCOUNT)
            if stored:
                return base64.b64decode(stored)
            # 최초: 32-byte 랜덤 생성 → Credential Manager
            mk = secrets.token_bytes(32)
            keyring.set_password(
                VAULT_SERVICE, VAULT_ACCOUNT,
                base64.b64encode(mk).decode()
            )
            return mk
        else:
            # keyring 미설치 환경: getpass 폴백
            pwd = getpass.getpass("[MasterVault] 마스터 패스워드 입력: ").encode()
            mk = self._kdf(pwd, FALLBACK_SALT)
            self._scrub(pwd)
            return mk

    # ── PBKDF2-SHA256 키 파생 ────────────────────────────────────────────────

    @staticmethod
    def _kdf(material: bytes, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=KDF_ITERATIONS,
        )
        return kdf.derive(material)

    # ── AES-256-GCM 암호화/복호화 ────────────────────────────────────────────

    @staticmethod
    def _enc(sk: bytes, plaintext: str) -> dict:
        """매 호출마다 새 12-byte nonce → 동일 평문도 다른 암호문"""
        nonce = secrets.token_bytes(NONCE_BYTES)
        ct = AESGCM(sk).encrypt(nonce, plaintext.encode("utf-8"), None)
        return {
            "n": base64.b64encode(nonce).decode(),
            "c": base64.b64encode(ct).decode(),
        }

    @staticmethod
    def _dec(sk: bytes, blob: dict) -> str:
        nonce = base64.b64decode(blob["n"])
        ct    = base64.b64decode(blob["c"])
        return AESGCM(sk).decrypt(nonce, ct, None).decode("utf-8")

    # ── vault 파일 I/O ───────────────────────────────────────────────────────

    def _read_vault(self) -> Optional[dict]:
        if not VAULT_FILE.exists():
            return None
        try:
            with open(VAULT_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _write_vault(self):
        """_cache의 모든 값을 새 session key + 새 nonce로 암호화하여 저장"""
        encrypted = {k: self._enc(self._sk, v) for k, v in self._cache.items()}
        VAULT_FILE.parent.mkdir(parents=True, exist_ok=True)
        VAULT_FILE.write_text(
            json.dumps({
                "v": "3.0",
                "s": base64.b64encode(self._salt).decode(),
                "d": encrypted,
            }, indent=2),
            encoding="utf-8",
        )

    # ── 공개 API ─────────────────────────────────────────────────────────────

    def unseal(self, key_name: str) -> str:
        """
        시크릿 조회.
        1순위: os.getenv() — Render 프로덕션 환경변수 우선
        2순위: vault 메모리 캐시
        """
        ev = os.getenv(key_name)
        if ev:
            return ev
        if key_name not in self._cache:
            raise KeyError(
                f"[MasterVault] '{key_name}' 없음 → "
                f"python tools/master_vault.py seal {key_name}"
            )
        return self._cache[key_name]

    def seal(self, key_name: str, value: str = None):
        """시크릿 등록/갱신 (value=None이면 getpass 입력)"""
        if value is None:
            value = getpass.getpass(f"[MasterVault] {key_name} 입력: ")
        self._cache[key_name] = value
        self._write_vault()

    def delete(self, key_name: str):
        """시크릿 삭제"""
        self._cache.pop(key_name, None)
        self._write_vault()

    def list_keys(self) -> list:
        return sorted(self._cache.keys())

    def rotate(self):
        """강제 session 회전 (vault 파일 완전 재암호화)"""
        self._init_session()

    # ── 메모리 소각 ──────────────────────────────────────────────────────────

    @staticmethod
    def _scrub(data: bytes):
        """ctypes 제로필로 GC 전 메모리 소각 유도"""
        try:
            buf = (ctypes.c_char * len(data)).from_buffer_copy(data)
            ctypes.memset(buf, 0, len(data))
        except Exception:
            pass


# ── 싱글톤 편의 함수 ──────────────────────────────────────────────────────────

_singleton: Optional[MasterVault] = None


def get_secret(key_name: str) -> str:
    """
    통합 시크릿 조회.
    1순위: os.getenv (Render 프로덕션)
    2순위: MasterVault (로컬 개발)
    """
    ev = os.getenv(key_name)
    if ev:
        return ev
    global _singleton
    if _singleton is None:
        _singleton = MasterVault()
    return _singleton.unseal(key_name)


# ── CLI ───────────────────────────────────────────────────────────────────────

REQUIRED_KEYS: list[tuple[str, str]] = [
    # Bridge 핵심 (최우선)
    ("BRIDGE_FIELD_KEY",      "DB 필드 암호화키 — 절대 분실 금지 (DB 복호화 불가)"),
    ("SECRET_KEY",            "FastAPI 세션/JWT 서명키"),
    # AWS S3
    ("AWS_ACCESS_KEY_ID",     "AWS 접근키 ID"),
    ("AWS_SECRET_ACCESS_KEY", "AWS 시크릿 접근키"),
    ("S3_BUCKET_NAME",        "S3 버킷 이름"),
    ("S3_REGION",             "S3 리전 (예: ap-northeast-2)"),
    # AI
    ("ANTHROPIC_API_KEY",     "Anthropic Claude API 키"),
    ("OPENAI_API_KEY",        "OpenAI API 키 (선택)"),
    # SMTP
    ("SMTP_HOST",             "SMTP 호스트 (예: smtp.gmail.com)"),
    ("SMTP_PORT",             "SMTP 포트 (예: 587)"),
    ("SMTP_USER",             "SMTP 이메일 주소"),
    ("SMTP_PASS",             "SMTP 앱 비밀번호"),
    # Google Meet
    ("GOOGLE_CLIENT_ID",      "Google OAuth 클라이언트 ID"),
    ("GOOGLE_CLIENT_SECRET",  "Google OAuth 클라이언트 시크릿"),
    ("GOOGLE_CALENDAR_ID",    "Google 캘린더 ID"),
    # Telegram
    ("TELEGRAM_BOT_TOKEN",    "Telegram 봇 토큰"),
    ("TELEGRAM_CHAT_ID",      "Telegram 채팅 ID (숫자)"),
    # VAPID (PWA 푸시 알림)
    ("VAPID_PRIVATE_KEY",     "VAPID 개인키"),
    ("VAPID_PUBLIC_KEY",      "VAPID 공개키"),
    # ClaudeBlog 공유 키
    ("BRIDGE_NAVER_ID",       "네이버 블로그 아이디 (선택)"),
    ("BRIDGE_NAVER_PW",       "네이버 블로그 비밀번호 (선택)"),
]

_HELP = """
MasterVault v3.0 CLI
  setup        전체 키 초기 등록 (대화형)
  seal KEY     단일 키 등록/갱신
  list         저장된 키 목록
  rotate       강제 재암호화 (vault 파일 교체)
  test KEY     키 존재 및 길이 확인 (값 미표시)
  delete KEY   키 삭제
"""

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "help":
        print(_HELP)
        sys.exit(0)

    vault = MasterVault()

    if cmd == "setup":
        print("\n=== MasterVault v3.0 초기 설정 ===")
        print("⚠  BRIDGE_FIELD_KEY는 기존 값 그대로 입력 (변경 시 DB 복호화 불가)\n")
        existing = vault.list_keys()

        for key, desc in REQUIRED_KEYS:
            tag = "✓ [등록됨]" if key in existing else "  [없음]  "
            yn = input(f"{tag} {key}\n            {desc}\n            등록/갱신? (y/N): ").strip().lower()
            if yn == "y":
                value = getpass.getpass("  값 입력: ")
                if value.strip():
                    vault.seal(key, value)
                    print("  → 저장 완료\n")
                else:
                    print("  → 빈값, 건너뜀\n")
            else:
                print()

        print(f"\n완료. 총 저장: {len(vault.list_keys())}개")
        print(f"Vault 위치: {VAULT_FILE}")

    elif cmd == "seal":
        key = sys.argv[2] if len(sys.argv) > 2 else input("키 이름: ").strip()
        vault.seal(key)
        print(f"[OK] '{key}' 저장됨")

    elif cmd == "list":
        keys = vault.list_keys()
        print(f"\n[MasterVault v3] 저장된 키 — {len(keys)}개:")
        for k in keys:
            print(f"  ✓ {k}")

    elif cmd == "rotate":
        vault.rotate()
        print(f"[OK] 재암호화 완료 — {len(vault.list_keys())}개 키")

    elif cmd == "test":
        key = sys.argv[2] if len(sys.argv) > 2 else input("테스트 키 이름: ").strip()
        val = vault.unseal(key)
        print(f"[OK] {key} = (길이 {len(val)}자, 앞4자: {val[:4]}***)")

    elif cmd == "delete":
        key = sys.argv[2] if len(sys.argv) > 2 else input("삭제할 키 이름: ").strip()
        vault.delete(key)
        print(f"[OK] '{key}' 삭제됨")

    else:
        print(_HELP)
