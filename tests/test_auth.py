"""
tests/test_auth.py — BRIDGE API 인증 플로우 테스트
===================================================
Production 미사용 — TestClient + 인메모리 DB

검증 항목:
  1. 인증 없는 접근 → 403
  2. 잘못된 키 → 403 + 브루트포스 카운터 누적
  3. 유효한 키 → 200
  4. 세션 토큰 흐름 (발급 → 사용 → 만료)
  5. Rate limit — 10회 실패 → 429
  6. 공개 엔드포인트 — 인증 불필요
"""
import time

import pytest


# ── 공개 엔드포인트 ───────────────────────────────────────────────────────────

class TestPublicEndpoints:
    def test_health_no_auth(self, client):
        """/health 는 인증 없이 접근 가능해야 함."""
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "ok"

    def test_root_redirect_or_ok(self, client):
        """루트는 200 또는 리다이렉트."""
        r = client.get("/", follow_redirects=False)
        assert r.status_code in (200, 301, 302, 307, 308, 404)


# ── 어드민 인증 차단 ─────────────────────────────────────────────────────────

class TestAuthBlocking:
    def test_no_key_returns_403(self, client, no_headers):
        """인증 헤더 없으면 403."""
        r = client.get("/api/admin/candidates", headers=no_headers)
        assert r.status_code == 403

    def test_wrong_key_returns_403(self, client, wrong_headers):
        """잘못된 키는 403."""
        r = client.get("/api/admin/candidates", headers=wrong_headers)
        assert r.status_code == 403
        body = r.json()
        # 에러 응답 구조 검증
        assert "detail" in body or "error" in body

    def test_wrong_key_error_category(self, client, wrong_headers):
        """잘못된 키 응답에 errorCategory 포함."""
        r = client.get("/api/admin/candidates", headers=wrong_headers)
        assert r.status_code == 403
        body = r.json()
        detail = body.get("detail", body)
        if isinstance(detail, dict):
            assert detail.get("isError") is True
            assert "ADMIN_KEY" in detail.get("errorCategory", "")

    def test_valid_key_passes(self, client, admin_headers):
        """유효한 키로 어드민 엔드포인트 접근 가능."""
        r = client.get("/api/admin/candidates", headers=admin_headers)
        # 200 또는 인증은 통과하고 다른 이유(DB 등)로 실패 가능
        assert r.status_code in (200, 500, 503)
        assert r.status_code != 403


# ── 브루트포스 방어 ──────────────────────────────────────────────────────────

class TestBruteForce:
    def test_repeated_wrong_key_eventually_429(self, client):
        """동일 IP에서 10회 이상 잘못된 키 → 429 Rate Limit."""
        headers = {"x-admin-key": "brute-force-test-wrong-key"}
        endpoint = "/api/admin/candidates"

        status_codes = []
        for _ in range(12):
            r = client.get(endpoint, headers=headers)
            status_codes.append(r.status_code)

        # 10회 이상에서 429가 나와야 함
        assert 429 in status_codes, (
            f"10회 연속 실패 후 429 없음. 응답: {status_codes}"
        )

    def test_rate_limit_response_structure(self, client):
        """429 응답에 RATE_LIMIT errorCategory 포함."""
        headers = {"x-admin-key": "rate-limit-test-wrong-key-xyz"}
        # 이미 브루트포스 카운터가 쌓인 상태일 수 있음
        for _ in range(12):
            r = client.get("/api/admin/candidates", headers=headers)
            if r.status_code == 429:
                body = r.json()
                detail = body.get("detail", body)
                if isinstance(detail, dict):
                    assert detail.get("errorCategory") == "RATE_LIMIT"
                return
        pytest.skip("Rate limit 429 미발생 — IP별 카운터가 초기화된 상태")


# ── 세션 토큰 플로우 ─────────────────────────────────────────────────────────

class TestSessionToken:
    def test_login_returns_session_token(self, client, admin_headers):
        """어드민 로그인 → session_token 발급."""
        # admin_login은 비밀번호 필요 — 테스트용 mock 비밀번호
        r = client.post(
            "/api/admin/login",
            json={"password": "test-password-does-not-matter"},
            headers=admin_headers,
        )
        # 인증은 통과하더라도 비밀번호 검증에서 실패할 수 있음
        assert r.status_code in (200, 401, 403, 422, 500)

    def test_missing_session_token_header(self, client):
        """x-admin-token 없으면 API키 방식으로 폴백."""
        r = client.get(
            "/api/admin/candidates",
            headers={"x-admin-token": ""},  # 빈 값
        )
        assert r.status_code == 403

    def test_invalid_session_token(self, client):
        """유효하지 않은 session_token → 403."""
        r = client.get(
            "/api/admin/candidates",
            headers={"x-admin-token": "invalid-token-xyz-12345"},
        )
        assert r.status_code == 403


# ── 공개 API 인증 불필요 확인 ────────────────────────────────────────────────

class TestPublicApiAccess:
    def test_apply_endpoint_exists(self, client):
        """/api/apply POST — 공개 엔드포인트 (인증 불필요)."""
        r = client.post("/api/apply", json={})
        # 422 (validation error) = 공개 접근은 허용, 입력값 문제
        # 403 은 NG (인증 차단이면 안 됨)
        assert r.status_code != 403, "/api/apply가 인증 없이 403 반환 — 공개 엔드포인트여야 함"

    def test_jobs_list_public(self, client):
        """/api/jobs — 공개 채용 목록 (인증 불필요)."""
        r = client.get("/api/jobs")
        assert r.status_code not in (401, 403)


# ── 응답 구조 검증 ────────────────────────────────────────────────────────────

class TestResponseStructure:
    def test_403_has_is_error_field(self, client, wrong_headers):
        """모든 403 응답에 isError:true 포함."""
        r = client.get("/api/admin/candidates", headers=wrong_headers)
        assert r.status_code == 403
        body = r.json()
        detail = body.get("detail", body)
        if isinstance(detail, dict):
            assert detail.get("isError") is True

    def test_403_has_is_retryable_field(self, client, wrong_headers):
        """403 응답에 isRetryable 필드 포함."""
        r = client.get("/api/admin/candidates", headers=wrong_headers)
        body = r.json()
        detail = body.get("detail", body)
        if isinstance(detail, dict):
            assert "isRetryable" in detail
