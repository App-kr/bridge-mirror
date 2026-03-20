r"""
bridge_imagefx.py — Bridge ImageFX v4 (Gemini)
================================================
완전 자동 이미지 생성 — BX에 저장된 Gemini API 키 사용
바탕화면 "Bridge ImageFX" 아이콘 더블클릭 → 자동생성 → 저장 폴더에 자동 저장
"""

import os
import sys
import json
import time
import random
import base64
import socket
import subprocess
import threading
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
import urllib.request
import urllib.error

# ── Paths ─────────────────────────────────────────────────────────────────
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(TOOLS_DIR)
HTML_FILE = os.path.join(TOOLS_DIR, "bridge_prompt_ui.html")
CONFIG_FILE = os.path.join(TOOLS_DIR, ".imagefx_config.json")
PORT = 8765

DEFAULT_SAVE_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "Bridge_ImageFX")

# ── Config ────────────────────────────────────────────────────────────────
def _load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

_config = _load_config()
_save_dir = _config.get("save_dir", DEFAULT_SAVE_DIR)

# ── Gemini API Keys (BX에서 로드) ────────────────────────────────────────
_gemini_keys = []
_key_index = 0

def _load_gemini_keys():
    global _gemini_keys
    try:
        sys.path.insert(0, TOOLS_DIR)
        from bx import get_gemini_keys
        keys = get_gemini_keys()
        _gemini_keys = [k["key"] for k in keys if k.get("key")]
        print(f"[KEYS] Gemini API keys loaded: {len(_gemini_keys)}")
    except Exception as e:
        print(f"[KEYS] Failed to load keys: {e}")
        _gemini_keys = []

def _next_key():
    global _key_index
    if not _gemini_keys:
        return None
    key = _gemini_keys[_key_index % len(_gemini_keys)]
    _key_index += 1
    return key

# ── Rate Limiting ────────────────────────────────────────────────────────
DELAY_BETWEEN = 3
_last_request_time = 0.0
_gen_lock = threading.Lock()

# ── Gemini Image Generation ─────────────────────────────────────────────
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"


def generate_image(prompt: str) -> dict:
    global _last_request_time, _save_dir

    if not _gemini_keys:
        return {"ok": False, "error": "Gemini API key not found. Run: python tools/bx.py ls"}

    with _gen_lock:
        elapsed = time.time() - _last_request_time
        if _last_request_time > 0 and elapsed < DELAY_BETWEEN:
            wait = DELAY_BETWEEN - elapsed
            time.sleep(wait)

        os.makedirs(_save_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        uid = random.randint(1000, 9999)

        api_key = _next_key()
        url = f"{GEMINI_URL}?key={api_key}"

        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            # Extract image from response
            candidates = result.get("candidates", [])
            if not candidates:
                return {"ok": False, "error": "No candidates in response"}

            parts = candidates[0].get("content", {}).get("parts", [])
            saved = []
            img_idx = 0
            for part in parts:
                inline = part.get("inlineData")
                if not inline:
                    continue
                b64_data = inline.get("data", "")
                mime = inline.get("mimeType", "image/png")
                if not b64_data:
                    continue

                img_bytes = base64.b64decode(b64_data)
                ext = ".png" if "png" in mime else ".jpg"
                fname = f"bridge_{ts}_{uid}_{img_idx}{ext}"
                fpath = os.path.join(_save_dir, fname)
                with open(fpath, "wb") as f:
                    f.write(img_bytes)

                saved.append({
                    "filename": fname,
                    "url": f"/api/saved-image/{fname}",
                    "size_kb": round(len(img_bytes) / 1024, 1),
                })
                img_idx += 1

            _last_request_time = time.time()

            if saved:
                return {
                    "ok": True,
                    "count": len(saved),
                    "folder": _save_dir.replace("\\", "/"),
                    "images": saved,
                }
            else:
                return {"ok": False, "error": "No image in response (prompt may be filtered)"}

        except urllib.error.HTTPError as e:
            body_text = ""
            try:
                body_text = e.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                pass
            if e.code == 429:
                return {"ok": False, "error": "Rate limited. 잠시 후 재시도"}
            if e.code == 400 and "SAFETY" in body_text.upper():
                return {"ok": False, "error": "Safety filter blocked this prompt"}
            return {"ok": False, "error": f"HTTP {e.code}: {body_text[:200]}"}
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}


# ── Folder Picker ─────────────────────────────────────────────────────────
def _pick_folder(initial_dir):
    try:
        escaped = initial_dir.replace("'", "''").replace("\\", "\\\\")
        cmd = [
            "powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command",
            "Add-Type -AssemblyName System.Windows.Forms; "
            "$f = New-Object System.Windows.Forms.FolderBrowserDialog; "
            f"$f.SelectedPath = '{escaped}'; "
            "$f.Description = 'Select image save folder'; "
            "$f.ShowNewFolderButton = $true; "
            "if($f.ShowDialog() -eq 'OK'){$f.SelectedPath}"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.stdout.strip()
    except Exception as e:
        print(f"[FOLDER] Dialog error: {e}")
        return ""


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
        elif parsed.path == "/api/get-folder":
            self._json_response({"folder": _save_dir.replace("\\", "/")})
        elif parsed.path.startswith("/api/saved-image/"):
            self._serve_saved_image(parsed.path)
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/generate":
            self._handle_generate()
        elif parsed.path == "/api/pick-folder":
            self._handle_pick_folder()
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

    def _serve_saved_image(self, path):
        fname = os.path.basename(path.split("/api/saved-image/", 1)[1])
        fpath = os.path.join(_save_dir, fname)
        abs_save = os.path.abspath(_save_dir)
        abs_file = os.path.abspath(fpath)
        if os.path.isfile(fpath) and abs_file.startswith(abs_save):
            ext = os.path.splitext(fname)[1].lower()
            ct = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}.get(ext, "image/jpeg")
            with open(fpath, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Cache-Control", "no-cache")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404)

    def _status_info(self):
        return {
            "ok": True,
            "online": bool(_gemini_keys),
            "provider": f"Gemini ({len(_gemini_keys)} keys)",
            "save_dir": _save_dir.replace("\\", "/"),
            "port": PORT,
        }

    def _handle_generate(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            body = json.loads(raw)
        except Exception:
            self._json_response({"ok": False, "error": "Bad request"}, 400)
            return
        prompt = body.get("prompt", "").strip()
        if not prompt:
            self._json_response({"ok": False, "error": "Empty prompt"}, 400)
            return
        result = generate_image(prompt)
        self._json_response(result)

    def _handle_pick_folder(self):
        global _save_dir, _config
        folder = _pick_folder(_save_dir)
        if folder:
            _save_dir = folder
            _config["save_dir"] = folder
            _save_config(_config)
            os.makedirs(folder, exist_ok=True)
            print(f"[FOLDER] Changed: {folder}")
            self._json_response({"ok": True, "folder": folder.replace("\\", "/")})
        else:
            self._json_response({"ok": False, "error": "Cancelled"})

    def _handle_open_folder(self):
        try:
            folder = _save_dir
            if not os.path.isdir(folder):
                os.makedirs(folder, exist_ok=True)
            os.startfile(folder)
            self._json_response({"ok": True})
        except Exception as e:
            self._json_response({"ok": False, "error": str(e)})

    def log_message(self, format, *args):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {args[0]}")


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    global _save_dir
    os.makedirs(_save_dir, exist_ok=True)
    _load_gemini_keys()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", PORT)) == 0:
            print(f"Already running: http://localhost:{PORT}")
            return

    print(f"\n{'='*50}")
    print(f"  Bridge ImageFX v4 (Gemini)")
    print(f"{'='*50}")
    print(f"  Server:  http://localhost:{PORT}")
    print(f"  Save:    {_save_dir}")
    print(f"  Keys:    {len(_gemini_keys)}")
    print(f"\n  Exit: Ctrl+C\n")

    server = HTTPServer(("127.0.0.1", PORT), ImageFXHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
        server.server_close()


if __name__ == "__main__":
    main()
