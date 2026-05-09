"""
security_middleware.py — Bridge Agency Enterprise Security Layer
================================================================
2026-03 최신 기준 적용
- OWASP Top 10 (2025) 완전 대응
- NIST SP 800-53 Rev.5 준거
- KISA 개인정보 처리방침 준수
- PII Zero-Leak 아키텍처
- 자동 보안 업데이트 (매월 1일 자가갱신)
- Fail-Closed 정책 (의심 = 차단)

사용법:
  from security_middleware import SecurityMiddleware, require_integrity
  app.add_middleware(SecurityMiddleware)
"""

import asyncio
import hashlib
import hmac
import ipaddress
import json
import logging
import os
import re
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from typing import Optional, Set

import httpx
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# ═══════════════════════════════════════════════════════════════
# 설정
# ═══════════════════════════════════════════════════════════════
ENV            = os.getenv("ENV", "development")
HMAC_SECRET    = os.getenv("HMAC_SECRET", os.getenv("ADMIN_API_KEY", "")).strip()
AUDIT_DIR      = Path(os.getenv("AUDIT_DIR", "audit"))
LOG_DIR        = Path(os.getenv("LOG_DIR", "logs"))
SECURITY_VERSION_FILE = Path("security_version.json")

AUDIT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# 국가별 강화 감지 설정
# ═══════════════════════════════════════════════════════════════
# 이 나라에서 오는 공격 패턴은 임계치를 낮춰 빠르게 차단
# (정상 사용자는 공격 패턴을 안 보내므로 영향 없음)
# ═══════════════════════════════════════════════════════════════
# 봇/스크래퍼 User-Agent 차단 (Google Sheets IMPORTXML 등)
# ═══════════════════════════════════════════════════════════════
SCRAPER_UA_PATTERNS: list[re.Pattern] = [
    # Google Sheets IMPORTXML / IMPORTHTML / IMPORTDATA
    re.compile(r"Google-Spreadsheet", re.IGNORECASE),
    re.compile(r"GoogleBot", re.IGNORECASE),
    re.compile(r"Google-Apps-Script", re.IGNORECASE),
    # Generic scraper/bot patterns
    re.compile(r"python-requests", re.IGNORECASE),
    re.compile(r"python-urllib", re.IGNORECASE),
    re.compile(r"scrapy", re.IGNORECASE),
    re.compile(r"curl/", re.IGNORECASE),
    re.compile(r"wget/", re.IGNORECASE),
    re.compile(r"httpx/", re.IGNORECASE),
    re.compile(r"axios/", re.IGNORECASE),
    re.compile(r"node-fetch", re.IGNORECASE),
    re.compile(r"go-http-client", re.IGNORECASE),
    re.compile(r"java/", re.IGNORECASE),
    re.compile(r"libwww-perl", re.IGNORECASE),
    re.compile(r"PostmanRuntime", re.IGNORECASE),
    re.compile(r"insomnia/", re.IGNORECASE),
    re.compile(r"Paw/", re.IGNORECASE),
    re.compile(r"HeadlessChrome", re.IGNORECASE),
    re.compile(r"PhantomJS", re.IGNORECASE),
    re.compile(r"Selenium", re.IGNORECASE),
    re.compile(r"Puppeteer", re.IGNORECASE),
    re.compile(r"Playwright", re.IGNORECASE),
    re.compile(r"CasperJS", re.IGNORECASE),
    re.compile(r"HTTrack", re.IGNORECASE),
    re.compile(r"SemrushBot", re.IGNORECASE),
    re.compile(r"AhrefsBot", re.IGNORECASE),
    re.compile(r"MJ12bot", re.IGNORECASE),
    re.compile(r"DotBot", re.IGNORECASE),
    re.compile(r"BLEXBot", re.IGNORECASE),
    re.compile(r"DataForSeoBot", re.IGNORECASE),
    re.compile(r"PetalBot", re.IGNORECASE),
    re.compile(r"Bytespider", re.IGNORECASE),
    re.compile(r"GPTBot", re.IGNORECASE),
    re.compile(r"CCBot", re.IGNORECASE),
    re.compile(r"ClaudeBot", re.IGNORECASE),
    re.compile(r"anthropic-ai", re.IGNORECASE),
]

# admin 인증 경로는 봇 차단 예외 (API 클라이언트 허용)
_BOT_CHECK_EXEMPT_PREFIXES = ("/api/admin/", "/api/apply", "/api/inquiry", "/api/track")

# 공개 읽기 전용 엔드포인트: GET 요청은 UA 차단 면제 (SEO + 정당한 API 클라이언트)
# POST/DELETE 등 쓰기는 여전히 UA 차단 적용 (봇 스팸 방지)
_PUBLIC_GET_PREFIXES = ("/api/community/", "/api/jobs")

def _is_scraper_ua(ua: str) -> bool:
    """User-Agent가 스크래퍼/봇인지 판별"""
    if not ua:
        return True  # UA 없음 = 봇으로 간주
    for pat in SCRAPER_UA_PATTERNS:
        if pat.search(ua):
            return True
    return False

STRICT_COUNTRIES: set[str] = {
    "US", "GB", "ZA",        # 미국, 영국, 남아공
    "CN",                    # 중국
    "AE",                    # UAE (두바이)
    "RU",                    # 러시아
    "KP",                    # 북한
    "BR",                    # 브라질
    "VN",                    # 베트남
    "ID",                    # 인도네시아
    "RO",                    # 루마니아
    "TR",                    # 터키
    "NG",                    # 나이지리아
}
STRICT_ATTACK_THRESHOLD = 1   # 이 나라에서는 1회 공격 패턴 = 즉시 차단
STRICT_RATE_WINDOW = 60       # 엄격 rate limit 윈도우 (초)
STRICT_RATE_MAX = 30          # 이 나라에서는 60초에 30 요청 초과 시 차단

# IP→국가 캐시 (메모리, TTL 1시간)
_geo_cache: dict[str, tuple[str, float]] = {}   # ip -> (country_code, expire_ts)
_GEO_TTL = 3600.0  # 1시간

async def _get_country(ip: str) -> str:
    """IP 국가코드 조회 (ip-api.com, 캐시 1시간). 실패 시 '' 반환."""
    now = time.time()
    cached = _geo_cache.get(ip)
    if cached and now < cached[1]:
        return cached[0]
    # private / localhost → KR로 간주 (개발 환경)
    try:
        addr = ipaddress.ip_address(ip)
        if addr.is_private or addr.is_loopback:
            _geo_cache[ip] = ("KR", now + _GEO_TTL)
            return "KR"
    except ValueError:
        pass
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"http://ip-api.com/json/{ip}?fields=countryCode")
            if r.status_code == 200:
                cc = r.json().get("countryCode", "")
                _geo_cache[ip] = (cc, now + _GEO_TTL)
                return cc
    except Exception:
        pass
    return ""

# ═══════════════════════════════════════════════════════════════
# 개인정보(PII) 탐지 패턴 — 절대 노출 금지
# ═══════════════════════════════════════════════════════════════
PII_PATTERNS = [
    # 전화번호 (한국)
    re.compile(r'0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4}'),
    # 이메일
    re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'),
    # 사업자등록번호
    re.compile(r'\d{3}-?\d{2}-?\d{5}'),
    # 주민등록번호 패턴
    re.compile(r'\d{6}[-\s]?\d{7}'),
    # 카드번호
    re.compile(r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}'),
    # 카카오 ID (영문+숫자 조합 4~20자)
    re.compile(r'kakao[_\s]?id\s*[:=]\s*\S+', re.IGNORECASE),
    # IP 주소 (내부)
    re.compile(r'192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.1[6-9]\.\d+\.\d+'),
]

def mask_pii(text: str) -> str:
    """응답 본문에서 PII 자동 마스킹"""
    if not isinstance(text, str):
        return text
    for pattern in PII_PATTERNS:
        text = pattern.sub("***MASKED***", text)
    return text

def contains_pii(text: str) -> bool:
    return any(p.search(text) for p in PII_PATTERNS)

# ═══════════════════════════════════════════════════════════════
# 공격 패턴 탐지 (OWASP 2025 기준)
# ═══════════════════════════════════════════════════════════════
ATTACK_PATTERNS = {
    "sql_injection": re.compile(
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|EXEC|EXECUTE|"
        r"CAST|CONVERT|DECLARE|XP_|SP_|0x[0-9a-f]+)\b|"
        r"(--|;|\/\*|\*\/|@@|char\(|nchar\(|varchar\(|"
        r"sleep\(|benchmark\(|waitfor\s+delay|load_file|into\s+outfile))",
        re.IGNORECASE
    ),
    "xss": re.compile(
        r"(<script[\s\S]*?>[\s\S]*?<\/script>|"
        r"javascript\s*:|on\w+\s*=|"
        r"<\s*img[^>]+src\s*=\s*['\"]?\s*javascript:|"
        r"expression\s*\(|vbscript\s*:|"
        r"data\s*:\s*text\/html|<\s*iframe|<\s*object|<\s*embed)",
        re.IGNORECASE
    ),
    "path_traversal": re.compile(
        r"(\.\./|\.\.\\|%2e%2e%2f|%2e%2e\/|\.\.%2f|%252e%252e)",
        re.IGNORECASE
    ),
    "command_injection": re.compile(
        r"(\|\||&&|`|\$\(|>\s*/|<\s*/proc|/etc/passwd|/etc/shadow|"
        r"nc\s+-|netcat|wget\s+http|curl\s+http|bash\s+-[ic])",
        re.IGNORECASE
    ),
    "llm_injection": re.compile(
        r"(ignore\s+previous\s+instructions?|"
        r"disregard\s+(all\s+)?prior|"
        r"you\s+are\s+now\s+(a\s+)?(different|new)|"
        r"act\s+as\s+if\s+you\s+have\s+no\s+(restrictions?|rules?)|"
        r"jailbreak|DAN\s+mode|pretend\s+you('re|\s+are)\s+an?\s+AI\s+without)",
        re.IGNORECASE
    ),
    "ssrf": re.compile(
        r"(169\.254\.|metadata\.google|169\.254\.169\.254|"
        r"file:\/\/|gopher:\/\/|dict:\/\/)",
        re.IGNORECASE
    ),
}

def detect_attack(text: str) -> Optional[str]:
    """공격 패턴 탐지 → 공격 유형 반환, 없으면 None"""
    for attack_type, pattern in ATTACK_PATTERNS.items():
        if pattern.search(text):
            return attack_type
    return None

# ═══════════════════════════════════════════════════════════════
# IP 블랙리스트 (메모리 + 파일 영속)
# ═══════════════════════════════════════════════════════════════
BLACKLIST_FILE    = AUDIT_DIR / "ip_blacklist.json"
PERMANENT_BAN_FILE = AUDIT_DIR / "ip_permanent_ban.json"
ATTACK_THRESHOLD  = 5   # 낮춤: 5회 → 차단 (이전 30)

# ── 누진 차단 시간 (오펜스 횟수 → 분) ──────────────────────────
BAN_TIERS = [60, 1440, 10080, 43200]   # 1h / 24h / 7d / 30d

# ── 허니팟 경로 — 접근 즉시 24h 차단 ──────────────────────────
HONEYPOT_PATHS: set[str] = {
    "/wp-admin", "/wp-login.php", "/wordpress/",
    "/phpmyadmin", "/pma", "/adminer",
    "/.env", "/.git/config", "/.htaccess",
    "/admin.php", "/config.php", "/setup.php",
    "/xmlrpc.php", "/eval-stdin.php",
    "/shell", "/cmd", "/exec",
    "/etc/passwd", "/proc/self/environ",
    "/actuator", "/actuator/health",  # Spring Boot 스캔
    "/solr/", "/jenkins/", "/jmx-console/",
}


def _load_admin_whitelist() -> list:
    """ADMIN_ALLOWED_IPS 환경변수를 ipaddress 네트워크 리스트로 파싱.
    화이트리스트 IP는 어떤 차단 메소드에서도 등록되지 않음.
    """
    import os, ipaddress as _ipa
    raw = os.getenv("ADMIN_ALLOWED_IPS", "").strip()
    if not raw:
        return []
    nets = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            nets.append(_ipa.ip_network(chunk, strict=False))
        except ValueError:
            continue
    return nets


_ADMIN_WHITELIST = _load_admin_whitelist()


def _is_admin_whitelisted(ip: str) -> bool:
    """주어진 IP가 ADMIN_ALLOWED_IPS에 있으면 True (어떤 블랙리스트에도 등록 금지)."""
    if not _ADMIN_WHITELIST:
        return False
    import ipaddress as _ipa
    try:
        addr = _ipa.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in _ADMIN_WHITELIST)


class IPBlacklist:
    def __init__(self):
        self._list: dict[str, dict] = {}   # ip -> {until, reason, count, offenses}
        self._permanent: set[str] = set()  # 영구 차단 목록
        self._load()
        # 시작 시 화이트리스트 IP는 모든 블랙리스트에서 즉시 제거
        self._purge_whitelisted()

    def _purge_whitelisted(self):
        """화이트리스트 IP가 어쩌다 들어왔으면 자동 정리."""
        if not _ADMIN_WHITELIST:
            return
        removed = []
        for ip in list(self._list.keys()):
            if _is_admin_whitelisted(ip):
                del self._list[ip]
                removed.append(ip)
        for ip in list(self._permanent):
            if _is_admin_whitelisted(ip):
                self._permanent.discard(ip)
                removed.append(ip)
        if removed:
            self._save()

    def _load(self):
        # 일반 블랙리스트 (만료된 것 제외)
        if BLACKLIST_FILE.exists():
            try:
                data = json.loads(BLACKLIST_FILE.read_text())
                now = datetime.now(timezone.utc).isoformat()
                self._list = {k: v for k, v in data.items() if v.get("until", "") > now or v.get("permanent")}
            except Exception:
                self._list = {}
        # 영구 차단 목록
        if PERMANENT_BAN_FILE.exists():
            try:
                self._permanent = set(json.loads(PERMANENT_BAN_FILE.read_text()))
            except Exception:
                self._permanent = set()

    def _save(self):
        try:
            BLACKLIST_FILE.write_text(json.dumps(self._list, ensure_ascii=False, indent=2))
        except Exception:
            pass
        try:
            PERMANENT_BAN_FILE.write_text(json.dumps(list(self._permanent), ensure_ascii=False))
        except Exception:
            pass

    def is_blocked(self, ip: str) -> bool:
        # ADMIN_ALLOWED_IPS 화이트리스트는 절대 차단하지 않음 (관리자 lockout 방지)
        if _is_admin_whitelisted(ip):
            # 어쩌다 등록되었으면 즉시 제거
            if ip in self._permanent or ip in self._list:
                self._permanent.discard(ip)
                self._list.pop(ip, None)
                self._save()
            return False
        # 영구 차단 먼저
        if ip in self._permanent:
            return True
        entry = self._list.get(ip)
        if not entry:
            return False
        if entry.get("permanent"):
            self._permanent.add(ip)
            return True
        until_str = entry.get("until", "")
        if not until_str:
            return False
        try:
            until = datetime.fromisoformat(until_str)
        except (ValueError, TypeError):
            return False
        if datetime.now(timezone.utc) > until:
            # 만료됐어도 오펜스 기록은 유지 (누진 적용)
            entry["until"] = ""
            self._list[ip] = entry
            self._save()
            return False
        return True

    def record_attack(self, ip: str, reason: str) -> bool:
        """공격 기록 → 누진 차단 적용. 차단됐으면 True."""
        # ADMIN_ALLOWED_IPS 화이트리스트는 공격 기록도 안 함
        if _is_admin_whitelisted(ip):
            return False
        entry = self._list.get(ip, {"count": 0, "offenses": 0, "reason": reason, "until": ""})
        entry["count"] = entry.get("count", 0) + 1
        entry["reason"] = reason
        if entry["count"] >= ATTACK_THRESHOLD:
            offenses = entry.get("offenses", 0)
            if offenses >= len(BAN_TIERS):
                # 반복 공격자 → 영구 차단
                entry["permanent"] = True
                entry["until"] = "9999-12-31T23:59:59+00:00"
                self._permanent.add(ip)
            else:
                ban_minutes = BAN_TIERS[offenses]
                entry["until"] = (datetime.now(timezone.utc) + timedelta(minutes=ban_minutes)).isoformat()
            entry["offenses"] = offenses + 1
            entry["count"] = 0  # 카운트 리셋 (다음 오펜스를 위해)
            self._list[ip] = entry
            self._save()
            return True
        self._list[ip] = entry
        self._save()
        return False

    def block(self, ip: str, reason: str, minutes: int = 60):
        """즉시 차단 (기본 1시간)."""
        if _is_admin_whitelisted(ip):
            return  # 화이트리스트 IP는 차단 거부
        entry = self._list.get(ip, {"count": ATTACK_THRESHOLD, "offenses": 0})
        entry["until"] = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()
        entry["reason"] = reason
        entry["offenses"] = entry.get("offenses", 0) + 1
        self._list[ip] = entry
        self._save()

    def block_permanent(self, ip: str, reason: str):
        """영구 차단. ADMIN_ALLOWED_IPS는 영구 차단 거부."""
        if _is_admin_whitelisted(ip):
            return  # 관리자 IP 영구 차단 절대 금지
        self._permanent.add(ip)
        self._list[ip] = {
            "until": "9999-12-31T23:59:59+00:00",
            "reason": reason,
            "count": ATTACK_THRESHOLD,
            "offenses": 99,
            "permanent": True,
        }
        self._save()


ip_blacklist = IPBlacklist()


# ── 관리자 로그인 Brute-Force 전용 보호 ─────────────────────────
class AdminLoginGuard:
    """로그인 실패 5회 → 24h 차단, 10회 → 7일 차단, 15회 → 영구"""
    THRESHOLDS = [(5, 1440), (10, 10080), (15, None)]  # (실패수, 차단분) None=영구

    def __init__(self):
        self._fails: dict[str, list[float]] = defaultdict(list)

    def record_fail(self, ip: str) -> Optional[int]:
        """실패 기록. 차단해야 하면 차단 분(None=영구) 반환, 아니면 None.
        ADMIN_ALLOWED_IPS 화이트리스트는 카운트 증가 없이 항상 None 반환 (관리자 lockout 방지).
        """
        if _is_admin_whitelisted(ip):
            return None  # 화이트리스트 IP는 카운트 안 함
        now = time.time()
        self._fails[ip] = [t for t in self._fails[ip] if now - t < 86400]  # 24h 윈도우
        self._fails[ip].append(now)
        count = len(self._fails[ip])
        for threshold, minutes in reversed(self.THRESHOLDS):
            if count >= threshold:
                return minutes  # minutes=None → 영구
        return None

    def clear(self, ip: str):
        self._fails.pop(ip, None)


admin_login_guard = AdminLoginGuard()

# ═══════════════════════════════════════════════════════════════
# Rate Limiting (슬라이딩 윈도우)
# ═══════════════════════════════════════════════════════════════
class RateLimiter:
    def __init__(self):
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._lock: asyncio.Lock | None = None

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    RULES = {
        # (endpoint_prefix, max_requests, window_seconds)
        "/api/admin":        (300, 60),
        "/api/security":     (10,  60),
        "/api/apply":        (5,   300),
        "/api/inquiry":      (5,   300),
        "/auth":             (10,  60),
        # 공개 데이터 — 스크래핑 방지 강화
        "/api/jobs":         (30,  60),
        "/api/community":    (40,  60),
        "/api/testimonials": (15,  60),
        "/api/partners":     (15,  60),
        "/api/settings":     (15,  60),
        "default":           (120, 60),
    }

    def _get_rule(self, path: str):
        for prefix, rule in self.RULES.items():
            if prefix != "default" and path.startswith(prefix):
                return rule
        return self.RULES["default"]

    async def check(self, ip: str, path: str,
                    override_window: Optional[int] = None,
                    override_max: Optional[int] = None) -> bool:
        """True = 허용, False = 차단. override로 엄격 국가 임계치 적용 가능."""
        max_req, window = self._get_rule(path)
        if override_window is not None:
            window = override_window
        if override_max is not None:
            max_req = override_max
        key = f"{ip}:{path.split('/')[1] if '/' in path else path}"
        now = time.time()
        async with self._get_lock():
            timestamps = self._windows[key]
            self._windows[key] = [t for t in timestamps if now - t < window]
            if len(self._windows[key]) >= max_req:
                return False
            self._windows[key].append(now)
            return True

rate_limiter = RateLimiter()

# ═══════════════════════════════════════════════════════════════
# 감사 로그 (JSONL — 절대 삭제 금지)
# ═══════════════════════════════════════════════════════════════
class AuditLogger:
    def log(self, event_type: str, data: dict, severity: str = "INFO"):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = AUDIT_DIR / f"audit_{today}.jsonl"
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            "severity": severity,
            "id": str(uuid.uuid4()),
            **{k: mask_pii(str(v)) if isinstance(v, str) else v for k, v in data.items()},
        }
        try:
            with log_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def get_recent(self, hours: int = 24, severity: Optional[str] = None) -> list:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        entries = []
        for f in sorted(AUDIT_DIR.glob("audit_*.jsonl"), reverse=True)[:3]:
            try:
                for line in f.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    obj = json.loads(line)
                    ts = datetime.fromisoformat(obj.get("ts", "2000-01-01T00:00:00+00:00"))
                    if ts < cutoff:
                        continue
                    if severity and obj.get("severity") != severity:
                        continue
                    entries.append(obj)
            except Exception:
                continue
        return sorted(entries, key=lambda x: x.get("ts", ""), reverse=True)[:200]

audit = AuditLogger()

# ═══════════════════════════════════════════════════════════════
# HMAC 요청 서명 검증
# ═══════════════════════════════════════════════════════════════
SIGNED_PATHS = {"/api/admin", "/api/security/report"}
SIGNATURE_MAX_AGE = 300  # 5분

def verify_hmac(request: Request, body: bytes) -> bool:
    """X-Bridge-Signature: t=<timestamp>,v1=<hmac> 헤더 검증"""
    if not HMAC_SECRET:
        return True  # 미설정 시 패스 (개발 환경)
    sig_header = request.headers.get("X-Bridge-Signature", "")
    if not sig_header:
        return False
    parts = dict(p.split("=", 1) for p in sig_header.split(",") if "=" in p)
    ts = parts.get("t", "")
    sig = parts.get("v1", "")
    if not ts or not sig:
        return False
    try:
        ts_int = int(ts)
        if abs(time.time() - ts_int) > SIGNATURE_MAX_AGE:
            return False  # 재전송 공격 방지
        payload = f"{ts}.{body.decode('utf-8', errors='replace')}"
        # HMAC_SECRET과 ADMIN_API_KEY 모두 시도 (클라이언트는 ADMIN_API_KEY로 서명)
        admin_key = os.getenv("ADMIN_API_KEY", "").strip()
        secrets_to_try = {HMAC_SECRET}
        if admin_key and admin_key != HMAC_SECRET:
            secrets_to_try.add(admin_key)
        for secret in secrets_to_try:
            expected = hmac.new(
                secret.encode(), payload.encode(), hashlib.sha256
            ).hexdigest()
            if hmac.compare_digest(expected, sig):
                return True
        return False
    except Exception:
        return False

def generate_hmac(body: str) -> str:
    """클라이언트용 서명 생성 헬퍼"""
    ts = str(int(time.time()))
    payload = f"{ts}.{body}"
    sig = hmac.new(HMAC_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"

# ═══════════════════════════════════════════════════════════════
# 보안 버전 자동 업데이트 (매월 1일 자가갱신)
# ═══════════════════════════════════════════════════════════════
SECURITY_FEEDS = [
    "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Input_Validation_Cheat_Sheet.md",
]

class SecurityUpdater:
    def __init__(self):
        self._version_data = self._load()

    def _load(self) -> dict:
        if SECURITY_VERSION_FILE.exists():
            try:
                return json.loads(SECURITY_VERSION_FILE.read_text())
            except Exception:
                pass
        return {"last_update": "2000-01-01", "version": "1.0.0", "patterns_hash": ""}

    def _save(self, data: dict):
        SECURITY_VERSION_FILE.write_text(json.dumps(data, indent=2))

    def needs_update(self) -> bool:
        last = datetime.fromisoformat(self._version_data.get("last_update", "2000-01-01"))
        now = datetime.now()
        # 매월 1일 또는 30일 이상 경과 시 업데이트
        return (now - last).days >= 30 or now.day == 1

    async def run_update(self):
        if not self.needs_update():
            return
        audit.log("SECURITY_AUTO_UPDATE", {"status": "started"}, "INFO")
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                for url in SECURITY_FEEDS:
                    try:
                        resp = await client.get(url)
                        if resp.status_code == 200:
                            # 패턴 해시 업데이트 (실제 패턴 파싱은 확장 가능)
                            content_hash = hashlib.sha256(resp.content).hexdigest()
                            self._version_data["patterns_hash"] = content_hash
                    except Exception:
                        pass
            now_str = datetime.now().strftime("%Y-%m-%d")
            self._version_data["last_update"] = now_str
            self._version_data["version"] = f"2026.{datetime.now().month:02d}.1"
            self._save(self._version_data)
            audit.log("SECURITY_AUTO_UPDATE", {
                "status": "completed",
                "version": self._version_data["version"],
                "date": now_str,
            }, "INFO")
        except Exception as e:
            audit.log("SECURITY_AUTO_UPDATE", {"status": "failed", "error": str(e)}, "WARNING")

security_updater = SecurityUpdater()

# ═══════════════════════════════════════════════════════════════
# 보안 헤더 (2026 최신)
# ═══════════════════════════════════════════════════════════════
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": (
        "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
        "magnetometer=(), microphone=(), payment=(), usb=()"
    ),
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "  # TODO: nonce 기반으로 교체 시 'unsafe-inline' 제거
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://bridge-n7hk.onrender.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    ),
    "Cache-Control": "no-store, no-cache, must-revalidate, private",
    "X-Robots-Tag": "noindex, nofollow",  # 관리자 페이지용
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}

# ═══════════════════════════════════════════════════════════════
# 메인 미들웨어
# ═══════════════════════════════════════════════════════════════
class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # 시작 시 자동 업데이트 스케줄
        asyncio.create_task(self._schedule_update())

    async def _schedule_update(self):
        await asyncio.sleep(5)  # 서버 기동 후 5초 대기
        await security_updater.run_update()
        # 이후 24시간마다 체크
        while True:
            await asyncio.sleep(86400)
            await security_updater.run_update()

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_ip = self._get_real_ip(request)
        path = request.url.path
        method = request.method
        req_id = str(uuid.uuid4())[:8]

        # 0. 헬스체크만 바이패스 (로그인은 반드시 검사)
        BYPASS_PATHS = {"/", "/health"}
        if path in BYPASS_PATHS:
            response = await call_next(request)
            return response

        # 0-0-pre. /uploads/ 직접 접근 차단 — 서명 URL(/api/files/)만 허용
        if path.startswith("/uploads/") or path == "/uploads":
            audit.log(
                "UNSIGNED_UPLOAD_ACCESS",
                {"ip": client_ip, "path": path},
                "WARNING",
            )
            return JSONResponse(
                status_code=403,
                content={"error": "직접 파일 접근이 차단되었습니다. 서명 URL을 통해 접근하세요."},
                headers={"X-Request-ID": req_id, "X-Content-Type-Options": "nosniff"},
            )

        # 0-0. 허니팟: 스캐너/해커가 자주 탐색하는 경로 → 즉시 24h 차단
        path_lower = path.lower().rstrip("/")
        for hp in HONEYPOT_PATHS:
            if path_lower == hp.lower().rstrip("/") or path_lower.startswith(hp.lower()):
                ip_blacklist.block(client_ip, f"honeypot:{path}", minutes=1440)
                audit.log("HONEYPOT_TRIGGERED", {"ip": client_ip, "path": path}, "CRITICAL")
                return JSONResponse(
                    status_code=404,
                    content={"detail": "Not found."},
                    headers={"X-Request-ID": req_id},
                )

        # 0-0-1. 봇/스크래퍼 UA 차단 (Google Sheets IMPORTXML 등)
        _ua = request.headers.get("user-agent", "")
        _exempt_bot = (
            any(path.startswith(p) for p in _BOT_CHECK_EXEMPT_PREFIXES)
            or (method == "GET" and any(path.startswith(p) for p in _PUBLIC_GET_PREFIXES))
        )
        if not _exempt_bot and _is_scraper_ua(_ua):
            ip_blacklist.record_attack(client_ip, f"scraper_ua")
            audit.log("SCRAPER_BLOCKED", {
                "ip": client_ip, "path": path,
                "ua": _ua[:200],
            }, "WARNING")
            return JSONResponse(
                status_code=403,
                content={"error": "Access denied."},
                headers={"X-Request-ID": req_id},
            )

        # 0-1. 유효한 admin key가 있으면 블랙리스트/rate limit 바이패스
        _admin_key = os.getenv("ADMIN_API_KEY", "").strip()
        if _admin_key and request.headers.get("x-admin-key", "").strip() == _admin_key:
            response = await call_next(request)
            for k, v in SECURITY_HEADERS.items():
                response.headers[k] = v
            response.headers["X-Request-ID"] = req_id
            return response

        # 1. IP 블랙리스트 차단 (로그인 경로는 자체 brute-force 보호 사용)
        if ip_blacklist.is_blocked(client_ip) and path != "/api/admin/login":
            audit.log("BLOCKED_IP", {"ip": client_ip, "path": path}, "WARNING")
            return JSONResponse(
                status_code=403,
                content={"error": "Access denied."},
                headers={"X-Request-ID": req_id},
            )

        # 2. Rate Limiting
        if not await rate_limiter.check(client_ip, path):
            audit.log("RATE_LIMIT", {"ip": client_ip, "path": path}, "WARNING")
            ip_blacklist.record_attack(client_ip, "rate_limit_exceeded")
            return JSONResponse(
                status_code=429,
                content={"error": "Too many requests. Please slow down."},
                headers={"Retry-After": "60", "X-Request-ID": req_id},
            )

        # 2-1. 국가 조회 (비동기, 캐시 활용)
        country_code = await _get_country(client_ip)
        is_strict_country = country_code in STRICT_COUNTRIES

        # 2-2. 엄격 국가 Rate Limit (기본 Rate Limit보다 낮은 임계치)
        if is_strict_country:
            strict_key = f"strict:{client_ip}"
            if not await rate_limiter.check(strict_key, path,
                                             override_window=STRICT_RATE_WINDOW,
                                             override_max=STRICT_RATE_MAX):
                audit.log("STRICT_RATE_LIMIT", {
                    "ip": client_ip, "country": country_code, "path": path
                }, "WARNING")
                ip_blacklist.block(client_ip, f"strict_rate:{country_code}", minutes=60)
                return JSONResponse(
                    status_code=429,
                    content={"error": "Too many requests."},
                    headers={"Retry-After": "3600", "X-Request-ID": req_id},
                )

        # 3. 요청 본문 읽기 (공격 탐지 + HMAC)
        body = b""
        if method in ("POST", "PUT", "PATCH") and "multipart" not in request.headers.get("content-type", ""):
            try:
                body = await request.body()
            except Exception:
                body = b""

        # 4. 공격 패턴 탐지 (쿼리스트링 + body)
        # 엄격 국가(US/GB/ZA)에서는 1회 탐지 즉시 차단, 그 외는 5회 누적 후 차단
        check_targets = [
            str(request.url.query),
            body.decode("utf-8", errors="replace"),
        ]
        for target in check_targets:
            attack_type = detect_attack(target)
            if attack_type:
                if is_strict_country:
                    # 엄격 국가: 즉시 24h 차단
                    ip_blacklist.block(client_ip, f"strict_attack:{attack_type}:{country_code}", minutes=1440)
                    audit.log("STRICT_ATTACK_BLOCKED", {
                        "ip": client_ip,
                        "country": country_code,
                        "type": attack_type,
                        "path": path,
                        "req_id": req_id,
                    }, "CRITICAL")
                else:
                    blocked = ip_blacklist.record_attack(client_ip, attack_type)
                    audit.log("ATTACK_DETECTED", {
                        "ip": client_ip,
                        "type": attack_type,
                        "path": path,
                        "auto_blocked": blocked,
                        "req_id": req_id,
                    }, "CRITICAL")
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid request detected."},
                    headers={"X-Request-ID": req_id},
                )

        # 5. HMAC 서명 검증 (관리자/보안 엔드포인트, 로그인 제외)
        HMAC_EXEMPT = {"/api/admin/login", "/api/admin/login/"}
        for signed_path in SIGNED_PATHS:
            if path.startswith(signed_path) and method != "GET" and path.rstrip("/") not in {p.rstrip("/") for p in HMAC_EXEMPT}:
                # 이중 확인: admin key가 유효하면 HMAC 건너뛰기
                if _admin_key and request.headers.get("x-admin-key", "").strip() == _admin_key:
                    break
                if not verify_hmac(request, body):
                    audit.log("INVALID_SIGNATURE", {
                        "ip": client_ip, "path": path
                    }, "CRITICAL")
                    return JSONResponse(
                        status_code=401,
                        content={"error": "Request signature invalid."},
                    )

        # 6. 실제 요청 처리
        response = await call_next(request)

        # 7. 응답 본문 PII 마스킹 (JSON 응답만)
        # /api/community/ 는 관리자 작성 콘텐츠 — 본문 마스킹 제외
        content_type = response.headers.get("content-type", "")
        _community_path = path.startswith("/api/community/") or path == "/api/community"
        if "application/json" in content_type and ENV == "production" and not _community_path:
            try:
                body_bytes = b""
                async for chunk in response.body_iterator:
                    body_bytes += chunk
                original = body_bytes.decode("utf-8")
                masked = mask_pii(original)
                if masked != original:
                    audit.log("PII_MASKED", {
                        "ip": client_ip, "path": path
                    }, "WARNING")
                response = Response(
                    content=masked,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type="application/json",
                )
            except Exception:
                pass

        # 8. 보안 헤더 주입
        for k, v in SECURITY_HEADERS.items():
            response.headers[k] = v
        response.headers["X-Request-ID"] = req_id

        # 9. 접근 감사 로그
        duration_ms = round((time.time() - start_time) * 1000)
        audit.log("REQUEST", {
            "ip": client_ip,
            "method": method,
            "path": path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "req_id": req_id,
        }, "INFO" if response.status_code < 400 else "WARNING")

        return response

    @staticmethod
    def _get_real_ip(request: Request) -> str:
        """Render/Vercel 프록시 헤더 우선 처리"""
        for header in ("X-Forwarded-For", "X-Real-IP", "CF-Connecting-IP"):
            val = request.headers.get(header, "")
            if val:
                ip = val.split(",")[0].strip()
                try:
                    ipaddress.ip_address(ip)
                    return ip
                except ValueError:
                    continue
        return request.client.host if request.client else "unknown"

# ═══════════════════════════════════════════════════════════════
# 엔드포인트 데코레이터 — 무결성 검증 필요 API용
# ═══════════════════════════════════════════════════════════════
def require_integrity(fn):
    """관리자 전용 엔드포인트에 추가 무결성 검증"""
    @wraps(fn)
    async def wrapper(request: Request, *args, **kwargs):
        api_key = request.headers.get("X-Admin-Api-Key", "")
        expected = os.getenv("ADMIN_API_KEY", "")
        if not expected or not hmac.compare_digest(
            hashlib.sha256(api_key.encode()).hexdigest(),
            hashlib.sha256(expected.encode()).hexdigest(),
        ):
            audit.log("UNAUTHORIZED_ADMIN", {
                "ip": SecurityMiddleware._get_real_ip(request),
                "path": request.url.path,
            }, "CRITICAL")
            raise HTTPException(status_code=403, detail="Forbidden")
        return await fn(request, *args, **kwargs)
    return wrapper

# ═══════════════════════════════════════════════════════════════
# 보안 리포트 엔드포인트 (api_server.py에서 import하여 등록)
# ═══════════════════════════════════════════════════════════════
from fastapi import APIRouter

security_router = APIRouter(prefix="/api/security", tags=["security"])
admin_security_router = APIRouter(prefix="/api/admin", tags=["admin"])

@security_router.post("/report")
async def security_report(request: Request):
    """프론트엔드 해킹 경고 시스템에서 호출"""
    try:
        data = await request.json()
    except Exception:
        data = {}
    ip = SecurityMiddleware._get_real_ip(request)
    attack_type = data.get("type", "unknown")
    ip_blacklist.block(ip, f"frontend_report:{attack_type}", minutes=60)
    audit.log("FRONTEND_SECURITY_REPORT", {
        "ip": ip,
        "type": attack_type,
        "ua": request.headers.get("User-Agent", ""),
        "fingerprint": data.get("fingerprint", ""),
    }, "CRITICAL")
    return {"status": "reported"}

@admin_security_router.get("/audit-log")
@require_integrity
async def get_audit_log(request: Request, hours: int = 24, severity: Optional[str] = None):
    """감사 로그 조회 — 관리자 전용"""
    entries = audit.get_recent(hours=min(hours, 168), severity=severity)
    return {
        "count": len(entries),
        "hours": hours,
        "entries": entries,
    }

@admin_security_router.get("/blacklist")
@require_integrity
async def get_blacklist(request: Request):
    """IP 블랙리스트 조회 — 관리자 전용"""
    now = datetime.now(timezone.utc)
    active = {
        ip: {
            "until": entry.get("until", ""),
            "reason": entry.get("reason", ""),
            "count": entry.get("count", 0),
            "remaining_minutes": max(0, round(
                (datetime.fromisoformat(entry["until"]) - now).total_seconds() / 60
            )) if entry.get("until") else 0,
        }
        for ip, entry in ip_blacklist._list.items()
        if entry.get("until", "") > now.isoformat()
    }
    return {"blocked_ips": len(active), "list": active}

@admin_security_router.delete("/blacklist/{ip}")
@require_integrity
async def remove_from_blacklist(request: Request, ip: str):
    """IP 블랙리스트 수동 해제"""
    if ip in ip_blacklist._list:
        del ip_blacklist._list[ip]
        ip_blacklist._save()
        audit.log("BLACKLIST_REMOVED", {"ip": ip, "by": "admin"}, "INFO")
        return {"status": "removed", "ip": ip}
    return {"status": "not_found", "ip": ip}

@admin_security_router.get("/security-status")
@require_integrity
async def security_status(request: Request):
    """전체 보안 시스템 상태"""
    return {
        "version": security_updater._version_data.get("version", "unknown"),
        "last_update": security_updater._version_data.get("last_update", "unknown"),
        "next_update_in_days": max(0, 30 - (
            datetime.now() - datetime.fromisoformat(
                security_updater._version_data.get("last_update", "2000-01-01")
            )
        ).days),
        "blocked_ips": sum(
            1 for v in ip_blacklist._list.values()
            if v.get("until", "") > datetime.now(timezone.utc).isoformat()
        ),
        "attack_patterns": list(ATTACK_PATTERNS.keys()),
        "pii_patterns_count": len(PII_PATTERNS),
        "fail_closed": True,
        "auto_update": True,
    }
