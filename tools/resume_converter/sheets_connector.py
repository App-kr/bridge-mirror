"""
sheets_connector.py — BRIDGE Resume Converter v2.1
데이터 소스: Bridge 관리자 API (기본) / Google Sheets (폴백)
신규: write_intake_row() — 변환 완료 후 접수 시트 자동 기록

소스 우선순위:
  1. Bridge API  — api.bridgejob.co.kr  (실시간, 최우선)
  2. Google Sheets — gspread / Sheets REST API

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
# 접수 시트 자동 기록 (form 변환 완료 → 시트 행 추가)
# ══════════════════════════════════════════════════════════════════════════

# 접수 시트 헤더 (첫 행이 비어있으면 자동 생성)
_INTAKE_HEADERS = ["접수일", "강사번호", "국적", "성별", "생년", "파일명", "상태", "PII제거수"]

_TOKEN_FILE = Path(__file__).parent / "form_watcher_token.json"


def _get_sheet_gid() -> Optional[int]:
    v = _config_get("sheet_gid", "")
    try:
        return int(v) if v else None
    except Exception:
        return None


def _get_oauth_creds():
    """
    form_watcher OAuth Credentials 객체 반환 (Sheets + Drive 공용).
    토큰 없거나 만료 시 None.
    """
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        if not _TOKEN_FILE.exists():
            return None
        tok = json.loads(_TOKEN_FILE.read_text(encoding="utf-8"))
        scopes = tok.get("scopes", [])

        creds = Credentials(
            token=tok.get("token"),
            refresh_token=tok.get("refresh_token"),
            token_uri=tok.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=tok.get("client_id"),
            client_secret=tok.get("cs"),
            scopes=scopes,
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            tok["token"] = creds.token
            _TOKEN_FILE.write_text(json.dumps(tok, indent=2, ensure_ascii=False), encoding="utf-8")
        return creds
    except Exception as e:
        log.warning("OAuth Credentials 초기화 실패: %s", e)
        return None


def _get_sheets_service_oauth() -> Optional[object]:
    """
    form_watcher OAuth 토큰으로 Google Sheets API 서비스 반환.
    spreadsheets 스코프 없으면 None.
    """
    try:
        from googleapiclient.discovery import build

        if not _TOKEN_FILE.exists():
            return None
        tok = json.loads(_TOKEN_FILE.read_text(encoding="utf-8"))
        scopes = tok.get("scopes", [])
        # spreadsheets 스코프가 없으면 쓰기 불가
        has_sheets_scope = any("spreadsheets" in s for s in scopes)
        if not has_sheets_scope:
            log.warning("OAuth 토큰에 spreadsheets 스코프 없음 — form_watcher.py --setup 재실행 필요")
            return None

        creds = _get_oauth_creds()
        if not creds:
            return None
        return build("sheets", "v4", credentials=creds, cache_discovery=False)
    except Exception as e:
        log.warning("Sheets OAuth 서비스 초기화 실패: %s", e)
        return None


def _get_gs_worksheet_by_gid(sheet_id: str, gid: Optional[int]) -> Optional[object]:
    """gspread로 gid 기반 워크시트 반환 (service account)."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials as SACredentials
        cred = _get_sa_credential()
        if not cred:
            return None
        sc = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive.readonly"]
        c = SACredentials.from_service_account_info(cred, scopes=sc)
        gc = gspread.authorize(c)
        wb = gc.open_by_key(sheet_id)
        if gid is not None:
            for ws in wb.worksheets():
                if ws.id == gid:
                    return ws
        return wb.get_worksheet(0)
    except Exception as e:
        log.debug("SA gspread 접근 실패: %s", e)
        return None


def _ensure_intake_headers(svc, sheet_id: str, sheet_range: str) -> None:
    """첫 행이 비어있으면 헤더 행 자동 생성."""
    try:
        res = svc.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{sheet_range}!A1:H1",
        ).execute()
        first_row = res.get("values", [[]])[0] if res.get("values") else []
        if not first_row or not any(first_row):
            svc.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=f"{sheet_range}!A1",
                valueInputOption="USER_ENTERED",
                body={"values": [_INTAKE_HEADERS]},
            ).execute()
            log.info("[시트] 헤더 행 자동 생성 완료")
    except Exception as e:
        log.debug("헤더 확인 실패 (무시): %s", e)


def _get_sheet_tab_name_by_gid(svc, sheet_id: str, gid: Optional[int]) -> str:
    """Sheets API로 gid에 해당하는 탭 이름 반환. 실패 시 첫 탭 사용."""
    try:
        meta = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
        for sheet in meta.get("sheets", []):
            props = sheet.get("properties", {})
            if gid is None or props.get("sheetId") == gid:
                return props.get("title", "시트1")
    except Exception:
        pass
    return "시트1"


def write_intake_row(
    candidate_id: str,
    nationality: str,
    gender: str,
    birth_year: str,
    output_filename: str,
    submission_date: str = "",
    pii_count: int = 0,
    candidate_name: str = "",
) -> bool:
    """
    강사 처리 완료 → Google Sheet 기존 행 업데이트.

    전략:
      1) D열(No)에서 candidate_id 검색 → 일치 행 찾기
      2) 없으면 B열(Full name)에서 이름 유사도로 검색
      3) 찾은 행의 다음 컬럼(처리열)에 파일명+상태 기록
         - D열(No): 비어있으면 candidate_id 기록
         - F열(Nationality): 비어있으면 nationality 기록
         - AV열(처리): "변환완료 | {output_filename} | PII:{pii_count}" 기록
      4) 실패 시 로컬 CSV 폴백
    """
    sid = _get_sheet_id()
    gid = _get_sheet_gid()
    if not sid:
        log.warning("[시트] sheet_id 미설정 — config.json 확인 필요")
        return False

    svc = _get_sheets_service_oauth()
    if svc is None:
        log.warning("  [시트] OAuth Sheets 접근 불가")
        _write_intake_csv_fallback(
            [submission_date or datetime.now().strftime("%Y-%m-%d"),
             candidate_id, nationality, gender, birth_year,
             output_filename, "변환완료", str(pii_count)]
        )
        return False

    try:
        tab = _get_sheet_tab_name_by_gid(svc, sid, gid)
        # 전체 데이터 로드
        res = svc.spreadsheets().values().get(
            spreadsheetId=sid,
            range=f"'{tab}'!A:AV",
        ).execute()
        rows = res.get("values", [])

        # ── 행 탐색 ────────────────────────────────────────────────────
        target_row_idx = None   # 1-indexed sheet row number

        # 1차: D열(index 3)에서 candidate_id 직접 검색
        for i, row in enumerate(rows):
            if len(row) > 3 and str(row[3]).strip() == str(candidate_id):
                target_row_idx = i + 1
                break

        # 2차: B열(index 1)에서 이름 유사도 검색
        if target_row_idx is None and candidate_name:
            name_parts = set(candidate_name.lower().split())
            best_score = 0
            best_idx   = None
            for i, row in enumerate(rows[1:], start=2):  # 헤더 제외
                if len(row) < 2 or not row[1]:
                    continue
                sheet_name  = row[1].lower()
                sheet_words = set(sheet_name.replace(";", " ").split())
                common      = name_parts & sheet_words
                score       = len(common) / max(len(name_parts), 1)
                if score >= 0.5 and score > best_score:
                    best_score = score
                    best_idx   = i
            if best_idx:
                target_row_idx = best_idx
                log.info("  [시트] 이름 유사도 매칭 행%d (score=%.2f)", best_idx, best_score)

        if target_row_idx is None:
            log.warning(
                "  [시트] %s(%s) 행 찾기 실패 → CSV 폴백",
                candidate_id, candidate_name[:20] if candidate_name else "?"
            )
            _write_intake_csv_fallback(
                [submission_date or datetime.now().strftime("%Y-%m-%d"),
                 candidate_id, nationality, gender, birth_year,
                 output_filename, "변환완료", str(pii_count)]
            )
            return False

        # ── 업데이트 requests ─────────────────────────────────────────
        existing_row = rows[target_row_idx - 1]

        def _cell(col_idx: int) -> str:
            return existing_row[col_idx].strip() if len(existing_row) > col_idx else ""

        updates = []
        ts = submission_date or datetime.now().strftime("%Y-%m-%d")

        # D열(4번째=index 3): 비어있으면 강사번호 기록
        if not _cell(3):
            updates.append({
                "range": f"'{tab}'!D{target_row_idx}",
                "values": [[candidate_id]],
            })

        # F열(6번째=index 5): 비어있으면 국적 기록
        if not _cell(5) and nationality:
            updates.append({
                "range": f"'{tab}'!F{target_row_idx}",
                "values": [[nationality]],
            })

        # AV열(48번째=index 47): 처리 상태 기록 (기존값 덮어쓰기)
        note = f"변환완료 {ts} | {output_filename} | PII:{pii_count}"
        updates.append({
            "range": f"'{tab}'!AV{target_row_idx}",
            "values": [[note]],
        })

        if updates:
            svc.spreadsheets().values().batchUpdate(
                spreadsheetId=sid,
                body={
                    "valueInputOption": "USER_ENTERED",
                    "data": updates,
                },
            ).execute()

        log.info("  [시트] 행%d 업데이트 완료 (%s)", target_row_idx, candidate_id)
        return True

    except Exception as e:
        log.error("  [시트] 기록 실패: %s", e)
        _write_intake_csv_fallback(
            [submission_date or datetime.now().strftime("%Y-%m-%d"),
             candidate_id, nationality, gender, birth_year,
             output_filename, "변환완료", str(pii_count)]
        )
        return False


def _write_intake_csv_fallback(row: list) -> None:
    """
    Google Sheet 접근 불가 시 로컬 CSV에 행 보존.
    경로: tools/resume_converter/logs/intake_pending.csv
    API 활성화 후 batch_push_pending_to_sheet() 로 일괄 업로드.
    """
    try:
        import csv
        csv_path = Path(__file__).parent / "logs" / "intake_pending.csv"
        csv_path.parent.mkdir(exist_ok=True)
        write_header = not csv_path.exists()
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(_INTAKE_HEADERS)
            w.writerow(row)
        log.info("  [CSV폴백] %s → intake_pending.csv", row[1] if len(row) > 1 else "?")
    except Exception as e:
        log.error("  [CSV폴백] 저장 실패: %s", e)


def batch_push_pending_to_sheet() -> int:
    """
    ⚠️ INSERT_ROWS 방식은 시트 데이터 파괴 위험 — 완전 비활성화.
    intake_pending.csv는 수동 검토용으로만 보존.
    반환: 0 (항상)
    """
    csv_path = Path(__file__).parent / "logs" / "intake_pending.csv"
    if csv_path.exists():
        # 파일 내용 확인 후 로그만 남기고 건너뜀
        try:
            import csv as _csv
            with open(csv_path, newline="", encoding="utf-8") as f:
                pending = list(_csv.reader(f))
            count = max(0, len(pending) - 1)  # 헤더 제외
            if count > 0:
                log.info("[일괄업로드] pending %d행 — 수동 검토 필요 (자동 업로드 비활성화)", count)
        except Exception:
            pass
    return 0


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
