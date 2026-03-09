"""
BRIDGE Payment Utilities
========================
PortOne(아임포트) + Stripe 결제 연동 유틸리티.

환경변수 (절대 하드코딩 금지):
    PORTONE_API_SECRET     : PortOne REST API 시크릿 키
    PORTONE_WEBHOOK_SECRET : PortOne 웹훅 서명 검증 키
    STRIPE_SECRET_KEY      : Stripe API 시크릿 키
    STRIPE_WEBHOOK_SECRET  : Stripe 웹훅 서명 시크릿
    PAYMENT_ENABLED        : "true"일 때만 결제 기능 활성화

Fail-Closed 원칙:
    - 환경변수 미설정 시 RuntimeError 발생 (로컬 fallback 없음)
    - 외부 API 오류 시 PaymentError 예외 전파
"""

import os
import hashlib
import hmac
import json
import logging
from typing import Any

import httpx

log = logging.getLogger(__name__)

# ──────────────────────────────────────────
# 예외 클래스
# ──────────────────────────────────────────

class PaymentError(Exception):
    """결제 처리 중 발생하는 모든 예외."""


class PaymentDisabledError(PaymentError):
    """PAYMENT_ENABLED=false 상태에서 결제 시도 시."""


# ──────────────────────────────────────────
# 환경변수 접근 헬퍼 (Fail-Closed)
# ──────────────────────────────────────────

def _require_env(key: str) -> str:
    """환경변수를 가져오되, 미설정이면 RuntimeError."""
    val = os.getenv(key, "").strip()
    if not val:
        raise RuntimeError(
            f"[BRIDGE Payment] 필수 환경변수 '{key}' 가 설정되지 않았습니다. "
            f".env 파일을 확인하세요."
        )
    return val


def _is_payment_enabled() -> bool:
    return os.getenv("PAYMENT_ENABLED", "false").lower() == "true"


def _guard_payment_enabled() -> None:
    if not _is_payment_enabled():
        raise PaymentDisabledError(
            "결제 기능이 비활성화되어 있습니다. PAYMENT_ENABLED=true 로 설정하세요."
        )


# ──────────────────────────────────────────
# PortOne (아임포트) 유틸리티
# ──────────────────────────────────────────

PORTONE_API_BASE = "https://api.iamport.kr"


async def _portone_access_token() -> str:
    """PortOne REST API 액세스 토큰 발급."""
    api_secret = _require_env("PORTONE_API_SECRET")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{PORTONE_API_BASE}/users/getToken",
            json={"imp_key": api_secret, "imp_secret": api_secret},
        )
    data = resp.json()
    if data.get("code") != 0:
        raise PaymentError(f"PortOne 토큰 발급 실패: {data.get('message')}")
    return data["response"]["access_token"]


async def create_portone_payment_intent(
    amount: int,
    order_id: str,
    candidate_id: str,
    *,
    currency: str = "KRW",
    name: str = "BRIDGE 서비스",
) -> dict[str, Any]:
    """
    PortOne 결제 예약 정보를 생성합니다.

    PortOne은 실제 결제를 프론트엔드 SDK가 처리하므로
    여기서는 결제 검증용 메타데이터를 반환합니다.

    Args:
        amount      : 결제 금액 (원 단위)
        order_id    : 고유 주문 번호 (merchant_uid)
        candidate_id: 지원자 ID (PII — 로그 출력 금지)
        currency    : 통화 코드 (기본 KRW)
        name        : 결제창에 표시할 상품명

    Returns:
        {merchant_uid, amount, currency, name, candidate_id}

    Raises:
        PaymentDisabledError: PAYMENT_ENABLED != true
        PaymentError        : 금액/주문번호 유효성 오류
    """
    _guard_payment_enabled()

    if amount <= 0:
        raise PaymentError(f"결제 금액은 0보다 커야 합니다. 입력값: {amount}")
    if not order_id:
        raise PaymentError("order_id는 비어있을 수 없습니다.")

    log.info("[PortOne] 결제 예약 생성: merchant_uid=%s amount=%d", order_id, amount)

    return {
        "merchant_uid": order_id,
        "amount": amount,
        "currency": currency,
        "name": name,
        "candidate_id": candidate_id,
    }


async def verify_portone_payment(imp_uid: str, expected_amount: int) -> bool:
    """
    PortOne 결제 완료 검증: 실제 결제금액 == expected_amount.

    Args:
        imp_uid         : PortOne 결제 고유 번호 (imp_uid)
        expected_amount : 사전에 등록한 금액

    Returns:
        True — 검증 성공

    Raises:
        PaymentDisabledError: PAYMENT_ENABLED != true
        PaymentError        : 금액 불일치 또는 API 오류
    """
    _guard_payment_enabled()

    access_token = await _portone_access_token()
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{PORTONE_API_BASE}/payments/{imp_uid}",
            headers={"Authorization": access_token},
        )
    data = resp.json()
    if data.get("code") != 0:
        raise PaymentError(f"PortOne 결제 조회 실패: {data.get('message')}")

    payment = data["response"]
    actual_amount = payment.get("amount", 0)
    status = payment.get("status", "")

    if status != "paid":
        raise PaymentError(f"결제 상태 이상: status={status}")
    if actual_amount != expected_amount:
        raise PaymentError(
            f"결제 금액 불일치: 실제={actual_amount}, 예상={expected_amount}"
        )

    log.info("[PortOne] 결제 검증 성공: imp_uid=%s amount=%d", imp_uid, actual_amount)
    return True


def verify_portone_webhook(body: bytes, signature: str) -> bool:
    """
    PortOne 웹훅 서명 검증 (HMAC-SHA256).

    Args:
        body      : 웹훅 요청 원본 바이트
        signature : X-ImpWebhook-Signature 헤더 값

    Returns:
        True — 서명 일치

    Raises:
        PaymentError: 서명 불일치 또는 환경변수 미설정
    """
    webhook_secret = _require_env("PORTONE_WEBHOOK_SECRET")
    expected = hmac.new(
        webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        log.warning("[PortOne] 웹훅 서명 검증 실패")
        raise PaymentError("PortOne 웹훅 서명 불일치")
    return True


# ──────────────────────────────────────────
# Stripe 유틸리티
# ──────────────────────────────────────────

async def create_stripe_payment_intent(
    amount: int,
    currency: str = "krw",
    metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Stripe PaymentIntent 생성.

    Args:
        amount  : 결제 금액 (최소 단위 — KRW는 원 단위)
        currency: 통화 코드 소문자 (기본 'krw')
        metadata: Stripe에 첨부할 임의 메타데이터

    Returns:
        Stripe PaymentIntent 객체 (client_secret 포함)

    Raises:
        PaymentDisabledError: PAYMENT_ENABLED != true
        PaymentError        : Stripe API 오류
    """
    _guard_payment_enabled()

    stripe_key = _require_env("STRIPE_SECRET_KEY")
    if amount <= 0:
        raise PaymentError(f"결제 금액은 0보다 커야 합니다. 입력값: {amount}")

    payload: dict[str, Any] = {
        "amount": amount,
        "currency": currency,
    }
    if metadata:
        for k, v in metadata.items():
            payload[f"metadata[{k}]"] = v

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "https://api.stripe.com/v1/payment_intents",
            data=payload,
            auth=(stripe_key, ""),
        )

    if resp.status_code != 200:
        err = resp.json().get("error", {})
        raise PaymentError(f"Stripe PaymentIntent 생성 실패: {err.get('message')}")

    pi = resp.json()
    log.info("[Stripe] PaymentIntent 생성: id=%s amount=%d", pi.get("id"), amount)
    return pi


def verify_stripe_webhook(payload: bytes, sig_header: str) -> dict[str, Any]:
    """
    Stripe 웹훅 서명 검증 (Stripe-Signature 헤더).

    stripe 패키지 없이 수동 검증(v1 scheme).

    Args:
        payload   : 웹훅 요청 원본 바이트
        sig_header: Stripe-Signature 헤더 값

    Returns:
        파싱된 Stripe 이벤트 dict

    Raises:
        PaymentError: 서명 불일치 또는 타임스탬프 만료 (300초)
    """
    import time

    webhook_secret = _require_env("STRIPE_WEBHOOK_SECRET")

    # 서명 헤더 파싱: t=timestamp,v1=signature
    parts: dict[str, str] = {}
    for item in sig_header.split(","):
        if "=" in item:
            k, v = item.split("=", 1)
            parts[k.strip()] = v.strip()

    ts = parts.get("t")
    v1 = parts.get("v1")
    if not ts or not v1:
        raise PaymentError("Stripe 서명 헤더 형식 오류")

    # 타임스탬프 만료 검사 (300초)
    if abs(time.time() - int(ts)) > 300:
        raise PaymentError("Stripe 웹훅 타임스탬프 만료")

    signed_payload = f"{ts}.".encode() + payload
    expected = hmac.new(
        webhook_secret.encode(),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, v1):
        log.warning("[Stripe] 웹훅 서명 검증 실패")
        raise PaymentError("Stripe 웹훅 서명 불일치")

    return json.loads(payload)
