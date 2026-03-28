"""
sheets_connector.py — BRIDGE Resume Converter v2.0
데이터 소스: Bridge 관리자 API (기본) / Google Sheets (폴백)

소스 우선순위:
  1. Bridge API  — api.bridgejob.co.kr  (실시간, 최우선)
  2. Google Sheets — gspread (폴백)

보안 원칙:
  - 자격증명은 모두 keyring에만 저장 (디스크 평문 없음)
  - HTTPS 강제 (http:// URL 거부)
  - 세션 토큰은 메모리에만 보관 (디스크 저장 없음)
  - PII 로그 금지 (이름/이메일 등 마스킹)
  - 요청 타임아웃 10초
  - URL은 keyring/config로 관리 (하드코딩 없음)
"""

from __future__ import annotations

import hashlib
import hmac as hmac_module
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

log = logging.getLogger("sheets_connector")

# ── 운영 도메인 (기본값 — keyring에 override 가능) ─────────────────────────
_BRIDGE_API_DEFAULT = "https://api.bridgejob.co.kr"

# ── keyring 서비스 이름 ──────────────────────────────────────────────────
_KR_SVC  = "BRIDGE_RC_CONFIG_V1"

# ── config 경로 ────────────────────────────────────────────────────────────
_CONFIG  = Path(__file__).parent / "config.json"

# ── 메모리 캐시 (세션 토큰 — 디스크 저장 없음) ─────────────────────────────
_bridge_session: dict = {}       # {"token": str, "expires": float}
_bridge_session_lock = threading.Lock()

# ── Google Sheets 클라이언트 캐시 ─────────────────────────────────────────
_gs_client = None
_gs_sheet  = None


# ══════════════════════════════════════════════════════════════════════════
# keyring 헬퍼
# ══════════════════════════════════════════════════════════════════════════

def _kr_get(key: str, default: str = "") -> str:
    """keyring에서 값 읽기 — 없으면 default."""
    try:
        import keyring
        val = keyring.get_password(_KR_SVC, key)
        return val if val else default
    except Exception:
        return default


def _config_get(key: str, default: str = "") -> str:
    """config.json에서 값 읽기 — 없으면 default."""
    try:
        if _CONFIG.exists():
            data = json.loads(_CONFIG.read_text(encoding="utf-8"))
            return data.get(key, default) or default
    except Exception:
        pass
    return default


# ══════════════════════════════════════════════════════════════════════════
# 소스 선택
# ══════════════════════════════════════════════════════════════════════════

def _get_source() -> str:
    """
    데이터 소스 결정.
    우선순위: keyring("source") → config.json("source") → "auto"
    "auto"이면 Bridge API 시도 → 실패 시 Google Sheets 폴백.
    """
    src = _kr_get("source") or _config_get("source", "auto")
    return src if src in ("bridge", "sheets", "auto") else "auto"


# ══════════════════════════════════════════════════════════════════════════
# Bridge API — 보안
# ══════════════════════════════════════════════════════════════════════════

def _validate_url(url: str) -> str:
    """
    HTTPS URL만 허용.
    - http:// 거부
    - 빈 URL → 기본 운영 도메인
    - 알 수 없는 도메인 경고 (Vercel 임시 URL 감지)
    """
    if not url:
        return _BRIDGE_API_DEFAULT
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"HTTPS URL만 허용됩니다. (입력: {url[:40]})")
    # Vercel 임시 URL 감지 → 운영 도메인으로 교체
    if "vercel.app" in url:
        log.warning(
            "Vercel 임시 URL 감지 → 운영 도메인(%s)으로 자동 대체합니다.",
            _BRIDGE_API_DEFAULT)
        return _BRIDGE_API_DEFAULT
    return url.rstrip("/")


def _get_bridge_api_url() -> str:
    """Bridge API URL 결정 (keyring > config > 기본값)."""
    raw = _kr_get("api_url") or _config_get("api_url", "")
    try:
        return _validate_url(raw)
    except ValueError as e:
        log.warning("URL 검증 실패, 기본값 사용: %s", e)
        return _BRIDGE_API_DEFAULT


def _bridge_login() -> Optional[str]:
    """
    Bridge 관리자 로그인 → 세션 토큰 반환 (메모리 캐시).
    비밀번호는 keyring에서만 읽음 — 절대 로그 기록 없음.
    """
    global _bridge_session

    # 캐시된 토큰이 유효하면 재사용
    with _bridge_session_lock:
        tok  = _bridge_session.get("token", "")
        exp  = _bridge_session.get("expires", 0.0)
        if tok and time.time() < exp - 60:   # 60초 여유
            return tok

    pw = _kr_get("admin_pw")
    if not pw:
        log.debug("관리자 비밀번호 미설정 — Bridge API 로그인 불가")
        return None

    base = _get_bridge_api_url()
    try:
        import urllib.request
        import ssl
        body = json.dumps({"password": pw}).encode()
        req  = urllib.request.Request(
            f"{base}/api/admin/login",
            data=body,
            headers={"Content-Type": "application/json",
                     "User-Agent": "BRIDGEConverter/2.0"},
            method="POST",
        )
        ctx = ssl.create_default_context()   # 시스템 CA 검증
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            token  = data.get("session_token", "")
            max_age = data.get("expires_in", 28800)  # 기본 8시간
            if not token:
                log.warning("Bridge 로그인 응답에 session_token 없음")
                return None
            with _bridge_session_lock:
                _bridge_session = {
                    "token":   token,
                    "expires": time.time() + max_age,
                }
            return token
    except Exception as e:
        log.warning("Bridge 로그인 실패: %s", type(e).__name__)
        return None
    finally:
        # 비밀번호 변수 즉시 소각
        pw = "\x00" * len(pw)
        del pw


def _bridge_get(path: str, params: dict | None = None) -> Optional[dict]:
    """
    Bridge Admin API GET 요청.
    - HTTPS 강제
    - 세션 토큰 자동 갱신
    - 타임아웃 10초
    - 응답 크기 제한 (1MB)
    - 에러 응답 구조화 로그 (PII 없음)
    """
    token = _bridge_login()
    if not token:
        return None

    base = _get_bridge_api_url()
    url  = f"{base}{path}"

    if params:
        from urllib.parse import urlencode
        url += "?" + urlencode(params)

    try:
        import urllib.request
        import ssl
        req = urllib.request.Request(
            url,
            headers={
                "x-admin-token": token,
                "User-Agent":    "BRIDGEConverter/2.0",
                "Accept":        "application/json",
            },
            method="GET",
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            raw = resp.read(1_048_576)   # 최대 1MB
            return json.loads(raw.decode())
    except Exception as e:
        log.warning("Bridge API 요청 실패 [%s]: %s", path, type(e).__name__)
        return None


# ══════════════════════════════════════════════════════════════════════════
# Google Sheets 연결 (폴백)
# ══════════════════════════════════════════════════════════════════════════

def _get_sa_credential() -> Optional[dict]:
    """
    서비스계정 자격증명.
    우선순위: vault_import → keyring(sa_json) → 환경변수 → config.json
    """
    # 0. gc_sa.enc vault
    try:
        from .vault_import import load_service_account_dict, VAULT_FILE
        if VAULT_FILE.exists():
            return load_service_account_dict()
    except Exception as e:
        log.debug("vault 로드 실패: %s", type(e).__name__)

    # 1. keyring(sa_json)
    sa_str = _kr_get("sa_json")
    if sa_str:
        try:
            return json.loads(sa_str)
        except Exception:
            pass

    # 2. 환경변수
    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            if Path(raw).exists():
                try:
                    return json.loads(Path(raw).read_text(encoding="utf-8"))
                except Exception:
                    pass

    # 3. config.json 경로 (평문 경고)
    sa_path = _config_get("service_account_path")
    if sa_path and Path(sa_path).exists():
        log.warning("config.json의 평문 SA JSON 사용 중 → keyring으로 이전 권장")
        try:
            return json.loads(Path(sa_path).read_text(encoding="utf-8"))
        except Exception:
            pass

    return None


def _get_sheet_id() -> Optional[str]:
    return (os.getenv("GOOGLE_SHEETS_CANDIDATES_ID", "").strip()
            or _kr_get("sheet_id")
            or _config_get("sheet_id")
            or None)


def _get_gs_worksheet():
    global _gs_client, _gs_sheet
    if _gs_sheet is not None:
        return _gs_sheet

    import gspread
    from google.oauth2.service_account import Credentials

    cred = _get_sa_credential()
    if not cred:
        raise RuntimeError("Google 서비스계정 자격증명 없음")
    sid = _get_sheet_id()
    if not sid:
        raise RuntimeError("Google Sheets ID 없음")

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive.readonly"]
    c      = Credentials.from_service_account_info(cred, scopes=SCOPES)
    _gs_client = gspread.authorize(c)
    wb         = _gs_client.open_by_key(sid)
    _gs_sheet  = wb.get_worksheet(0)
    return _gs_sheet


# ══════════════════════════════════════════════════════════════════════════
# 공개 API
# ══════════════════════════════════════════════════════════════════════════

def get_candidate_info(candidate_id: str) -> Optional[dict]:
    """
    강사 정보 조회 → {nationality, gender, birth_year, name, ...}.
    - candidate_id: 숫자 문자열 (강사 번호 / sheet_number)
    - 로그에 이름/연락처 등 PII 출력 않음
    """
    # 입력 검증
    if not candidate_id or not str(candidate_id).isdigit():
        return None

    src = _get_source()

    # ── Bridge API ─────────────────────────────────────────────────
    if src in ("bridge", "auto"):
        data = _bridge_get(f"/api/admin/candidates",
                           {"search": candidate_id, "limit": "1",
                            "field": "sheet_number"})
        if data:
            items = data.get("candidates") or data.get("data") or []
            if isinstance(items, list) and items:
                row = items[0]
            elif isinstance(data, dict) and "id" in data:
                row = data
            else:
                row = None
            if row:
                return {
                    "id":          str(row.get("sheet_number", candidate_id)),
                    "name":        row.get("name", ""),
                    "nationality": row.get("nationality", ""),
                    "gender":      row.get("gender", ""),
                    "birth_year":  str(row.get("birth_year", ""))[:4],
                    "stage":       row.get("stage", ""),
                    "email":       row.get("email", ""),
                    "_source":     "bridge",
                }
        if src == "bridge":
            return None   # 폴백 없음

    # ── Google Sheets 폴백 ────────────────────────────────────────
    try:
        ws   = _get_gs_worksheet()
        rows = ws.get_all_values()
        for i, row in enumerate(rows):
            if len(row) > 3 and str(row[3]).strip() == str(candidate_id):
                return {
                    "row_index":   i + 1,
                    "id":          row[3] if len(row) > 3 else "",
                    "name":        row[0] if len(row) > 0 else "",
                    "nationality": row[1] if len(row) > 1 else "",
                    "gender":      row[2] if len(row) > 2 else "",
                    "birth_year":  row[4][:4] if len(row) > 4 and row[4] else "",
                    "_source":     "sheets",
                }
        return None
    except Exception as e:
        log.error("get_candidate_info(GS) 실패: %s", type(e).__name__)
        return None


def get_unprocessed_rows(limit: int = 20) -> list[dict]:
    """미처리 행 목록 — GUI 미처리 목록에 표시."""
    # limit 안전 제한
    limit = min(max(1, limit), 100)
    src   = _get_source()

    # ── Bridge API ─────────────────────────────────────────────────
    if src in ("bridge", "auto"):
        data = _bridge_get("/api/admin/candidates",
                           {"stage": "접수,대기", "limit": str(limit),
                            "sort": "created_at:desc"})
        if data:
            items = data.get("candidates") or data.get("data") or []
            if isinstance(items, list):
                return [
                    {
                        "id":     str(r.get("sheet_number", "")),
                        "name":   r.get("name", ""),
                        "status": r.get("stage", ""),
                        "error":  r.get("processing_error", ""),
                        "_source": "bridge",
                    }
                    for r in items if r.get("sheet_number")
                ]
        if src == "bridge":
            return []

    # ── Google Sheets 폴백 ────────────────────────────────────────
    try:
        ws     = _get_gs_worksheet()
        rows   = ws.get_all_values()
        result = []
        for i, row in enumerate(rows[1:], start=2):
            if len(row) < 4:
                continue
            cid    = str(row[3]).strip()
            status = row[-1].strip() if row else ""
            if cid and status in ("", "미처리", "접수"):
                result.append({
                    "row":    i,
                    "id":     cid,
                    "name":   row[0] if row else "",
                    "status": status,
                    "error":  "",
                    "_source": "sheets",
                })
            if len(result) >= limit:
                break
        return result
    except Exception as e:
        log.error("get_unprocessed_rows(GS) 실패: %s", type(e).__name__)
        return []


def get_latest_unprocessed_id() -> Optional[str]:
    rows = get_unprocessed_rows(limit=1)
    return rows[0]["id"] if rows else None


def write_processed_entry(
    candidate_id: str,
    output_filename: str,
    pii_count: int = 0,
    notes: str = "",
) -> bool:
    """처리 완료 기록."""
    src = _get_source()

    if src in ("bridge", "auto"):
        ts  = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        res = _bridge_get(f"/api/admin/candidates/{candidate_id}/processed",
                          {"filename": output_filename,
                           "pii_count": str(pii_count),
                           "processed_at": ts})
        if res:
            return True
        if src == "bridge":
            return False

    # Google Sheets 기록
    try:
        ws   = _get_gs_worksheet()
        rows = ws.get_all_values()
        for i, row in enumerate(rows):
            if len(row) > 3 and str(row[3]).strip() == str(candidate_id):
                row_num  = i + 1
                last_col = len(row) + 1
                ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                ws.update_cell(row_num, last_col,
                               f"처리완료 {ts} | {output_filename} | PII:{pii_count}")
                if notes:
                    ws.update_cell(row_num, last_col + 1, notes)
                return True
        return False
    except Exception as e:
        log.error("write_processed_entry(GS) 실패: %s", type(e).__name__)
        return False


def is_connected() -> bool:
    """연결 상태 확인."""
    src = _get_source()

    if src in ("bridge", "auto"):
        token = _bridge_login()
        if token:
            return True
        if src == "bridge":
            return False

    try:
        ws = _get_gs_worksheet()
        ws.cell(1, 1)
        return True
    except Exception:
        return False


def get_active_source() -> str:
    """현재 활성 소스 이름 (표시용)."""
    src = _get_source()
    if src == "bridge":
        return "Bridge API"
    if src == "sheets":
        return "Google Sheets"
    # auto: 실제 연결된 소스 판별
    token = _bridge_login()
    return "Bridge API" if token else "Google Sheets"


# ══════════════════════════════════════════════════════════════════════════
# CLI 테스트
# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print(f"소스 설정: {_get_source()}")
    print(f"API URL  : {_get_bridge_api_url()}")
    print(f"연결 상태: {'OK' if is_connected() else 'FAIL'}")
    print(f"활성 소스: {get_active_source()}")
    rows = get_unprocessed_rows(3)
    print(f"미처리 행: {len(rows)}개")
    for r in rows:
        # PII 마스킹: 이름 첫 자만 표시
        name_masked = (r["name"][0] + "**") if r.get("name") else "???"
        print(f"  [{r['id']}] {name_masked} [{r['_source']}]")
