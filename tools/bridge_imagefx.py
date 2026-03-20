r"""
bridge_imagefx.py — ImageFX 이미지 자동 생성 서버 v2
====================================================
Google ImageFX 직접 호출. 완전 무료, API 키 불필요.

사용법:
  1) 서버 시작:
     python "Q:/Claudework/bridge base/tools/bridge_imagefx.py"

  2) 토큰 등록 — labs.google/fx 페이지 Console에서 실행:
     (서버 시작 시 안내 표시 / UI에서 "토큰 등록" 클릭하면 자동 복사)

  3) bridge_prompt_ui.html에서 "사진 생성" 클릭

토큰 유효기간: ~1시간 → 만료 시 Console 코드 재실행
벤 방지: 8~15초 딜레이, 10회/시간, 50회/일
"""

import os
import sys
import json
import time
import random
import base64
import threading
from datetime import datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, quote
import urllib.request
import urllib.error

# ── Paths ─────────────────────────────────────────────────────────────────
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(TOOLS_DIR)
SAVE_DIR = os.path.join(TOOLS_DIR, "generated_images")
HTML_FILE = os.path.join(TOOLS_DIR, "bridge_prompt_ui.html")
PORT = 8765

# ── Ban Prevention ────────────────────────────────────────────────────────
DELAY_MIN = 8
DELAY_MAX = 15
HOURLY_LIMIT = 10
DAILY_LIMIT = 50
MAX_IMAGES = 4

# ── API ───────────────────────────────────────────────────────────────────
GENERATE_URL = "https://aisandbox-pa.googleapis.com/v1:runImageFx"

API_HEADERS = {
    "Origin": "https://labs.google",
    "Content-Type": "application/json",
    "Referer": "https://labs.google/fx/tools/image-fx",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
}

# Console snippet — ImageFX 페이지에서 1회 실행하면 토큰이 로컬 서버로 전송됨
# 브라우저가 자체 쿠키로 세션 엔드포인트를 호출하므로 쿠키 복사 불필요
AUTH_SNIPPET = (
    "fetch('/fx/api/auth/session')"
    ".then(r=>r.json())"
    ".then(d=>{"
    "if(!d.access_token){console.error('ImageFX 로그인 필요');return}"
    "fetch('http://localhost:" + str(PORT) + "/api/set-token',"
    "{method:'POST',headers:{'Content-Type':'application/json'},"
    "body:JSON.stringify({token:d.access_token,expires:d.expires})})"
    ".then(r=>r.json())"
    ".then(r=>console.log(r.message))"
    ".catch(e=>console.error(e))})"
)


# ── Session ───────────────────────────────────────────────────────────────
class ImageFXSession:
    def __init__(self):
        self.token = None
        self.token_expires = 0
        self._lock = threading.Lock()
        self._request_times: list = []
        self._daily_count = 0
        self._daily_reset = datetime.now().replace(
            hour=0, minute=0, second=0
        ) + timedelta(days=1)
        self._last_request = 0.0

    @property
    def authenticated(self) -> bool:
        return bool(self.token) and time.time() < self.token_expires

    @property
    def token_remaining_min(self) -> int:
        if not self.token:
            return 0
        return max(0, int((self.token_expires - time.time()) / 60))

    def set_token(self, token: str, expires=None):
        """브라우저에서 전달받은 토큰 설정"""
        with self._lock:
            self.token = token
            if expires:
                try:
                    if isinstance(expires, str):
                        dt = datetime.fromisoformat(
                            expires.replace("Z", "+00:00")
                        )
                        self.token_expires = dt.timestamp()
                    elif isinstance(expires, (int, float)):
                        ts = float(expires)
                        if ts > 1e12:
                            ts /= 1000
                        self.token_expires = ts
                    else:
                        self.token_expires = time.time() + 3000
                except Exception:
                    self.token_expires = time.time() + 3000
            else:
                self.token_expires = time.time() + 3000
            print(f"[AUTH] 토큰 설정 완료 (유효: {self.token_remaining_min}분)")

    def get_auth_headers(self) -> dict:
        if not self.authenticated:
            raise RuntimeError("토큰 없음 또는 만료")
        return {
            **API_HEADERS,
            "Authorization": f"Bearer {self.token}",
        }

    def check_rate_limit(self):
        now = datetime.now()
        if now >= self._daily_reset:
            self._daily_count = 0
            self._daily_reset = now.replace(
                hour=0, minute=0, second=0
            ) + timedelta(days=1)
        if self._daily_count >= DAILY_LIMIT:
            return f"일일 한도 도달 ({DAILY_LIMIT}회)"
        cutoff = time.time() - 3600
        self._request_times = [t for t in self._request_times if t > cutoff]
        if len(self._request_times) >= HOURLY_LIMIT:
            wait = int((self._request_times[0] + 3600 - time.time()) / 60) + 1
            return f"시간당 한도 ({HOURLY_LIMIT}회). {wait}분 후 재시도"
        return None

    def record_request(self):
        self._request_times.append(time.time())
        self._daily_count += 1
        self._last_request = time.time()

    def wait_delay(self):
        elapsed = time.time() - self._last_request
        if self._last_request > 0 and elapsed < DELAY_MIN:
            wait = random.uniform(DELAY_MIN, DELAY_MAX) - elapsed
            if wait > 0:
                print(f"[SAFE] {wait:.1f}초 대기 (벤 방지)")
                time.sleep(wait)

    def remaining(self) -> dict:
        cutoff = time.time() - 3600
        hourly_used = len([t for t in self._request_times if t > cutoff])
        return {
            "hourly": f"{hourly_used}/{HOURLY_LIMIT}",
            "daily": f"{self._daily_count}/{DAILY_LIMIT}",
            "token_min": self.token_remaining_min,
        }


# ── Image Generation ──────────────────────────────────────────────────────
_session = ImageFXSession()
_gen_lock = threading.Lock()


def generate_images(prompt: str, count: int = 3) -> dict:
    if not _session.authenticated:
        return {
            "ok": False,
            "error": "토큰 미등록 — 상단 '토큰 등록' 클릭",
            "need_auth": True,
        }

    with _gen_lock:
        limit_msg = _session.check_rate_limit()
        if limit_msg:
            return {"ok": False, "error": limit_msg, "quota": _session.remaining()}

        _session.wait_delay()

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_dir = os.path.join(SAVE_DIR, ts)
        os.makedirs(batch_dir, exist_ok=True)

        try:
            headers = _session.get_auth_headers()

            body = json.dumps({
                "userInput": {
                    "candidatesCount": min(count, MAX_IMAGES),
                    "prompts": [prompt],
                    "seed": random.randint(1, 999999999),
                },
                "clientContext": {
                    "sessionId": f";{int(time.time() * 1000)}",
                    "tool": "IMAGE_FX",
                },
                "modelInput": {
                    "modelNameType": "IMAGEN_3_5",
                },
                "aspectRatio": "IMAGE_ASPECT_RATIO_LANDSCAPE",
            }).encode("utf-8")

            req = urllib.request.Request(GENERATE_URL, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=90) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            panels = result.get("imagePanels", [])
            if not panels:
                _cleanup_empty(batch_dir)
                return {"ok": False, "error": "이미지 패널 없음 — 프롬프트 필터링 가능성"}

            gen_images = panels[0].get("generatedImages", [])
            if not gen_images:
                _cleanup_empty(batch_dir)
                return {"ok": False, "error": "생성된 이미지 없음"}

            saved = []
            for i, img_data in enumerate(gen_images):
                encoded = img_data.get("encodedImage", "")
                if not encoded:
                    continue
                try:
                    img_bytes = base64.b64decode(encoded)
                except Exception:
                    img_bytes = _fetch_media(encoded, headers)
                    if not img_bytes:
                        continue

                fname = f"{ts}_{i+1}.png"
                fpath = os.path.join(batch_dir, fname)
                with open(fpath, "wb") as f:
                    f.write(img_bytes)

                saved.append({
                    "filename": fname,
                    "path": fpath.replace("\\", "/"),
                    "url": f"/generated_images/{ts}/{fname}",
                    "size_kb": round(len(img_bytes) / 1024, 1),
                })

            _session.record_request()

            if saved:
                return {
                    "ok": True,
                    "count": len(saved),
                    "folder": batch_dir.replace("\\", "/"),
                    "images": saved,
                    "quota": _session.remaining(),
                }
            else:
                _cleanup_empty(batch_dir)
                return {"ok": False, "error": "이미지 저장 실패"}

        except urllib.error.HTTPError as e:
            _cleanup_empty(batch_dir)
            body_text = e.read().decode("utf-8", errors="replace")[:500]
            if e.code in (401, 403):
                _session.token = None
                return {
                    "ok": False,
                    "error": f"인증 만료 (HTTP {e.code})",
                    "need_auth": True,
                }
            if e.code == 429:
                return {"ok": False, "error": "Google 속도 제한. 잠시 후 재시도"}
            return {"ok": False, "error": f"HTTP {e.code}: {body_text}"}
        except RuntimeError as e:
            _cleanup_empty(batch_dir)
            return {"ok": False, "error": str(e), "need_auth": True}
        except Exception as e:
            _cleanup_empty(batch_dir)
            return {"ok": False, "error": str(e)[:300]}


def _fetch_media(media_key: str, headers: dict):
    try:
        param = json.dumps({"json": {"mediaKey": media_key}})
        url = f"https://labs.google/fx/api/trpc/media.fetchMedia?input={quote(param)}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            nested = data.get("result", {}).get("data", {}).get("json", {})
            media_url = nested.get("url", "")
            if media_url:
                req2 = urllib.request.Request(media_url)
                with urllib.request.urlopen(req2, timeout=30) as resp2:
                    return resp2.read()
            b64 = nested.get("base64", "")
            if b64:
                return base64.b64decode(b64)
    except Exception as e:
        print(f"[MEDIA] 다운로드 실패: {e}")
    return None


def _cleanup_empty(batch_dir: str):
    if os.path.isdir(batch_dir) and not os.listdir(batch_dir):
        os.rmdir(batch_dir)


# ── HTTP Server ───────────────────────────────────────────────────────────
class ImageFXHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=TOOLS_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._serve_html()
        elif parsed.path == "/api/status":
            self._json_response(self._status_info())
        elif parsed.path == "/api/auth-snippet":
            self._json_response({"snippet": AUTH_SNIPPET})
        elif parsed.path.startswith("/generated_images/"):
            super().do_GET()
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/generate":
            self._handle_generate()
        elif parsed.path == "/api/set-token":
            self._handle_set_token()
        elif parsed.path == "/api/open-folder":
            self._handle_open_folder()
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _serve_html(self):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            html = f.read()
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def _status_info(self):
        return {
            "ok": True,
            "authenticated": _session.authenticated,
            "provider": "Google ImageFX (Imagen)",
            "quota": _session.remaining(),
            "save_dir": SAVE_DIR.replace("\\", "/"),
            "port": PORT,
            "limits": {
                "delay": f"{DELAY_MIN}~{DELAY_MAX}초",
                "hourly": HOURLY_LIMIT,
                "daily": DAILY_LIMIT,
            },
        }

    def _handle_set_token(self):
        """브라우저 Console에서 전달된 토큰 수신"""
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            body = json.loads(raw)
        except Exception:
            self._json_response({"ok": False, "message": "잘못된 요청"}, 400)
            return

        token = body.get("token") or body.get("access_token")
        expires = body.get("expires")

        if not token:
            self._json_response({
                "ok": False,
                "message": "토큰이 비어있습니다. ImageFX 로그인 상태를 확인하세요",
            }, 400)
            return

        _session.set_token(token, expires)
        self._json_response({
            "ok": True,
            "message": f"인증 완료! 토큰 유효: {_session.token_remaining_min}분",
        })

    def _handle_generate(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            body = json.loads(raw)
        except Exception:
            self._json_response({"ok": False, "error": "잘못된 요청"}, 400)
            return

        prompt = body.get("prompt", "").strip()
        count = min(int(body.get("count", 3)), MAX_IMAGES)
        if not prompt:
            self._json_response(
                {"ok": False, "error": "프롬프트가 비어있습니다"}, 400
            )
            return

        result = generate_images(prompt, count)
        self._json_response(result)

    def _handle_open_folder(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            body = json.loads(raw)
            folder = body.get("folder", SAVE_DIR)
            if os.path.isdir(folder):
                os.startfile(folder)
                self._json_response({"ok": True})
            else:
                self._json_response({"ok": False, "error": "폴더 없음"})
        except Exception as e:
            self._json_response({"ok": False, "error": str(e)})

    def log_message(self, format, *args):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {args[0]}")


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    os.makedirs(SAVE_DIR, exist_ok=True)

    print(f"\n{'='*56}")
    print(f"  Bridge ImageFX Server v2")
    print(f"{'='*56}")
    print(f"  서버:    http://localhost:{PORT}")
    print(f"  벤 방지: {DELAY_MIN}~{DELAY_MAX}초, {HOURLY_LIMIT}회/시간, {DAILY_LIMIT}회/일")
    print(f"  저장:    {SAVE_DIR}")
    print()
    print("  [토큰 등록 방법]")
    print("  1. https://labs.google/fx/tools/image-fx 접속 (로그인)")
    print("  2. F12 → Console → 아래 코드 붙여넣기 → Enter:")
    print()
    print(f"  {AUTH_SNIPPET}")
    print()
    print("  3. Console에 '인증 완료!' 표시되면 OK")
    print("  ※ 토큰 ~1시간 유효. 만료 시 같은 코드 재실행")
    print(f"\n  종료: Ctrl+C\n")

    server = HTTPServer(("127.0.0.1", PORT), ImageFXHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버 종료")
        server.server_close()


if __name__ == "__main__":
    main()
