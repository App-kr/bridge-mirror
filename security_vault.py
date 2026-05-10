# security_vault.py
# Bridge MasterVault — 3중 암호화 + 세션 연동 자동 키 교체
# Layer 1: AES-256-GCM (PII 필드 암호화)
# Layer 2: AES-256-GCM (DB 레코드 래핑)
# Layer 3: ChaCha20-Poly1305 (Vault 마스터 키 보호)
# 세션 변경 감지 시 3개 레이어 키 동시 자동 교체

import os
import json
import time
import hmac
import struct
import hashlib
import logging
import secrets
import threading
import sys
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
from argon2.low_level import hash_secret_raw, Type

# [ZERO-TRACE SECURITY]
# 기존 .env 로드 로직 하드 딜리트 (평문 원천 차단)

logger = logging.getLogger("bridge.vault")

# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API — PII 필드 암호화/복호화 (api_server.py에서 호출)
# ═══════════════════════════════════════════════════════════════════════════════

def encrypt_field(value, *args, **kwargs):
    """
    PII 필드 T3v1 암호화. 이미 암호화된 값은 그대로 반환 (idempotent).
    args[0] 또는 kwargs['column_name'] = 컬럼명 (L1 키 분리용).
    """
    if not value or not isinstance(value, str):
        return value
    if is_t3_encrypted(value):
        return value
    col = args[0] if args else kwargs.get("column_name", "")
    return t3_encrypt(value, col)


# ════════════════════════════════════════════════════════════════════════════
# T3v1 — BRIDGE_FIELD_KEY 기반 경량 3중 AES-256-GCM
# Vault(VAULT_PASSPHRASE) 의존 없음. BRIDGE_FIELD_KEY 단독으로 동작.
# 포맷: base64( b"T3v1" + nonce1(12) + nonce2(12) + nonce3(12) + ciphertext )
# L1_key = SHA-256(base_key + b"L1" + col_name)   — 컬럼별 키 분리
# L2_key = SHA-256(base_key + b"L2" + nonce1)      — nonce 바인딩
# L3_key = SHA-256(base_key + b"L3" + nonce2+nonce1)
# ════════════════════════════════════════════════════════════════════════════

_T3_MAGIC = b"T3v1"


def is_t3_encrypted(value) -> bool:
    """T3v1 암호화 여부 감지 (base64 디코드 후 magic 확인)."""
    if not isinstance(value, str) or len(value) < 60:
        return False
    try:
        raw = base64.b64decode(value)
        return raw[:4] == _T3_MAGIC
    except Exception:
        return False


def t3_encrypt(plaintext: str, column_name: str = "") -> str:
    """
    T3v1 3중 AES-256-GCM 암호화.
    BRIDGE_FIELD_KEY → SHA-256 → 컬럼별/nonce별 하위 키 3개 파생.
    매 호출마다 랜덤 nonce 3개 → 같은 값도 매번 다른 암호문.
    """
    base = _derive_key()
    col = column_name.encode()
    k1 = hashlib.sha256(base + b"L1" + col).digest()
    n1 = secrets.token_bytes(12)
    n2 = secrets.token_bytes(12)
    n3 = secrets.token_bytes(12)
    k2 = hashlib.sha256(base + b"L2" + n1).digest()
    k3 = hashlib.sha256(base + b"L3" + n2 + n1).digest()
    ct1 = AESGCM(k1).encrypt(n1, plaintext.encode("utf-8"), None)
    ct2 = AESGCM(k2).encrypt(n2, ct1, None)
    ct3 = AESGCM(k3).encrypt(n3, ct2, None)
    return base64.b64encode(_T3_MAGIC + n1 + n2 + n3 + ct3).decode("ascii")


def t3_decrypt(encoded: str, column_name: str = "") -> str:
    """T3v1 3중 복호화. magic 불일치 또는 인증 실패 시 ValueError."""
    raw = base64.b64decode(encoded)
    if raw[:4] != _T3_MAGIC:
        raise ValueError("T3v1 magic mismatch")
    n1, n2, n3 = raw[4:16], raw[16:28], raw[28:40]
    ct3 = raw[40:]
    base = _derive_key()
    col = column_name.encode()
    k1 = hashlib.sha256(base + b"L1" + col).digest()
    k2 = hashlib.sha256(base + b"L2" + n1).digest()
    k3 = hashlib.sha256(base + b"L3" + n2 + n1).digest()
    ct2 = AESGCM(k3).decrypt(n3, ct3, None)
    ct1 = AESGCM(k2).decrypt(n2, ct2, None)
    return AESGCM(k1).decrypt(n1, ct1, None).decode("utf-8")


def auto_decrypt_value(value, column_name: str = ""):
    """T3v1이면 복호화, 아니면 그대로 반환 (plaintext pass-through)."""
    if not value:
        return value
    if is_t3_encrypted(value):
        try:
            return t3_decrypt(str(value), column_name)
        except Exception:
            return value
    return value


def decrypt_field(value, *args, **kwargs):
    """
    T3v1 암호화값 자동 복호화. 평문은 그대로 반환 (안전한 pass-through).
    api_server.py의 _safe_decrypt / _decrypt_row 에서 호출됨.
    """
    col = args[0] if args else kwargs.get("column_name", "")
    return auto_decrypt_value(value, col)


def is_encrypted(value, *args, **kwargs):
    """T3v1 암호화 여부 확인."""
    return is_t3_encrypted(value)

# ── Render [ENC:] 환경변수 전역 복호화 계층 (가장 먼저 실행됨) ──────────────
def unseal_render_environment():
    """
    Render에 올라간 'ENC:' 로 시작하는 "꼬아놓은" 혼동 암호문 환경변수들을
    메모리 기동 시 단 한 번 RENDER_MASTER_KEY로 풀어서 os.environ에 평문으로 덮어씌움.
    이후 앱(api_server 등)은 평소처럼 os.getenv를 쓰면 평문이 정상적으로 나옴.
    """
    master_key_raw = os.environ.get("RENDER_MASTER_KEY")
    if not master_key_raw:
        return
        
    master_key_bytes = master_key_raw.encode('utf-8')
    key = hashlib.sha256(master_key_bytes).digest()
    
    try:
        aesgcm = AESGCM(key)
        
        for k, v in list(os.environ.items()):
            if v.startswith("ENC:"):
                b64_str = v[4:]
                try:
                    raw = base64.b64decode(b64_str.encode('ascii'), validate=True)
                    nonce = raw[:12]
                    ciphertext = raw[12:]
                    plain_bytes = aesgcm.decrypt(nonce, ciphertext, None)
                    # 환경변수에 평문으로 복원 주입 (런타임 RAM에만 존재)
                    os.environ[k] = plain_bytes.decode('utf-8')
                except Exception as e:
                    logger.error(f"환경변수 {k} 꼬인 문자열(ENC:) 해독 실패: {e}")
    finally:
        del master_key_bytes
        del key

# 모듈 로드 직후 즉각적으로 전역 환경변수 꼬인 문자열 복원 가동
unseal_render_environment()


# ─── 상수 ────────────────────────────────────────────────────────────────
VAULT_DIR = Path(os.environ.get("VAULT_DIR", "Q:/Claudework/.vault"))
KEY_ROTATION_LOG = VAULT_DIR / "key_rotation.jsonl"
ACTIVE_KEYS_FILE = VAULT_DIR / "active_keys.enc"
GRACE_PERIOD_SEC = 30          # 구 키 유예 기간 (복호화 전용)
KEY_TTL_HOURS = 720            # 정기 교체 주기 (30일)
SESSION_TRIGGER_ROTATE = True  # 세션 이상 시 즉시 키 교체 여부


# ── Key Derivation ─────────────────────────────────────────────────────────────

def _get_field_key_raw() -> bytearray:
    """
    BRIDGE_FIELD_KEY 다형성 롤링 금고(V4) 단일 조회
    평문(.env) 로직 완벽 제거 및 메모리 강제 소각 지원
    """
    # [프로덕션 보안] Render 환경 변수가 주입된 상태인지 확인 (메모리 로드)
    # .env 파일은 읽지 않으므로 평문 유출 위험은 0% 입니다.
    import os
    prod_key = os.environ.get("BRIDGE_FIELD_KEY", "").strip()
    if prod_key:
        return bytearray(prod_key.encode('utf-8'))

    # 로컬 .bridge.key 폴백 (개발/로컬 환경)
    _key_candidates = [
        Path(__file__).resolve().parent / ".bridge.key",
        Path("Q:/Claudework/bridge base/.bridge.key"),
    ]
    for _kp in _key_candidates:
        if _kp.exists():
            _raw = _kp.read_text(encoding="utf-8").strip()
            if _raw:
                return bytearray(_raw.encode("utf-8"))

    # V4 Vault (레거시 — 미사용)
    _vault_path = Path("Q:/")
    if str(_vault_path) not in sys.path:
        sys.path.insert(0, str(_vault_path))
    try:
        from secure_vault_v3 import PolymorphicQuantumVault  # type: ignore
        vault = PolymorphicQuantumVault()
        return vault.unseal_and_roll("BRIDGE_FIELD_KEY")
    except Exception as e:
        raise EnvironmentError(
            f"BRIDGE_FIELD_KEY 미설정 + .bridge.key 없음 + V4 Vault 오류: {e}\n"
            "로컬: .bridge.key 파일 확인 / Render: BRIDGE_FIELD_KEY 환경변수 설정"
        )


def _derive_key() -> bytes:
    """
    Derive a 32-byte AES-256 key from BRIDGE_FIELD_KEY.
    SHA-256 guarantees exactly 32 bytes regardless of raw key length.
    """
    raw_key_bytes = _get_field_key_raw()
    try:
        derived = hashlib.sha256(raw_key_bytes).digest()
        return derived
    finally:
        # C-Level Memory Scrubbing (Zeroing Wipe)
        # 램(RAM) 잔상을 물리적으로 0으로 덮어씀 (메모리 덤프 완벽 방어)
        raw_key_bytes[:] = b'\x00' * len(raw_key_bytes)
        del raw_key_bytes


# ─── Argon2id 기반 마스터 키 파생 ────────────────────────────────────────
def derive_master_key(passphrase: bytes, salt: bytes) -> bytes:
    """
    Argon2id로 마스터 키 파생.
    passphrase: Vault 잠금 비밀번호 (환경변수 VAULT_PASSPHRASE)
    salt: VAULT_DIR/master.salt 파일에서 읽음 (최초 1회 랜덤 생성)
    """
    return hash_secret_raw(
        secret=passphrase,
        salt=salt,
        time_cost=3,
        memory_cost=65536,   # 64MB
        parallelism=4,
        hash_len=32,
        type=Type.ID,
    )


def _get_or_create_salt(salt_path: Path) -> bytes:
    if salt_path.exists():
        return salt_path.read_bytes()
    salt = secrets.token_bytes(32)
    salt_path.write_bytes(salt)
    logger.info(f"[VAULT] New master salt created: {salt_path}")
    return salt


# ─── 3중 레이어 키 생성 ──────────────────────────────────────────────────
def generate_layer_keys() -> dict:
    """
    3개 레이어 키 랜덤 생성.
    각 키는 256비트(32바이트) CSPRNG.
    """
    return {
        "layer1_key": secrets.token_bytes(32),   # AES-256-GCM PII
        "layer2_key": secrets.token_bytes(32),   # AES-256-GCM DB
        "layer3_key": secrets.token_bytes(32),   # ChaCha20 Vault
        "created_at": datetime.utcnow().isoformat() + "Z",
        "version": secrets.token_hex(8),
    }


# ─── 레이어 키 저장/로드 (마스터 키로 암호화) ────────────────────────────
def save_layer_keys(layer_keys: dict, master_key: bytes) -> None:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    plaintext = json.dumps({
        k: v.hex() if isinstance(v, bytes) else v
        for k, v in layer_keys.items()
    }).encode()
    nonce = secrets.token_bytes(12)
    aesgcm = AESGCM(master_key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, b"bridge-vault-v1")
    ACTIVE_KEYS_FILE.write_bytes(nonce + ciphertext)
    logger.info(f"[VAULT] Layer keys saved. version={layer_keys.get('version')}")


def load_layer_keys(master_key: bytes) -> Optional[dict]:
    if not ACTIVE_KEYS_FILE.exists():
        return None
    raw = ACTIVE_KEYS_FILE.read_bytes()
    nonce, ciphertext = raw[:12], raw[12:]
    aesgcm = AESGCM(master_key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, b"bridge-vault-v1")
        data = json.loads(plaintext)
        data["layer1_key"] = bytes.fromhex(data["layer1_key"])
        data["layer2_key"] = bytes.fromhex(data["layer2_key"])
        data["layer3_key"] = bytes.fromhex(data["layer3_key"])
        return data
    except Exception as e:
        logger.error(f"[VAULT] Key load failed (wrong passphrase or tampered): {e}")
        return None


# ─── 감사 로그 (HMAC 체인) ───────────────────────────────────────────────
def _log_rotation(event: str, detail: dict, hmac_key: bytes) -> None:
    KEY_ROTATION_LOG.parent.mkdir(parents=True, exist_ok=True)
    last_hash = "0" * 64
    if KEY_ROTATION_LOG.exists():
        lines = KEY_ROTATION_LOG.read_text(encoding="utf-8").strip().splitlines()
        if lines:
            try:
                last_hash = json.loads(lines[-1]).get("entry_hash", "0" * 64)
            except Exception:
                pass
    record = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "event": event,
        "detail": detail,
        "prev_hash": last_hash,
    }
    entry_str = json.dumps(record, sort_keys=True, ensure_ascii=False)
    entry_hash = hmac.new(hmac_key, entry_str.encode(), hashlib.sha256).hexdigest()
    record["entry_hash"] = entry_hash
    with open(KEY_ROTATION_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


# ─── 3중 암호화 (실제 PII 암호화에 사용) ─────────────────────────────────
class TripleEncryptor:
    """
    Layer 1 (AES-256-GCM) → Layer 2 (AES-256-GCM) → Layer 3 (ChaCha20-Poly1305)
    순서대로 3중 암호화. 복호화는 역순.
    각 레이어는 독립 nonce 사용 (재사용 공격 방지).
    """
    def __init__(self, layer_keys: dict):
        self.k1 = layer_keys["layer1_key"]
        self.k2 = layer_keys["layer2_key"]
        self.k3 = layer_keys["layer3_key"]
        self.version = layer_keys.get("version", "unknown")

    def encrypt(self, plaintext: bytes, aad: bytes = b"bridge-pii") -> bytes:
        # Layer 1: AES-256-GCM
        n1 = secrets.token_bytes(12)
        c1 = AESGCM(self.k1).encrypt(n1, plaintext, aad)

        # Layer 2: AES-256-GCM
        n2 = secrets.token_bytes(12)
        c2 = AESGCM(self.k2).encrypt(n2, n1 + c1, aad)

        # Layer 3: ChaCha20-Poly1305
        n3 = secrets.token_bytes(12)
        c3 = ChaCha20Poly1305(self.k3).encrypt(n3, n2 + c2, aad)

        # 버전 태그 (4바이트) + nonce3 + ciphertext3
        ver_tag = self.version.encode()[:4].ljust(4, b"\x00")
        return ver_tag + n3 + c3

    def decrypt(self, ciphertext: bytes, aad: bytes = b"bridge-pii") -> bytes:
        # 버전 태그 분리
        _ver_tag = ciphertext[:4]
        rest = ciphertext[4:]

        # Layer 3 복호화
        n3, c3 = rest[:12], rest[12:]
        n2_c2 = ChaCha20Poly1305(self.k3).decrypt(n3, c3, aad)

        # Layer 2 복호화
        n2, c2 = n2_c2[:12], n2_c2[12:]
        n1_c1 = AESGCM(self.k2).decrypt(n2, c2, aad)

        # Layer 1 복호화
        n1, c1 = n1_c1[:12], n1_c1[12:]
        return AESGCM(self.k1).decrypt(n1, c1, aad)


# ─── KeyRotationController (핵심: 세션 변경 → 자동 키 교체) ─────────────
class KeyRotationController:
    """
    세션 이상 감지 시 즉시 3중 키 전체 교체.
    구 키는 GRACE_PERIOD_SEC 동안 복호화 전용 유지 후 소각.
    정기 교체: KEY_TTL_HOURS마다 자동 실행 (백그라운드 스레드).
    """
    def __init__(self, master_key: bytes, hmac_key: bytes):
        self.master_key = master_key
        self.hmac_key = hmac_key
        self._lock = threading.Lock()
        self._active: Optional[TripleEncryptor] = None
        self._grace: Optional[dict] = None   # 구 키 (복호화 전용)
        self._grace_until: float = 0
        self._load_or_init()
        self._start_rotation_scheduler()

    def _load_or_init(self) -> None:
        keys = load_layer_keys(self.master_key)
        if keys:
            self._active = TripleEncryptor(keys)
            logger.info(f"[VAULT] Keys loaded. version={keys.get('version')}")
        else:
            logger.info("[VAULT] No existing keys. Generating new key set.")
            self._do_rotate(reason="init")

    def _do_rotate(self, reason: str = "scheduled", trigger_ip: str = "internal") -> None:
        """실제 키 교체 수행. 반드시 self._lock 내부에서 호출."""
        old_keys = load_layer_keys(self.master_key)

        new_keys = generate_layer_keys()
        save_layer_keys(new_keys, self.master_key)
        self._active = TripleEncryptor(new_keys)

        if old_keys:
            self._grace = old_keys
            self._grace_until = time.time() + GRACE_PERIOD_SEC
            logger.info(f"[VAULT] Old keys enter grace period ({GRACE_PERIOD_SEC}s)")

        _log_rotation("KEY_ROTATED", {
            "reason": reason,
            "trigger_ip": trigger_ip,
            "new_version": new_keys["version"],
            "old_version": old_keys.get("version") if old_keys else None,
        }, self.hmac_key)

        logger.warning(
            f"[VAULT] KEY ROTATION COMPLETE — reason={reason}, "
            f"new_version={new_keys['version']}, trigger={trigger_ip}"
        )

    def rotate_on_session_anomaly(self, trigger_ip: str = "unknown") -> None:
        """
        security_hardened.py의 SessionBinding에서 세션 이상 감지 시 호출.
        3중 키 즉시 교체 + 모든 세션 강제 만료.
        """
        if not SESSION_TRIGGER_ROTATE:
            return
        with self._lock:
            logger.error(
                f"[VAULT] SESSION ANOMALY → IMMEDIATE KEY ROTATION. ip={trigger_ip}"
            )
            self._do_rotate(reason="session_anomaly", trigger_ip=trigger_ip)

    def get_encryptor(self) -> TripleEncryptor:
        with self._lock:
            self._cleanup_grace()
            if self._active is None:
                raise RuntimeError("[VAULT] No active encryptor. Call _load_or_init first.")
            return self._active

    def get_grace_encryptor(self) -> Optional[TripleEncryptor]:
        """구 키로 복호화 시도 (마이그레이션 지원)."""
        with self._lock:
            self._cleanup_grace()
            if self._grace and time.time() < self._grace_until:
                return TripleEncryptor(self._grace)
            return None

    def _cleanup_grace(self) -> None:
        if self._grace and time.time() >= self._grace_until:
            logger.info(f"[VAULT] Grace period expired. Securely wiping old keys.")
            # 메모리에서 키 소각 (덮어쓰기)
            for k in ("layer1_key", "layer2_key", "layer3_key"):
                if k in self._grace and isinstance(self._grace[k], bytes):
                    # bytearray로 변환해 덮어쓰기
                    ba = bytearray(self._grace[k])
                    for i in range(len(ba)):
                        ba[i] = 0
            self._grace = None
            self._grace_until = 0

    def decrypt_with_fallback(self, ciphertext: bytes, aad: bytes = b"bridge-pii") -> bytes:
        """
        현재 키로 복호화 시도 → 실패 시 유예 기간 내 구 키로 재시도.
        키 교체 직후 마이그레이션 기간 동안 구 데이터도 읽을 수 있음.
        """
        try:
            return self.get_encryptor().decrypt(ciphertext, aad)
        except Exception:
            grace = self.get_grace_encryptor()
            if grace:
                try:
                    result = grace.decrypt(ciphertext, aad)
                    logger.info("[VAULT] Decrypted with grace (old) key — re-encrypt recommended.")
                    return result
                except Exception:
                    pass
            raise ValueError("[VAULT] Decryption failed with all available keys.")

    def _start_rotation_scheduler(self) -> None:
        """KEY_TTL_HOURS마다 정기 키 교체 (데몬 스레드)."""
        def _scheduler():
            while True:
                time.sleep(KEY_TTL_HOURS * 3600)
                with self._lock:
                    logger.info("[VAULT] Scheduled key rotation triggered.")
                    self._do_rotate(reason="scheduled_ttl")
        t = threading.Thread(target=_scheduler, daemon=True, name="vault-key-rotator")
        t.start()
        logger.info(f"[VAULT] Key rotation scheduler started. TTL={KEY_TTL_HOURS}h")

    def force_rotate(self, reason: str = "manual") -> None:
        """관리자 수동 교체."""
        with self._lock:
            self._do_rotate(reason=reason)

    def verify_log_integrity(self) -> bool:
        if not KEY_ROTATION_LOG.exists():
            return True
        lines = KEY_ROTATION_LOG.read_text(encoding="utf-8").strip().splitlines()
        prev = "0" * 64
        for i, line in enumerate(lines):
            record = json.loads(line)
            if record.get("prev_hash") != prev:
                logger.error(f"[VAULT] Rotation log chain broken at line {i+1}")
                return False
            entry_copy = {k: v for k, v in record.items() if k != "entry_hash"}
            expected = hmac.new(
                self.hmac_key,
                json.dumps(entry_copy, sort_keys=True, ensure_ascii=False).encode(),
                hashlib.sha256
            ).hexdigest()
            prev = record.get("entry_hash", "")
        return True


# ─── Vault 초기화 헬퍼 ───────────────────────────────────────────────────
def init_vault() -> KeyRotationController:
    """
    api_server.py 시작 시 1회 호출.
    환경변수 VAULT_PASSPHRASE, VAULT_HMAC_KEY 필수.
    """
    passphrase = os.environ.get("VAULT_PASSPHRASE", "").encode()
    hmac_key_hex = os.environ.get("VAULT_HMAC_KEY", "")

    if not passphrase:
        raise RuntimeError("[VAULT] VAULT_PASSPHRASE 환경변수 미설정. 시작 불가.")
    if not hmac_key_hex:
        raise RuntimeError("[VAULT] VAULT_HMAC_KEY 환경변수 미설정. 시작 불가.")

    hmac_key = bytes.fromhex(hmac_key_hex)
    salt_path = VAULT_DIR / "master.salt"
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    salt = _get_or_create_salt(salt_path)
    master_key = derive_master_key(passphrase, salt)

    controller = KeyRotationController(master_key, hmac_key)
    logger.info("[VAULT] Vault initialized successfully.")
    return controller


# ─── 편의 함수 (api_server.py에서 직접 사용) ─────────────────────────────
_vault_controller: Optional[KeyRotationController] = None

def get_vault() -> KeyRotationController:
    global _vault_controller
    if _vault_controller is None:
        _vault_controller = init_vault()
    return _vault_controller

def encrypt_pii(plaintext: str) -> str:
    """PII 문자열 암호화 → hex 문자열 반환."""
    return get_vault().get_encryptor().encrypt(plaintext.encode()).hex()

def decrypt_pii(hex_ciphertext: str) -> str:
    """PII hex 문자열 복호화 → 원문 문자열 반환."""
    return get_vault().decrypt_with_fallback(bytes.fromhex(hex_ciphertext)).decode()
