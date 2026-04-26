"""
kakao_notify.py — 카카오톡 나에게 보내기 (개인 전용)
=====================================================
사용법:
  python tools/kakao_notify.py setup   # 최초 1회 — 브라우저 인증
  python tools/kakao_notify.py test    # 테스트 메시지 발송
  python tools/kakao_notify.py status  # 토큰 상태 확인

코드에서 호출:
  from tools.kakao_notify import send
  send("메시지 내용")
"""

from __future__ import annotations

import http.server
import json
import logging
import os
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_KST = timezone(timedelta(hours=9))

# ── 로깅 ──────────────────────────────────────────────────────────────────────
log = logging.getLogger("kakao_notify")
if not log.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

# ── bx 크리덴셜 키 이름 ────────────────────────────────────────────────────────
_KEY_REST    = "KAKAO_REST_API_KEY"
_KEY_ACCESS  = "KAKAO_ACCESS_TOKEN"
_KEY_REFRESH = "KAKAO_REFRESH_TOKEN"
_KEY_EXPIRY  = "KAKAO_TOKEN_EXPIRY"   # unix timestamp (str)

# ── Kakao OAuth 엔드포인트 ─────────────────────────────────────────────────────
_AUTH_URL    = "https://kauth.kakao.com/oauth/authorize"
_TOKEN_URL   = "https://kauth.kakao.com/oauth/token"
_SEND_URL    = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
_REDIRECT    = "http://localhost:9876"

# ── bx 읽기/쓰기 헬퍼 ─────────────────────────────────────────────────────────
def _bx_read(key: str) -> str:
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "tools"))
        from bx import _read
        v = _read(key)
        return v.strip() if v else ""
    except Exception:
        return ""


def _bx_write(key: str, value: str) -> bool:
    """bx에 값 저장 — bx의 _write 함수 사용."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "tools"))
        from bx import _write
        _write(key, value)
        return True
    except Exception as e:
        log.warning(f"[BX] {key} 저장 실패: {e}")
        return False


# ── OAuth 로컬 콜백 서버 ──────────────────────────────────────────────────────
_code_bucket: list[str] = []


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # 서버 로그 억제

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            _code_bucket.append(params["code"][0])
            body = "<html><body><h2>BRIDGE: OK!</h2><p>창을 닫으세요.</p></body></html>".encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
        elif "error" in params:
            _code_bucket.append("")
            body = b"<html><body><h2>Error</h2></body></html>"
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)


def _wait_for_code(timeout: int = 120) -> str | None:
    """포트 9876에서 인가 코드를 기다린다."""
    _code_bucket.clear()  # 이전 실행 잔류 코드 제거
    server = http.server.HTTPServer(("localhost", 9876), _CallbackHandler)
    server.timeout = 1
    deadline = time.time() + timeout
    while time.time() < deadline and not _code_bucket:
        server.handle_request()
    server.server_close()
    return _code_bucket[0] if _code_bucket else None


# ── 토큰 교환 / 갱신 ──────────────────────────────────────────────────────────
def _exchange_code(rest_key: str, code: str) -> dict | None:
    """인가 코드 → access/refresh 토큰 교환."""
    data = urllib.parse.urlencode({
        "grant_type":   "authorization_code",
        "client_id":    rest_key,
        "redirect_uri": _REDIRECT,
        "code":         code,
    }).encode()
    try:
        req = urllib.request.Request(_TOKEN_URL, data=data,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        log.error(f"[KAKAO] 코드 교환 실패: {e}")
        return None


def _refresh_access_token(rest_key: str, refresh_token: str) -> dict | None:
    """refresh_token → 새 access_token 발급."""
    data = urllib.parse.urlencode({
        "grant_type":    "refresh_token",
        "client_id":     rest_key,
        "refresh_token": refresh_token,
    }).encode()
    try:
        req = urllib.request.Request(_TOKEN_URL, data=data,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        log.error(f"[KAKAO] 토큰 갱신 실패: {e}")
        return None


def _save_tokens(tokens: dict) -> None:
    """발급된 토큰을 bx에 저장."""
    if "access_token" in tokens:
        _bx_write(_KEY_ACCESS, tokens["access_token"])
        expires_in = tokens.get("expires_in", 43199)
        expiry = int(time.time()) + int(expires_in) - 60  # 1분 여유
        _bx_write(_KEY_EXPIRY, str(expiry))
    if "refresh_token" in tokens:
        _bx_write(_KEY_REFRESH, tokens["refresh_token"])


def _get_valid_access_token() -> str | None:
    """유효한 access_token 반환 (만료 시 자동 갱신)."""
    access  = _bx_read(_KEY_ACCESS)
    expiry  = _bx_read(_KEY_EXPIRY)
    refresh = _bx_read(_KEY_REFRESH)
    rest    = _bx_read(_KEY_REST)

    if not access or not refresh or not rest:
        log.error("[KAKAO] 토큰 없음 — `python tools/kakao_notify.py setup` 실행 필요")
        return None

    now = int(time.time())
    # 만료 10분 전부터 갱신
    try:
        if expiry and now < int(expiry) - 600:
            return access
    except ValueError:
        pass  # expiry 파싱 실패 시 갱신으로 진행

    log.info("[KAKAO] access_token 갱신 중...")
    new_tokens = _refresh_access_token(rest, refresh)
    if not new_tokens or "access_token" not in new_tokens:
        log.error("[KAKAO] 토큰 갱신 실패")
        return None
    _save_tokens(new_tokens)
    return new_tokens["access_token"]


# ── 나에게 보내기 ──────────────────────────────────────────────────────────────
def send(text: str) -> bool:
    """카카오톡 나에게 메시지 발송. 성공 시 True."""
    token = _get_valid_access_token()
    if not token:
        return False

    template = json.dumps({
        "object_type": "text",
        "text": text[:2000],
        "link": {"web_url": "https://bridgejob.co.kr"},
        "button_title": "BRIDGE 열기",
    }, ensure_ascii=False)

    data = urllib.parse.urlencode({"template_object": template}).encode("utf-8")
    req = urllib.request.Request(
        _SEND_URL, data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/x-www-form-urlencoded;charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())
            if result.get("result_code") == 0:
                log.info("[KAKAO] 발송 완료")
                return True
            else:
                log.warning(f"[KAKAO] 발송 실패: {result}")
                return False
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="ignore")
        log.error(f"[KAKAO] HTTP {e.code}: {body}")
        return False
    except Exception as e:
        log.error(f"[KAKAO] 발송 오류: {e}")
        return False


# ── CLI ───────────────────────────────────────────────────────────────────────
def cmd_setup():
    print("=" * 50)
    print("BRIDGE 카카오톡 나에게 보내기 — 초기 설정")
    print("=" * 50)
    print()
    print("사전 준비:")
    print("  1. https://developers.kakao.com → 내 애플리케이션 → 앱 추가")
    print("  2. 앱 설정 → 카카오 로그인 → 활성화 ON")
    print("  3. Redirect URI 추가: http://localhost:9876")
    print("  4. 동의항목 → 카카오톡 메시지 전송 → 필수 동의")
    print()
    rest_key = input("REST API 키 입력: ").strip()
    if not rest_key:
        print("취소됨.")
        return

    _bx_write(_KEY_REST, rest_key)

    auth_url = (
        f"{_AUTH_URL}?response_type=code"
        f"&client_id={rest_key}"
        f"&redirect_uri={urllib.parse.quote(_REDIRECT, safe=':/')}"
        f"&scope=talk_message"
    )

    print()
    print("브라우저를 열어 카카오 로그인을 진행합니다...")
    print(f"(자동으로 안 열리면 직접 접속: {auth_url})")
    print()
    webbrowser.open(auth_url)

    print("로그인 대기 중... (최대 2분)")
    code = _wait_for_code(timeout=120)
    if not code:
        print("시간 초과 또는 오류 — 다시 실행하세요.")
        return

    print("인가 코드 수신, 토큰 교환 중...")
    tokens = _exchange_code(rest_key, code)
    if not tokens or "access_token" not in tokens:
        err = tokens.get("error_description") or tokens.get("error") if tokens else "응답 없음"
        print(f"토큰 교환 실패: {err}")
        return

    _save_tokens(tokens)
    print()
    print("✅ 설정 완료! 테스트 발송 중...")
    ok = send("BRIDGE 카카오 알림 설정 완료!")
    if ok:
        print("✅ 카카오톡에서 메시지를 확인하세요.")
    else:
        print("❌ 발송 실패 — 동의항목 설정을 다시 확인하세요.")


def cmd_test():
    now = datetime.now(_KST).strftime("%Y-%m-%d %H:%M KST")
    ok = send(f"[BRIDGE 테스트] {now}")
    print("✅ 발송 완료" if ok else "❌ 발송 실패")


def cmd_status():
    rest    = _bx_read(_KEY_REST)
    access  = _bx_read(_KEY_ACCESS)
    refresh = _bx_read(_KEY_REFRESH)
    expiry  = _bx_read(_KEY_EXPIRY)
    print(f"REST API KEY : {'설정됨' if rest else '없음'}")
    print(f"Access Token : {'설정됨' if access else '없음'}", end="")
    if expiry:
        left = int(expiry) - int(time.time())
        print(f" (만료까지 {left//3600}시간 {(left%3600)//60}분)")
    else:
        print()
    print(f"Refresh Token: {'설정됨' if refresh else '없음'}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "setup":
        cmd_setup()
    elif cmd == "test":
        cmd_test()
    elif cmd == "status":
        cmd_status()
    else:
        print("사용법: python tools/kakao_notify.py [setup|test|status]")
