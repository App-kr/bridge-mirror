"""
OAuth Drive 인증 스크립트 — drive + spreadsheets 전체 스코프
커스텀 HTTP 서버: code 파라미터 있는 콜백만 처리 (preflight 요청 무시)

실행: "Q:/Phtyon 3/python.exe" -X utf8 "Q:/Claudework/bridge base/tools/oauth_drive.py"
"""
import os
import threading
import webbrowser

# 로컬호스트 HTTP 허용 (oauthlib 보안 경고 우회 — 로컬 개발 전용)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"   # 반환 스코프 범위 확장 허용
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from google_auth_oauthlib.flow import Flow

CRED_PATH  = Path("Q:/Claudework/bridge base/drive_oauth_credentials.json")
TOKEN_PATH = Path("Q:/Claudework/bridge base/drive_full_token.json")
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]
PORT = 18770
REDIRECT_URI = f"http://localhost:{PORT}/"

# ── OAuth Flow 생성 ──────────────────────────────────────────────
flow = Flow.from_client_secrets_file(
    str(CRED_PATH),
    scopes=SCOPES,
    redirect_uri=REDIRECT_URI,
)
auth_url, state = flow.authorization_url(
    access_type="offline",
    prompt="consent",
    include_granted_scopes="true",
)
print(f"[인증] State: {state[:12]}...", flush=True)
print(f"[인증] URL 생성 완료", flush=True)

# ── 콜백 대기용 이벤트 ────────────────────────────────────────────
callback_event = threading.Event()
callback_uri_holder = []


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed  = urlparse(self.path)
        params  = parse_qs(parsed.query)

        # favicon 등 code 없는 요청은 무시
        if "code" not in params:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<html><body>Waiting for Google auth...</body></html>")
            return

        # 실제 OAuth 콜백
        callback_uri_holder.append(f"{REDIRECT_URI.rstrip('/')}{self.path}")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            "<html><body><h2>인증 완료! 이 창을 닫아도 됩니다.</h2></body></html>".encode("utf-8")
        )
        callback_event.set()

    def log_message(self, *args):
        pass  # 서버 로그 출력 억제


# ── HTTP 서버 시작 ────────────────────────────────────────────────
server = HTTPServer(("localhost", PORT), OAuthCallbackHandler)
server_thread = threading.Thread(target=server.serve_forever, daemon=True)
server_thread.start()
print(f"[인증] 로컬 서버 시작 (포트 {PORT})", flush=True)

# ── 브라우저 열기 ─────────────────────────────────────────────────
webbrowser.open(auth_url)
print(f"[인증] 브라우저 오픈. Google 로그인 후 Drive 권한 허용해주세요...", flush=True)

# ── 콜백 대기 (최대 5분) ─────────────────────────────────────────
if not callback_event.wait(timeout=300):
    print("❌ 5분 내 인증 없음 — 타임아웃", flush=True)
    raise SystemExit(1)

server.shutdown()

# ── 토큰 교환 ─────────────────────────────────────────────────────
full_uri = callback_uri_holder[0]
print(f"[인증] 콜백 수신, 토큰 교환 중...", flush=True)
flow.fetch_token(authorization_response=full_uri)

creds = flow.credentials
TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
print(f"✅ {TOKEN_PATH.name} 저장 완료!", flush=True)
print(f"   scopes: {list(creds.scopes or [])}", flush=True)
