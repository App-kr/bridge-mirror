r"""
bridge_imagefx.py — FLUX.1 이미지 자동 생성 서버
====================================================
프롬프트 UI에서 '사진 생성' 클릭 → Together AI FLUX.1 → 3장 저장

실행:
  "C:/Users/Scarlett/AppData/Local/Programs/Python/Python313/python.exe" -X utf8 "Q:/Claudework/bridge base/tools/bridge_imagefx.py"

브라우저:
  http://localhost:8765

API 키 등록 (최초 1회):
  "C:/Users/Scarlett/AppData/Local/Programs/Python/Python313/python.exe" -X utf8 tools/bx.py set TOGETHER_API_KEY

엔드포인트:
  POST /api/generate  { "prompt": "...", "count": 3 }
  GET  /api/status    → 키 상태, 저장 경로
"""

import os
import sys
import json
import base64
import threading
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
import urllib.request
import urllib.error

# ── 경로 설정 ─────────────────────────────────────────────────────────────────
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(TOOLS_DIR)
SAVE_DIR = os.path.join(TOOLS_DIR, "generated_images")
HTML_FILE = os.path.join(TOOLS_DIR, "bridge_prompt_ui.html")
PORT = 8765

# ── Together AI 설정 ─────────────────────────────────────────────────────────
TOGETHER_API_URL = "https://api.together.xyz/v1/images/generations"
FLUX_MODEL = "black-forest-labs/FLUX.1-schnell-Free"  # 무료 모델
FLUX_MODEL_PAID = "black-forest-labs/FLUX.1-schnell"   # 유료 (더 빠름)

# ── BX 키 로드 (DPAPI) ───────────────────────────────────────────────────────
sys.path.insert(0, TOOLS_DIR)
from bx import _read as bx_read

def load_together_key():
    key = bx_read("TOGETHER_API_KEY")
    if key:
        return key.strip()
    return None

TOGETHER_KEY = load_together_key()


# ── FLUX.1 이미지 생성 ───────────────────────────────────────────────────────
def generate_images(prompt: str, count: int = 3) -> dict:
    """Together AI FLUX.1로 이미지 생성 후 파일 저장"""
    if not TOGETHER_KEY:
        return {"ok": False, "error": "Together API 키 없음. BX에 등록하세요:\npython tools/bx.py set TOGETHER_API_KEY"}

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = os.path.join(SAVE_DIR, ts)
    os.makedirs(batch_dir, exist_ok=True)

    saved = []
    errors = []

    # FLUX.1은 1회 요청에 1장씩 → count번 반복
    for i in range(count):
        try:
            payload = json.dumps({
                "model": FLUX_MODEL,
                "prompt": prompt,
                "width": 1024,
                "height": 1024,
                "steps": 4,
                "n": 1,
                "response_format": "b64_json",
            }).encode("utf-8")

            req = urllib.request.Request(
                TOGETHER_API_URL,
                data=payload,
                headers={
                    "Authorization": f"Bearer {TOGETHER_KEY}",
                    "Content-Type": "application/json",
                },
            )

            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            if "data" not in result or not result["data"]:
                errors.append(f"이미지 {i+1}: 응답에 데이터 없음")
                continue

            b64_data = result["data"][0].get("b64_json", "")
            if not b64_data:
                errors.append(f"이미지 {i+1}: base64 데이터 없음")
                continue

            img_bytes = base64.b64decode(b64_data)
            fname = f"{ts}_{i+1}.png"
            fpath = os.path.join(batch_dir, fname)
            with open(fpath, "wb") as f:
                f.write(img_bytes)

            saved.append({
                "filename": fname,
                "path": fpath.replace("\\", "/"),
                "size_kb": round(len(img_bytes) / 1024, 1),
                "base64_thumb": _make_thumb_b64(fpath),
            })

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            errors.append(f"이미지 {i+1}: HTTP {e.code} - {body[:200]}")
        except Exception as e:
            errors.append(f"이미지 {i+1}: {str(e)[:200]}")

    # 빈 폴더 정리
    if not saved and os.path.isdir(batch_dir) and not os.listdir(batch_dir):
        os.rmdir(batch_dir)

    if saved:
        return {
            "ok": True,
            "count": len(saved),
            "folder": batch_dir.replace("\\", "/"),
            "images": saved,
            "errors": errors if errors else None,
        }
    else:
        return {"ok": False, "error": "; ".join(errors) if errors else "알 수 없는 오류"}


def _make_thumb_b64(fpath: str, max_size: int = 200) -> str:
    """작은 썸네일 base64"""
    try:
        from PIL import Image
        import io
        img = Image.open(fpath)
        img.thumbnail((max_size, max_size))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        with open(fpath, "rb") as f:
            return base64.b64encode(f.read()).decode()


# ── HTTP 서버 ─────────────────────────────────────────────────────────────────
class ImageFXHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=TOOLS_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self._serve_html()
        elif parsed.path == "/api/status":
            self._json_response(self._status_info())
        elif parsed.path.startswith("/generated_images/"):
            super().do_GET()
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/generate":
            self._handle_generate()
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
            "ok": bool(TOGETHER_KEY),
            "provider": "Together AI (FLUX.1)",
            "model": FLUX_MODEL,
            "key_set": bool(TOGETHER_KEY),
            "save_dir": SAVE_DIR.replace("\\", "/"),
            "port": PORT,
        }

    def _handle_generate(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            body = json.loads(raw)
        except Exception:
            self._json_response({"ok": False, "error": "잘못된 요청"}, 400)
            return

        prompt = body.get("prompt", "").strip()
        count = min(int(body.get("count", 3)), 4)
        if not prompt:
            self._json_response({"ok": False, "error": "프롬프트가 비어있습니다"}, 400)
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


# ── 메인 ──────────────────────────────────────────────────────────────────────
def main():
    global TOGETHER_KEY
    os.makedirs(SAVE_DIR, exist_ok=True)

    print(f"=== Bridge ImageFX Server (FLUX.1) ===")
    print(f"  모델: {FLUX_MODEL}")
    print(f"  API 키: {'설정됨' if TOGETHER_KEY else '미설정 — python tools/bx.py set TOGETHER_API_KEY'}")
    print(f"  저장 경로: {SAVE_DIR}")
    print(f"  서버: http://localhost:{PORT}")
    print(f"  종료: Ctrl+C")
    print()

    server = HTTPServer(("127.0.0.1", PORT), ImageFXHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버 종료")
        server.server_close()


if __name__ == "__main__":
    main()
