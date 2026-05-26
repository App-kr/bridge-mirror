r"""
bridge_imagefx.py — Bridge ImageFX v4 (Auto Token via Extension)
================================================================
Chrome 확장 프로그램이 25분마다 ImageFX 토큰을 자동 갱신.
바탕화면 "Bridge ImageFX" 아이콘 더블클릭 → 자동생성 → 바탕화면에 저장.

최초 1회 설정:
  1. Chrome → chrome://extensions → 개발자 모드 ON
  2. "압축해제된 확장 프로그램을 로드합니다" → tools/bridge_token_ext 선택
  3. 끝 — 이후 토큰 자동 갱신
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
from datetime import datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, quote
import urllib.request
import urllib.error

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

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

# ── Ban Prevention ────────────────────────────────────────────────────────
DELAY_MIN = 10
DELAY_MAX = 18
HOURLY_LIMIT = 8
DAILY_LIMIT = 40
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
            # Persist token to disk for server restart recovery
            self._persist_token()
            print(f"[AUTH] Token set ({self.token_remaining_min}min remaining)")

    def _persist_token(self):
        """Save token to config file so it survives server restarts."""
        try:
            cfg = _load_config()
            cfg["_token"] = self.token
            cfg["_token_expires"] = self.token_expires
            _save_config(cfg)
        except Exception:
            pass

    def load_persisted_token(self):
        """Restore token from disk if still valid."""
        try:
            cfg = _load_config()
            token = cfg.get("_token")
            expires = cfg.get("_token_expires", 0)
            if token and float(expires) > time.time():
                self.token = token
                self.token_expires = float(expires)
                print(f"[AUTH] Restored token from disk ({self.token_remaining_min}min remaining)")
        except Exception:
            pass

    def get_auth_headers(self) -> dict:
        if not self.authenticated:
            raise RuntimeError("Token missing or expired")
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
            return f"Daily limit ({DAILY_LIMIT})"
        cutoff = time.time() - 3600
        self._request_times = [t for t in self._request_times if t > cutoff]
        if len(self._request_times) >= HOURLY_LIMIT:
            wait = int((self._request_times[0] + 3600 - time.time()) / 60) + 1
            return f"Hourly limit ({HOURLY_LIMIT}). Wait {wait}min"
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
                print(f"[SAFE] {wait:.1f}s delay")
                time.sleep(wait)

    def remaining(self) -> dict:
        cutoff = time.time() - 3600
        hourly_used = len([t for t in self._request_times if t > cutoff])
        return {
            "hourly": f"{hourly_used}/{HOURLY_LIMIT}",
            "daily": f"{self._daily_count}/{DAILY_LIMIT}",
            "token_min": self.token_remaining_min,
        }


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


# ── BRIDGE Logo Overlay ──────────────────────────────────────────────────
LOGO_PNG = os.path.join(TOOLS_DIR, "bridge_logo.png")


def _overlay_bridge_logo(img_bytes: bytes) -> bytes:
    """Add BRIDGE text watermark — left-center, clearly visible on any background."""
    if not HAS_PILLOW:
        return img_bytes
    try:
        import io
        img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        w, h = img.size

        if os.path.isfile(LOGO_PNG):
            logo = Image.open(LOGO_PNG).convert("RGBA")
            target_w = int(w * 0.18)
            ratio = target_w / logo.width
            target_h = int(logo.height * ratio)
            logo = logo.resize((target_w, target_h), Image.LANCZOS)
            margin = int(w * 0.035)
            # Left-center: vertically centered
            pos = (margin, (h - target_h) // 2)
            img.paste(logo, pos, logo)
        else:
            # Larger font for visibility
            font_size = max(36, int(w * 0.055))
            font = None
            for fpath in ["arial.ttf", "C:/Windows/Fonts/arial.ttf",
                          "C:/Windows/Fonts/arialbd.ttf"]:
                try:
                    font = ImageFont.truetype(fpath, font_size)
                    break
                except OSError:
                    continue
            if font is None:
                font = ImageFont.load_default()

            draw = ImageDraw.Draw(img)
            margin = int(w * 0.035)
            # Left-center position: y = 45% from top
            tx = margin
            ty = int(h * 0.45)

            # Multi-layer shadow for visibility on any background
            for ox, oy in [(4, 4), (3, 3), (2, 2), (-1, -1), (0, 2)]:
                draw.text((tx + ox, ty + oy), "BRIDGE",
                          fill=(0, 0, 0, 140), font=font)
            # Main white text — high opacity
            draw.text((tx, ty), "BRIDGE",
                      fill=(255, 255, 255, 245), font=font)

        out = io.BytesIO()
        img.save(out, format="PNG", optimize=True)
        return out.getvalue()
    except Exception as e:
        print(f"[LOGO] Overlay failed: {e}")
        return img_bytes


def _naturalize_photo(img_bytes: bytes, quality: int = 88) -> bytes:
    """Post-process AI image to look like a real DSLR photograph.

    Applies subtle real-camera imperfections:
    1. Sensor noise (Gaussian grain)
    2. Micro color shift (WB drift)
    3. Subtle vignette
    4. Minor sharpness variation
    5. JPEG compression artifacts (real cameras save JPEG)
    6. Realistic EXIF-style metadata via JPEG save
    """
    if not HAS_PILLOW:
        return img_bytes
    try:
        import io
        import struct
        import numpy as np
    except ImportError:
        # numpy not available — at least do JPEG conversion
        try:
            import io as _io
            img = Image.open(_io.BytesIO(img_bytes)).convert("RGB")
            out = _io.BytesIO()
            img.save(out, format="JPEG", quality=quality, subsampling=0)
            return out.getvalue()
        except Exception:
            return img_bytes

    try:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        w, h = img.size
        arr = np.array(img, dtype=np.float32)

        # 1. Sensor noise — Gaussian grain (ISO 400-800 feel, stronger than before)
        noise_strength = random.uniform(3.5, 7.0)
        noise = np.random.normal(0, noise_strength, arr.shape).astype(np.float32)
        # More noise in blue channel (real Bayer sensor characteristic)
        noise[:, :, 2] *= 1.4
        # Slightly more noise in shadows (realistic sensor behavior)
        shadow_mask = (arr.mean(axis=2, keepdims=True) < 80).astype(np.float32)
        noise *= (1.0 + shadow_mask * 0.5)
        arr = np.clip(arr + noise, 0, 255)

        # 2. White-balance drift — warm/cool color cast (every real camera has one)
        wb_r = random.uniform(0.992, 1.012)
        wb_g = random.uniform(0.996, 1.004)
        wb_b = random.uniform(0.988, 1.008)
        arr[:, :, 0] *= wb_r
        arr[:, :, 1] *= wb_g
        arr[:, :, 2] *= wb_b
        arr = np.clip(arr, 0, 255)

        # 3. Chromatic aberration — slight RGB channel offset at edges (real lens defect)
        ca_strength = random.uniform(0.5, 1.5)
        try:
            from scipy.ndimage import shift as ndshift
            arr[:, :, 0] = ndshift(arr[:, :, 0], [0, ca_strength], mode='nearest')
            arr[:, :, 2] = ndshift(arr[:, :, 2], [0, -ca_strength * 0.7], mode='nearest')
        except ImportError:
            ca_px = max(1, int(ca_strength))
            arr[:, ca_px:, 0] = arr[:, :-ca_px, 0]  # shift red right
            arr[:, :-ca_px, 2] = arr[:, ca_px:, 2]  # shift blue left

        # 4. Subtle vignette — darker corners like a real lens
        Y, X = np.ogrid[:h, :w]
        cx, cy = w / 2, h / 2
        max_dist = np.sqrt(cx ** 2 + cy ** 2)
        dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) / max_dist
        vignette_strength = random.uniform(0.10, 0.22)
        vignette = 1.0 - (dist ** 2) * vignette_strength
        arr *= vignette[:, :, np.newaxis]
        arr = np.clip(arr, 0, 255)

        # 5. Subtle contrast reduction (AI images are too contrasty)
        contrast_factor = random.uniform(0.93, 0.98)
        mean_val = arr.mean()
        arr = mean_val + (arr - mean_val) * contrast_factor
        arr = np.clip(arr, 0, 255)

        img = Image.fromarray(arr.astype(np.uint8))

        # 6. Micro sharpness variation
        if random.random() < 0.7:
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(random.uniform(0.88, 1.06))

        # 7. Very subtle brightness micro-drift
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(random.uniform(0.98, 1.02))

        # 8. Slight saturation reduction (AI images over-saturate)
        if random.random() < 0.5:
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(random.uniform(0.92, 0.98))

        # 9. Save as JPEG with lower quality (real cameras: 80-90)
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=quality, subsampling=0, optimize=True)
        print(f"[NATURALIZE] {w}x{h} | noise={noise_strength:.1f} | "
              f"wb=({wb_r:.3f},{wb_g:.3f},{wb_b:.3f}) | "
              f"vignette={vignette_strength:.2f} | contrast={contrast_factor:.3f} | "
              f"jpg_q={quality}")
        return out.getvalue()

    except Exception as e:
        print(f"[NATURALIZE] Failed: {e}")
        # Fallback: at least convert to JPEG
        try:
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            out = io.BytesIO()
            img.save(out, format="JPEG", quality=quality, subsampling=0)
            return out.getvalue()
        except Exception:
            return img_bytes


# ── Image Generation ──────────────────────────────────────────────────────
_session = ImageFXSession()
_session.load_persisted_token()
_gen_lock = threading.Lock()


def _simplify_prompt(prompt: str) -> str:
    """Simplify a prompt for retry after safety filter rejection.
    Removes race descriptors and shortens constraints that may trigger filters."""
    import re
    # Remove race/ethnicity descriptors that may trigger PROMINENT_PEOPLE filter
    prompt = re.sub(r'\b(Caucasian|Black|Latino|mixed-race Western)\b', '', prompt)
    # Remove age ranges
    prompt = re.sub(r'\(ages? \d+[–\-]\d+\)', '', prompt)
    # Shorten the CRITICAL block to reduce complexity
    prompt = re.sub(
        r'CRITICAL:.*?(?=Aspect ratio)',
        'No text, no letters, no logos anywhere. ',
        prompt,
        flags=re.DOTALL,
    )
    # Collapse multiple spaces/periods
    prompt = re.sub(r'  +', ' ', prompt)
    prompt = re.sub(r'\.\s*\.', '.', prompt)
    return prompt.strip()


def generate_images(prompt: str, count: int = 3) -> dict:
    global _save_dir
    if not _session.authenticated:
        return {
            "ok": False,
            "error": "Token not set. Install Chrome extension (bridge_token_ext) or visit ImageFX first.",
            "need_auth": True,
        }

    with _gen_lock:
        limit_msg = _session.check_rate_limit()
        if limit_msg:
            return {"ok": False, "error": limit_msg, "quota": _session.remaining()}

        _session.wait_delay()
        os.makedirs(_save_dir, exist_ok=True)

        # Find next BRIDGE_N sequence number (supports both .png and .jpg)
        existing = [f for f in os.listdir(_save_dir) if f.startswith("BRIDGE_") and (f.endswith(".png") or f.endswith(".jpg"))]
        max_n = 0
        for f in existing:
            try:
                n = int(f.replace("BRIDGE_", "").replace(".png", "").replace(".jpg", ""))
                if n > max_n:
                    max_n = n
            except ValueError:
                pass
        next_n = max_n + 1

        # Retry loop: attempt original prompt, then simplified on filter error
        attempts = [prompt]
        last_error = ""

        for attempt_idx, current_prompt in enumerate(attempts):
            try:
                headers = _session.get_auth_headers()

                body = json.dumps({
                    "userInput": {
                        "candidatesCount": min(count, MAX_IMAGES),
                        "prompts": [current_prompt],
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
                    last_error = "No panels — prompt may be filtered"
                    if attempt_idx == 0:
                        simplified = _simplify_prompt(prompt)
                        if simplified != prompt:
                            print(f"[RETRY] Prompt filtered, retrying with simplified version...")
                            attempts.append(simplified)
                            _session.wait_delay()
                            continue
                    return {"ok": False, "error": last_error}

                gen_images = panels[0].get("generatedImages", [])
                if not gen_images:
                    last_error = "No images generated"
                    if attempt_idx == 0:
                        simplified = _simplify_prompt(prompt)
                        if simplified != prompt:
                            print(f"[RETRY] No images, retrying with simplified version...")
                            attempts.append(simplified)
                            _session.wait_delay()
                            continue
                    return {"ok": False, "error": last_error}

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

                    # Apply BRIDGE logo overlay
                    img_bytes = _overlay_bridge_logo(img_bytes)

                    # Naturalize: add real-camera imperfections + convert to JPG
                    img_bytes = _naturalize_photo(img_bytes, quality=random.randint(78, 88))

                    fname = f"BRIDGE_{next_n + i}.jpg"
                    fpath = os.path.join(_save_dir, fname)
                    with open(fpath, "wb") as f:
                        f.write(img_bytes)

                    saved.append({
                        "filename": fname,
                        "url": f"/api/saved-image/{fname}",
                        "size_kb": round(len(img_bytes) / 1024, 1),
                    })

                _session.record_request()

                if saved:
                    retried = " (retried with simplified prompt)" if attempt_idx > 0 else ""
                    return {
                        "ok": True,
                        "count": len(saved),
                        "folder": _save_dir.replace("\\", "/"),
                        "images": saved,
                        "quota": _session.remaining(),
                        "retried": attempt_idx > 0,
                    }
                else:
                    return {"ok": False, "error": "Failed to save images"}

            except urllib.error.HTTPError as e:
                body_text = e.read().decode("utf-8", errors="replace")[:500]
                if e.code in (401, 403):
                    _session.token = None
                    return {
                        "ok": False,
                        "error": f"Auth expired (HTTP {e.code})",
                        "need_auth": True,
                    }
                if e.code == 429:
                    return {"ok": False, "error": "Google rate limit. Wait a moment"}
                # On HTTP error, try simplified prompt if first attempt
                last_error = f"HTTP {e.code}: {body_text}"
                if attempt_idx == 0:
                    simplified = _simplify_prompt(prompt)
                    if simplified != prompt:
                        print(f"[RETRY] HTTP {e.code}, retrying with simplified prompt...")
                        attempts.append(simplified)
                        _session.wait_delay()
                        continue
                return {"ok": False, "error": last_error}
            except RuntimeError as e:
                return {"ok": False, "error": str(e), "need_auth": True}
            except Exception as e:
                return {"ok": False, "error": str(e)[:300]}

        # All attempts exhausted
        return {"ok": False, "error": last_error or "All retry attempts failed"}


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
        print(f"[MEDIA] Download failed: {e}")
    return None


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
        elif parsed.path == "/api/set-token":
            self._handle_set_token()
        elif parsed.path == "/api/logout":
            self._handle_logout()
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
            ct = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}.get(ext, "image/png")
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
            "online": True,
            "authenticated": _session.authenticated,
            "provider": "ImageFX (Imagen 3.5)",
            "quota": _session.remaining(),
            "save_dir": _save_dir.replace("\\", "/"),
            "port": PORT,
        }

    def _handle_set_token(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            body = json.loads(raw)
        except Exception:
            self._json_response({"ok": False, "message": "Bad request"}, 400)
            return
        token = body.get("token") or body.get("access_token")
        expires = body.get("expires")
        if not token:
            self._json_response({
                "ok": False,
                "message": "Empty token",
            }, 400)
            return
        _session.set_token(token, expires)
        self._json_response({
            "ok": True,
            "message": f"Auth OK! Token valid: {_session.token_remaining_min}min",
        })

    def _handle_logout(self):
        """토큰 삭제 — 설정 파일에서도 제거."""
        _session.token = None
        _session.token_expires = 0
        try:
            cfg_path = os.path.join(os.path.dirname(__file__), ".imagefx_config.json")
            if os.path.exists(cfg_path):
                with open(cfg_path, encoding="utf-8") as f:
                    cfg = json.load(f)
                cfg.pop("_token", None)
                cfg.pop("_token_expires", None)
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        self._json_response({"ok": True, "message": "로그아웃 완료"})

    def _handle_generate(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            body = json.loads(raw)
        except Exception:
            self._json_response({"ok": False, "error": "Bad request"}, 400)
            return
        prompt = body.get("prompt", "").strip()
        count = min(int(body.get("count", 3)), MAX_IMAGES)
        if not prompt:
            self._json_response(
                {"ok": False, "error": "Empty prompt"}, 400
            )
            return
        result = generate_images(prompt, count)
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

    # Kill any zombie server on same port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", PORT)) == 0:
            print(f"[INIT] Killing previous server on port {PORT}...")
            try:
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     f"Get-NetTCPConnection -LocalPort {PORT} -State Listen -ErrorAction SilentlyContinue "
                     f"| ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }}"],
                    capture_output=True, timeout=5
                )
                time.sleep(1)
            except Exception:
                pass

    ext_dir = os.path.join(TOOLS_DIR, "bridge_token_ext")
    ext_ok = os.path.isdir(ext_dir)

    print(f"\n{'='*56}")
    print(f"  Bridge ImageFX Server v4")
    print(f"{'='*56}")
    print(f"  Server:    http://localhost:{PORT}")
    print(f"  Save:      {_save_dir}")
    print(f"  Extension: {'OK' if ext_ok else 'MISSING'} ({ext_dir})")
    print(f"  Limits:    {DELAY_MIN}~{DELAY_MAX}s, {HOURLY_LIMIT}/hr, {DAILY_LIMIT}/day")
    print()
    if not ext_ok:
        print("  [!] Chrome extension not found!")
    print("  Token will be auto-refreshed by Chrome extension.")
    print(f"\n  Exit: Ctrl+C\n")

    class ThreadedServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True

    server = ThreadedServer(("127.0.0.1", PORT), ImageFXHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
        server.server_close()


if __name__ == "__main__":
    main()
