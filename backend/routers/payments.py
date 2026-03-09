"""
BRIDGE Payments Router
======================
결제 관련 FastAPI 라우터.

PAYMENT_ENABLED=false 상태에서는 모든 엔드포인트가 503을 반환합니다.
실제 결제 처리는 backend/utils/payment.py 에 위임합니다.

관리자 인증: api_server.py의 _check_admin 패턴과 동일하게
            x-admin-key 헤더 + ADMIN_API_KEY 환경변수 사용.
"""

import os
import hmac
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from backend.utils.payment import (
    PaymentDisabledError,
    PaymentError,
    create_portone_payment_intent,
    verify_portone_payment,
    create_stripe_payment_intent,
    verify_portone_webhook,
    verify_stripe_webhook,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/payments", tags=["payments"])

_DB = os.path.join(os.path.dirname(__file__), "..", "..", "master.db")
_ADMIN_KEY = os.getenv("ADMIN_API_KEY", "")
_PAYMENT_ENABLED = os.getenv("PAYMENT_ENABLED", "false").lower() == "true"


# ──────────────────────────────────────────
# 내부 헬퍼
# ──────────────────────────────────────────

def _guard_enabled() -> None:
    if not _PAYMENT_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="결제 기능이 비활성화되어 있습니다. (PAYMENT_ENABLED=false)",
        )


def _check_admin(request: Request) -> None:
    """x-admin-key 헤더 검증 (api_server.py의 _check_admin과 동일 패턴)."""
    if not _ADMIN_KEY:
        raise HTTPException(status_code=503, detail="관리자 기능이 비활성화되어 있습니다.")
    provided = request.headers.get("x-admin-key", "").strip()
    if not hmac.compare_digest(provided, _ADMIN_KEY.strip()):
        raise HTTPException(status_code=403, detail="관리자 키가 올바르지 않습니다.")


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB)
    conn.row_factory = sqlite3.Row
    return conn


def _insert_payment(
    candidate_id: str,
    employer_id: int | None,
    amount: int,
    currency: str,
    payment_type: str,
    description: str,
    status: str = "pending",
) -> int:
    with _db() as conn:
        cur = conn.execute(
            """
            INSERT INTO payments
                (candidate_id, employer_id, amount, currency,
                 payment_type, description, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate_id,
                employer_id,
                amount,
                currency,
                payment_type,
                description,
                status,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        return cur.lastrowid


def _update_payment_status(payment_id: int, status: str) -> None:
    confirmed_at = datetime.now(timezone.utc).isoformat() if status == "paid" else None
    with _db() as conn:
        conn.execute(
            "UPDATE payments SET status=?, confirmed_at=? WHERE id=?",
            (status, confirmed_at, payment_id),
        )
        conn.commit()


# ──────────────────────────────────────────
# Pydantic 모델
# ──────────────────────────────────────────

class PortoneIntentRequest(BaseModel):
    order_id: str
    amount: int
    candidate_id: str
    currency: str = "KRW"
    name: str = "BRIDGE 서비스"

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("amount는 0보다 커야 합니다.")
        return v


class PortoneVerifyRequest(BaseModel):
    imp_uid: str
    merchant_uid: str
    amount: int
    payment_id: int


class StripeIntentRequest(BaseModel):
    amount: int
    candidate_id: str
    currency: str = "krw"
    employer_id: int | None = None
    description: str = "BRIDGE 서비스"

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("amount는 0보다 커야 합니다.")
        return v


class StripeVerifyRequest(BaseModel):
    payment_intent_id: str
    payment_id: int


# ──────────────────────────────────────────
# PortOne 엔드포인트
# ──────────────────────────────────────────

@router.post("/portone/intent")
async def portone_create_intent(body: PortoneIntentRequest) -> dict[str, Any]:
    """
    PortOne 결제 예약 메타데이터 생성.
    프론트엔드는 이 응답값을 IMP.request_pay()에 전달합니다.

    인증 불필요 (공개 엔드포인트 — 금액은 서버에서 검증).
    """
    _guard_enabled()
    try:
        intent = await create_portone_payment_intent(
            amount=body.amount,
            order_id=body.order_id,
            candidate_id=body.candidate_id,
            currency=body.currency,
            name=body.name,
        )
        # DB에 pending 상태로 사전 등록
        payment_id = _insert_payment(
            candidate_id=body.candidate_id,
            employer_id=None,
            amount=body.amount,
            currency=body.currency,
            payment_type="portone",
            description=body.name,
            status="pending",
        )
        intent["payment_id"] = payment_id
        return intent
    except PaymentDisabledError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except PaymentError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/portone/verify")
async def portone_verify(body: PortoneVerifyRequest) -> dict[str, Any]:
    """
    PortOne 결제 완료 검증 (프론트엔드 결제 후 호출).
    금액 불일치 시 즉시 실패.
    """
    _guard_enabled()
    try:
        await verify_portone_payment(body.imp_uid, body.amount)
        _update_payment_status(body.payment_id, "paid")
        log.info("[PortOne] 결제 확인: payment_id=%d", body.payment_id)
        return {"status": "paid", "payment_id": body.payment_id}
    except PaymentDisabledError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except PaymentError as e:
        _update_payment_status(body.payment_id, "failed")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/portone/webhook")
async def portone_webhook(request: Request) -> dict[str, str]:
    """PortOne 서버→서버 웹훅 수신 (서명 검증)."""
    _guard_enabled()
    body = await request.body()
    sig = request.headers.get("X-ImpWebhook-Signature", "")
    try:
        verify_portone_webhook(body, sig)
    except PaymentError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # 웹훅 페이로드 처리는 여기에 추가
    log.info("[PortOne] 웹훅 수신 및 서명 검증 성공")
    return {"status": "ok"}


# ──────────────────────────────────────────
# Stripe 엔드포인트
# ──────────────────────────────────────────

@router.post("/stripe/intent")
async def stripe_create_intent(body: StripeIntentRequest) -> dict[str, Any]:
    """
    Stripe PaymentIntent 생성.
    client_secret을 반환 → 프론트엔드에서 stripe.confirmPayment() 호출.
    """
    _guard_enabled()
    try:
        metadata = {"candidate_id": body.candidate_id}
        pi = await create_stripe_payment_intent(
            amount=body.amount,
            currency=body.currency,
            metadata=metadata,
        )
        payment_id = _insert_payment(
            candidate_id=body.candidate_id,
            employer_id=body.employer_id,
            amount=body.amount,
            currency=body.currency.upper(),
            payment_type="stripe",
            description=body.description,
            status="pending",
        )
        return {
            "client_secret": pi["client_secret"],
            "payment_intent_id": pi["id"],
            "payment_id": payment_id,
        }
    except PaymentDisabledError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except PaymentError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request) -> dict[str, str]:
    """Stripe 서버→서버 웹훅 수신 (서명 검증)."""
    _guard_enabled()
    payload = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    try:
        event = verify_stripe_webhook(payload, sig)
    except PaymentError as e:
        raise HTTPException(status_code=400, detail=str(e))

    event_type = event.get("type", "")
    log.info("[Stripe] 웹훅 수신: type=%s", event_type)

    if event_type == "payment_intent.succeeded":
        pi_id = event["data"]["object"]["id"]
        log.info("[Stripe] 결제 성공: payment_intent_id=%s", pi_id)
        # TODO: payment_id 조회 후 _update_payment_status 호출

    return {"status": "ok"}


# ──────────────────────────────────────────
# 관리자 전용 엔드포인트
# ──────────────────────────────────────────

@router.get("/admin/list")
async def admin_list_payments(request: Request) -> dict[str, Any]:
    """결제 내역 조회 (관리자 전용)."""
    _check_admin(request)
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT id, candidate_id, employer_id, amount, currency,
                   status, payment_type, description, created_at, confirmed_at
            FROM payments
            ORDER BY created_at DESC
            LIMIT 200
            """
        ).fetchall()
    return {"payments": [dict(r) for r in rows], "total": len(rows)}
