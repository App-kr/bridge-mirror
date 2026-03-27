"""
sheets_connector.py — BRIDGE Resume Converter
Google Sheets 연동

번호 컬럼: D열
환경변수: GOOGLE_SHEETS_CANDIDATES_ID / GOOGLE_SERVICE_ACCOUNT_JSON
"""

from __future__ import annotations

import os
import json
import logging
from pathlib import Path
from typing import Optional, Any

log = logging.getLogger("sheets_connector")

# ── config 로드 ────────────────────────────────────────────────────────────
_CONFIG_PATH = Path(__file__).parent / "config.json"

def _load_config() -> dict:
    if _CONFIG_PATH.exists():
        try:
            return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _get_sheet_id() -> Optional[str]:
    """시트 ID 우선순위: 환경변수 → config.json → None"""
    sid = os.getenv("GOOGLE_SHEETS_CANDIDATES_ID", "").strip()
    if sid:
        return sid
    cfg = _load_config()
    return cfg.get("sheet_id") or None


def _get_sa_credential() -> Optional[dict]:
    """
    서비스계정 자격증명 우선순위:
      1. 환경변수 GOOGLE_SERVICE_ACCOUNT_JSON (JSON 문자열)
      2. config.json → service_account_path (파일 경로)
      3. Q:/Claudework/.vault/ 에서 *service_account*.json 탐색
    """
    # 1. 환경변수
    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            if Path(raw).exists():
                return json.loads(Path(raw).read_text(encoding="utf-8"))

    # 2. config.json
    cfg = _load_config()
    sa_path = cfg.get("service_account_path", "")
    if sa_path and Path(sa_path).exists():
        return json.loads(Path(sa_path).read_text(encoding="utf-8"))

    # 3. vault 탐색
    vault = Path("Q:/Claudework/.vault")
    if vault.exists():
        for f in vault.glob("*service_account*.json"):
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue

    return None


# ── gspread 클라이언트 ──────────────────────────────────────────────────────
_client = None
_sheet  = None

def _get_client():
    global _client
    if _client is not None:
        return _client

    import gspread
    from google.oauth2.service_account import Credentials

    cred_dict = _get_sa_credential()
    if cred_dict is None:
        raise RuntimeError(
            "서비스 계정 자격증명을 찾을 수 없습니다.\n"
            "환경변수 GOOGLE_SERVICE_ACCOUNT_JSON 또는 config.json의 "
            "service_account_path 를 설정하세요."
        )

    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds   = Credentials.from_service_account_info(cred_dict, scopes=SCOPES)
    _client = gspread.authorize(creds)
    return _client


def _get_worksheet():
    global _sheet
    if _sheet is not None:
        return _sheet

    sheet_id = _get_sheet_id()
    if not sheet_id:
        raise RuntimeError(
            "구글시트 ID를 찾을 수 없습니다.\n"
            "환경변수 GOOGLE_SHEETS_CANDIDATES_ID 또는 config.json의 "
            "sheet_id 를 설정하세요."
        )

    client = _get_client()
    wb     = client.open_by_key(sheet_id)
    _sheet = wb.get_worksheet(0)
    return _sheet


# ── 공개 API ───────────────────────────────────────────────────────────────

def get_candidate_info(candidate_id: str) -> Optional[dict]:
    """
    D열에서 candidate_id 검색 → {nationality, gender, birth_year} 반환.
    없으면 None.
    """
    try:
        ws   = _get_worksheet()
        rows = ws.get_all_values()

        # 헤더 찾기 (D열 = index 3)
        for i, row in enumerate(rows):
            if len(row) > 3 and str(row[3]).strip() == str(candidate_id):
                result = {
                    "row_index": i + 1,
                    "id":        row[3] if len(row) > 3 else "",
                    "name":      row[0] if len(row) > 0 else "",  # A열
                    "nationality": "",
                    "gender":      "",
                    "birth_year":  "",
                }
                # 컬럼 매핑 (프로젝트 시트 구조에 맞게 조정 필요)
                # 일반적 구조: A=이름, B=국적, C=성별, D=번호, E=생년월일
                if len(row) > 1: result["nationality"] = row[1]
                if len(row) > 2: result["gender"]      = row[2]
                if len(row) > 4: result["birth_year"]  = row[4][:4] if row[4] else ""
                return result

        return None
    except Exception as e:
        log.error(f"get_candidate_info 오류: {e}")
        return None


def get_unprocessed_rows(limit: int = 20) -> list[dict]:
    """
    미처리 행 목록 반환 (status 컬럼이 비어있거나 '미처리').
    GUI 드롭다운용.
    """
    try:
        ws   = _get_worksheet()
        rows = ws.get_all_values()
        result = []
        for i, row in enumerate(rows[1:], start=2):  # 헤더 스킵
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
                })
            if len(result) >= limit:
                break
        return result
    except Exception as e:
        log.error(f"get_unprocessed_rows 오류: {e}")
        return []


def get_latest_unprocessed_id() -> Optional[str]:
    """최신 미처리 행의 번호 반환 (3순위 매칭용)."""
    rows = get_unprocessed_rows(limit=1)
    return rows[0]["id"] if rows else None


def write_processed_entry(
    candidate_id: str,
    output_filename: str,
    pii_count: int = 0,
    notes: str = "",
) -> bool:
    """처리완료 기록 → 해당 행 마지막 컬럼에 상태 기록."""
    try:
        ws   = _get_worksheet()
        rows = ws.get_all_values()
        for i, row in enumerate(rows):
            if len(row) > 3 and str(row[3]).strip() == str(candidate_id):
                row_num = i + 1
                # 마지막 컬럼 다음에 기록
                last_col = len(row) + 1
                from datetime import datetime
                ws.update_cell(
                    row_num, last_col,
                    f"처리완료 {datetime.now().strftime('%Y-%m-%d %H:%M')} | {output_filename} | PII:{pii_count}"
                )
                if notes:
                    ws.update_cell(row_num, last_col + 1, notes)
                log.info(f"시트 기록 완료: {candidate_id} → {output_filename}")
                return True
        log.warning(f"번호 {candidate_id} 시트에서 찾을 수 없음")
        return False
    except Exception as e:
        log.error(f"write_processed_entry 오류: {e}")
        return False


def is_connected() -> bool:
    """시트 연결 상태 확인."""
    try:
        ws = _get_worksheet()
        ws.cell(1, 1)
        return True
    except Exception:
        return False


# ── CLI 테스트 ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"시트 ID: {_get_sheet_id() or '미설정'}")
    print(f"서비스계정: {'OK' if _get_sa_credential() else '미설정'}")
    print(f"연결 상태: {'OK' if is_connected() else 'FAIL'}")

    rows = get_unprocessed_rows(5)
    print(f"미처리 행: {len(rows)}개")
    for r in rows:
        print(f"  [{r['id']}] {r['name']}")
