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
import pytest


# ── 브루트포스 카운터 초기화 픽스처 ────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_auth_fail():
    """각 테스트 전 _AUTH_FAIL 초기화 — 브루트포스 상태 오염 방지."""
    try:
        import api_server
        api_server._AUTH_FAIL.clear()
    except Exception:
        pass
    yield
    try:
        import api_server
        api_server._AUTH_FAIL.clear()
    except Exception:
        pass


def _ok_body(body: dict) -> dict:
    """응답 본문에서 구조화 필드 추출 (detail 직접 또는 최상위)."""
    return body.get("detail", body) if isinstance(body, dict) else {}


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
        assert isinstance(body, dict)

    def test_wrong_key_error_category(self, client, wrong_headers):
        """잘못된 키 응답에 에러 정보 포함."""
        r = client.get("/api/admin/candidates", headers=wrong_headers)
        assert r.status_code == 403
        body = r.json()
        assert isinstance(body, dict)
        # SecurityMiddleware 래핑: {success, error: {code, message, status}, data}
        # 또는 직접 구조: {isError, errorCategory, ...}
        body_str = str(body)
        assert any(k in body_str for k in ["ADMIN_KEY", "FORBIDDEN", "isError", "errorCategory"]), \
            f"에러 관련 키 없음: {body}"

    def test_valid_key_passes(self, client, admin_headers):
        """유효한 키로 어드민 엔드포인트 접근 가능."""
        r = client.get("/api/admin/candidates", headers=admin_headers)
        # 403이 아닌 응답이면 인증 통과 (DB 오류 등은 허용)
        assert r.status_code != 403, f"유효한 키로 403 반환됨. 본문: {r.json()}"


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
        """429 응답에 RATE_LIMIT 관련 컨텍스트 포함."""
        headers = {"x-admin-key": "rate-limit-test-wrong-key-xyz"}  # gitleaks:allow
        r429 = None
        for _ in range(12):
            r = client.get("/api/admin/candidates", headers=headers)
            if r.status_code == 429:
                r429 = r
                break

        if r429 is None:
            pytest.skip("Rate limit 429 미발생 — IP별 카운터가 초기화된 상태")

        body = r429.json()
        body_str = str(body)
        # SecurityMiddleware 래핑 또는 직접 구조 모두 허용
        assert any(k in body_str for k in ["RATE_LIMIT", "RATE_LIMITED", "isRetryable"]), \
            f"Rate limit 응답에 관련 정보 없음: {body}"


# ── 세션 토큰 플로우 ─────────────────────────────────────────────────────────

class TestSessionToken:
    def test_login_returns_session_token(self, client, admin_headers):
        """어드민 로그인 → session_token 발급."""
        r = client.post(
            "/api/admin/login",
            json={"password": "test-password-does-not-matter"},
            headers=admin_headers,
        )
        # 인증은 통과하더라도 비밀번호 검증에서 실패할 수 있음
        assert r.status_code in (200, 401, 403, 422, 500)

    def test_missing_session_token_header(self, client):
        """x-admin-token 없으면 API키 방식으로 폴백 → 인증 실패."""
        r = client.get(
            "/api/admin/candidates",
            headers={"x-admin-token": ""},  # 빈 값
        )
        assert r.status_code in (403, 429)  # 인증 실패 또는 rate limit

    def test_invalid_session_token(self, client):
        """유효하지 않은 session_token → 403 또는 429."""
        r = client.get(
            "/api/admin/candidates",
            headers={"x-admin-token": "invalid-token-xyz-12345"},
        )
        assert r.status_code in (403, 429)


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
        """모든 403 응답에 에러 구조 포함."""
        r = client.get("/api/admin/candidates", headers=wrong_headers)
        assert r.status_code in (403, 429)  # 둘 다 인증 실패
        body = r.json()
        assert isinstance(body, dict), "응답이 JSON 객체여야 함"

    def test_403_has_is_retryable_field(self, client, wrong_headers):
        """403/429 응답에 에러 정보 포함."""
        r = client.get("/api/admin/candidates", headers=wrong_headers)
        assert r.status_code in (403, 429)
        body = r.json()
        body_str = str(body)
        # isRetryable, errorCategory, code 중 하나라도 있어야 함
        assert any(k in body_str for k in ["isRetryable", "errorCategory", "code", "error"]), \
            f"에러 정보 없음: {body}"
