"""
Push Notification API — Web Push (VAPID) 알림
=============================================
- POST /api/admin/push/subscribe     — 구독 등록
- DELETE /api/admin/push/unsubscribe — 구독 해제
- POST /api/admin/push/test          — 테스트 알림 발송
- GET  /api/admin/push/vapid-key     — VAPID 공개키 조회
- POST /api/admin/push/broadcast     — 전체 알림 발송 (내부용)

의존성: pywebpush (RFC 8291 암호화 + VAPID 서명)
"""

import json
import logging
import os
import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

_log = logging.getLogger("bridge.push")

router = APIRouter(prefix="/api/admin/push", tags=["push"])

# ── DB ──
_DB_PATH = Path(os.getenv("DB_PATH", str(Path(__file__).resolve().parent / "master.db")))


def _db():
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_push_tables():
    conn = _db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint TEXT NOT NULL UNIQUE,
            p256dh TEXT NOT NULL,
            auth TEXT NOT NULL,
            user_agent TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_used TEXT DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()


try:
    _ensure_push_tables()
except Exception as _e:
    _log.warning("push_subscriptions 테이블 생성 실패: %s", _e)


# ── VAPID ──
def _get_vapid_keys():
    """환경변수 또는 bx에서 VAPID 키 로드."""
    pub = os.getenv("VAPID_PUBLIC_KEY", "")
    priv_pem = os.getenv("VAPID_PRIVATE_KEY_PEM", "")

    if not pub or not priv_pem:
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parent / "tools"))
            from bx import _read as bx_read
            pub = pub or bx_read("VAPID_PUBLIC_KEY") or ""
            priv_pem = priv_pem or bx_read("VAPID_PRIVATE_KEY_PEM") or ""
        except Exception:
            pass

    return pub, priv_pem


# ── Auth helper ──
def _check_admin(request: Request):
    key = request.headers.get("x-admin-key", "")
    if not key:
        raise HTTPException(401, "Admin key required")


def ok(data=None, message="ok"):
    return {"success": True, "data": data, "message": message}


# ── Models ──
class PushSubscription(BaseModel):
    endpoint: str = Field(..., min_length=10, max_length=2000)
    keys: dict = Field(...)  # { p256dh, auth }


class PushMessage(BaseModel):
    title: str = Field("BRIDGE", max_length=200)
    body: str = Field("New notification", max_length=1000)
    url: str = Field("/admin/m", max_length=500)


# ── Endpoints ──

@router.get("/vapid-key")
async def get_vapid_key():
    """VAPID 공개키 반환 (인증 불필요 — 구독 시 사용)."""
    pub, _ = _get_vapid_keys()
    if not pub:
        raise HTTPException(500, "VAPID key not configured")
    return ok(data={"publicKey": pub})


@router.post("/subscribe")
async def subscribe(body: PushSubscription, request: Request):
    """Push 구독 등록."""
    _check_admin(request)

    p256dh = body.keys.get("p256dh", "")
    auth = body.keys.get("auth", "")
    if not p256dh or not auth:
        raise HTTPException(400, "Missing p256dh or auth keys")

    ua = request.headers.get("user-agent", "")[:200]
    conn = _db()
    try:
        conn.execute("""
            INSERT INTO push_subscriptions (endpoint, p256dh, auth, user_agent)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(endpoint) DO UPDATE SET
                p256dh = excluded.p256dh,
                auth = excluded.auth,
                user_agent = excluded.user_agent,
                last_used = CURRENT_TIMESTAMP,
                is_active = 1
        """, (body.endpoint, p256dh, auth, ua))
        conn.commit()
    finally:
        conn.close()

    _log.info("Push subscription registered: %s...", body.endpoint[:50])
    return ok(message="Subscribed")


@router.delete("/unsubscribe")
async def unsubscribe(request: Request):
    """Push 구독 해제."""
    _check_admin(request)
    try:
        body = await request.json()
        endpoint = body.get("endpoint", "")
    except Exception:
        raise HTTPException(400, "Invalid JSON")

    if not endpoint:
        raise HTTPException(400, "endpoint required")

    conn = _db()
    try:
        conn.execute(
            "UPDATE push_subscriptions SET is_active = 0 WHERE endpoint = ?",
            (endpoint,),
        )
        conn.commit()
    finally:
        conn.close()

    return ok(message="Unsubscribed")


@router.post("/test")
async def test_push(request: Request):
    """테스트 알림 발송."""
    _check_admin(request)
    count = send_push_to_all(
        title="BRIDGE Test",
        body="Push notification is working!",
        url="/admin/m",
    )
    return ok(data={"sent": count}, message=f"Test sent to {count} subscribers")


@router.post("/broadcast")
async def broadcast(body: PushMessage, request: Request):
    """전체 알림 브로드캐스트."""
    _check_admin(request)
    count = send_push_to_all(title=body.title, body=body.body, url=body.url)
    return ok(data={"sent": count}, message=f"Broadcast sent to {count} subscribers")


# ── Web Push Sender (pywebpush — RFC 8291 암호화) ──

def send_push(endpoint: str, p256dh: str, auth: str, payload: dict) -> bool:
    """단일 구독자에게 Push 발송 (pywebpush 사용)."""
    pub_key, priv_pem = _get_vapid_keys()
    if not pub_key or not priv_pem:
        _log.warning("VAPID keys not configured, skip push")
        return False

    try:
        from pywebpush import webpush, WebPushException

        subscription_info = {
            "endpoint": endpoint,
            "keys": {"p256dh": p256dh, "auth": auth},
        }

        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=priv_pem,
            vapid_claims={"sub": "mailto:admin@bridgejob.co.kr"},
            ttl=86400,
        )
        return True
    except Exception as exc:
        exc_str = str(exc)
        # 404/410 = subscription expired
        if "404" in exc_str or "410" in exc_str:
            conn = _db()
            try:
                conn.execute(
                    "UPDATE push_subscriptions SET is_active = 0 WHERE endpoint = ?",
                    (endpoint,),
                )
                conn.commit()
            finally:
                conn.close()
            _log.info("Push subscription expired, deactivated: %s...", endpoint[:50])
        else:
            _log.warning("Push failed: %s | endpoint: %s...", exc_str[:200], endpoint[:50])
        return False


def send_push_to_all(title: str, body: str, url: str = "/admin/m") -> int:
    """모든 활성 구독자에게 Push 발송."""
    conn = _db()
    try:
        rows = conn.execute(
            "SELECT endpoint, p256dh, auth FROM push_subscriptions WHERE is_active = 1"
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return 0

    payload = {"title": title, "body": body, "url": url}
    sent = 0
    for row in rows:
        if send_push(row["endpoint"], row["p256dh"], row["auth"], payload):
            sent += 1

    _log.info("Push broadcast: %d/%d sent", sent, len(rows))
    return sent
