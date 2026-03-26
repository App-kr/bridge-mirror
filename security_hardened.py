# security_hardened.py
# Bridge 강화 세션 바인딩 + Vault 연동 자동 키 교체
# api_server.py에서 import하여 _check_admin() 보완 용도로 사용

import logging
import secrets
import threading
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, Request

logger = logging.getLogger("bridge.security_hardened")

# ─── 감사 로그 ───────────────────────────────────────────────────────────
class AuditLog:
    """보안 이벤트 감사 로그 (append-only JSONL)."""
    def __init__(self, log_path: str = "Q:/Claudework/bridge base/bridge_security.log"):
        self._path = Path(log_path)
        self._lock = threading.Lock()

    def write(self, event: str, detail: dict) -> None:
        record = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "event": event,
            "detail": detail,
        }
        with self._lock:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.info(f"[AUDIT] {event}: {detail}")


audit_log = AuditLog()


# ─── 세션 바인딩 ─────────────────────────────────────────────────────────
class SessionBinding:
    """
    IP /24 서브넷 + User-Agent 핑거프린트 기반 세션 바인딩.
    세션 이상(핑거프린트 불일치) 감지 시:
      - 해당 세션 즉시 폐기
      - vault_controller.rotate_on_session_anomaly() 호출 → 3중 키 교체
      - 모든 세션 강제 만료 (revoke_all)
    """
    def __init__(self, session_ttl: int = 28800):  # 8시간
        self._sessions: dict = {}
        self._lock = threading.Lock()
        self._ttl = session_ttl

    def _fingerprint(self, request: Request) -> str:
        """IP /24 서브넷 + UA 앞 50자로 핑거프린트 생성."""
        ip = request.client.host if request.client else "unknown"
        # /24 서브넷
        parts = ip.split(".")
        subnet = ".".join(parts[:3]) + ".0" if len(parts) == 4 else ip
        ua = request.headers.get("User-Agent", "")[:50]
        return f"{subnet}|{ua}"

    def create(self, request: Request) -> str:
        """새 세션 발급. 토큰 반환."""
        token = secrets.token_urlsafe(32)
        fp = self._fingerprint(request)
        now = time.time()
        with self._lock:
            # 만료 세션 정리
            expired = [k for k, v in self._sessions.items() if v["expires"] < now]
            for k in expired:
                del self._sessions[k]
            self._sessions[token] = {
                "fingerprint": fp,
                "created": now,
                "expires": now + self._ttl,
            }
        return token

    def validate(self, session_id: str, request: Request, vault_controller=None) -> bool:
        s = self._sessions.get(session_id)
        if not s:
            return False
        if datetime.utcnow().timestamp() > s["expires"]:
            with self._lock:
                self._sessions.pop(session_id, None)
            return False
        if self._fingerprint(request) != s["fingerprint"]:
            ip = request.client.host if request.client else "unknown"
            logging.error(
                f"[SECURITY] Session anomaly detected. "
                f"session={session_id[:8]}... ip={ip}. "
                f"Triggering immediate key rotation."
            )
            with self._lock:
                self._sessions.pop(session_id, None)
            # ── 핵심: 세션 이상 → 3중 키 즉시 교체 트리거 ──
            if vault_controller is not None:
                vault_controller.rotate_on_session_anomaly(trigger_ip=ip)
                # 모든 세션 강제 만료
                self.revoke_all()
            return False
        # 슬라이딩 갱신
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id]["expires"] = time.time() + self._ttl
        return True

    def revoke(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def revoke_all(self) -> int:
        with self._lock:
            count = len(self._sessions)
            self._sessions.clear()
            logger.warning(f"[SECURITY] All {count} sessions revoked.")
            return count

    def list_sessions(self) -> list:
        now = time.time()
        with self._lock:
            return [
                {
                    "token_prefix": k[:8] + "...",
                    "created": datetime.fromtimestamp(v["created"]).isoformat(),
                    "expires": datetime.fromtimestamp(v["expires"]).isoformat(),
                    "active": v["expires"] > now,
                }
                for k, v in self._sessions.items()
            ]


session_binding = SessionBinding()


# ─── FastAPI Dependency — Vault 연동 require_auth ────────────────────────
async def require_auth(request: Request):
    from security_vault import get_vault
    session_id = request.cookies.get("session_id")
    if not session_id:
        audit_log.write("UNAUTH_ACCESS", {
            "ip": request.client.host if request.client else "unknown",
            "path": str(request.url.path),
            "reason": "no_session_cookie"
        })
        raise HTTPException(status_code=401, detail="인증이 필요합니다")
    vault = get_vault()
    if not session_binding.validate(session_id, request, vault_controller=vault):
        audit_log.write("SESSION_INVALID_OR_ANOMALY", {
            "ip": request.client.host if request.client else "unknown",
            "path": str(request.url.path),
        })
        raise HTTPException(status_code=401, detail="세션이 만료되었거나 유효하지 않습니다")
    return session_id
