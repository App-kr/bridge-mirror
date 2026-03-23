"""
통합 수신함 + 통계 API 모듈 (SQLite)
- api_server.py에서 import하여 라우터 등록
- 엔드포인트: /api/admin/inbox, /api/admin/stats, /api/admin/stats/monthly, /api/admin/stats/by-source
"""
import hashlib
import os
import re
import sqlite3
import logging
import time as _time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field

_log = logging.getLogger("bridge.inbox")

# ── 설정 ──────────────────────────────────────────────────────────────────────
_ADMIN_DB_PATH = Path(os.getenv("BRIDGE_DB_PATH", "./master.db"))
_ADMIN_KEY = os.getenv("ADMIN_API_KEY", "")
_IS_PROD = os.getenv("BRIDGE_ENV", "") == "production"

router = APIRouter(prefix="/api/admin", tags=["inbox"])


# ── 인증 ──────────────────────────────────────────────────────────────────────
def _check_admin(request: Request):
    """ADMIN_API_KEY 헤더 검증."""
    if not _ADMIN_KEY:
        if _IS_PROD:
            raise HTTPException(status_code=503, detail="관리자 기능 비활성화")
        return
    if request.headers.get("x-admin-key", "") != _ADMIN_KEY:
        raise HTTPException(status_code=403, detail="관리자 키가 올바르지 않습니다.")


# ── DB 헬퍼 ───────────────────────────────────────────────────────────────────
def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    return conn


def ok(data=None, message: str = "ok"):
    return {"success": True, "message": message, "data": data}


# ── DB 마이그레이션 (read_at 컬럼) ────────────────────────────────────────────
def _ensure_read_at_cols():
    """candidates, client_inquiries에 read_at 컬럼 추가 (없으면)."""
    try:
        conn = _get_conn()
        for tbl in ("candidates", "client_inquiries"):
            try:
                conn.execute(f"ALTER TABLE {tbl} ADD COLUMN read_at TEXT")
            except Exception:
                pass  # already exists
        conn.commit()
        conn.close()
    except Exception:
        pass


try:
    _ensure_read_at_cols()
except Exception:
    pass


# ── 보안 헬퍼 ────────────────────────────────────────────────────────────────
_RATE_LIMIT: dict[str, list[float]] = {}


def _rate_ok(ip_hash: str, window: int = 300, max_posts: int = 30) -> bool:
    """5분 안에 최대 30건."""
    now = _time.time()
    ts = _RATE_LIMIT.get(ip_hash, [])
    ts = [t for t in ts if now - t < window]
    if len(ts) >= max_posts:
        return False
    ts.append(now)
    _RATE_LIMIT[ip_hash] = ts
    return True


def _sanitize_search(raw: str) -> str:
    """SQL LIKE에 안전한 검색어로 변환."""
    cleaned = re.sub(r"[^a-zA-Z0-9가-힣ㄱ-ㅎㅏ-ㅣ\s@.\-]", "", raw).strip()[:100]
    return cleaned.replace("%", "").replace("_", "")


def _get_ip_hash(request: Request) -> str:
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


# ── 응답 모델 ─────────────────────────────────────────────────────────────────
VALID_STATUSES = {"new", "reviewed", "contacted", "interview", "hired", "rejected"}


class StatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=20)


class BulkAction(BaseModel):
    ids: list[str] = Field(...)
    action: str = Field(...)   # "mark_status" | "assign"
    value: str = Field(...)


# ── TTL 캐시 (stats) ─────────────────────────────────────────────────────────
_stats_cache: dict = {"data": None, "ts": 0}
_STATS_TTL = 60  # seconds


# ── GET /api/admin/inbox ──────────────────────────────────────────────────────
@router.get("/inbox")
async def admin_inbox(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    source: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort: str = "newest",
):
    """통합 수신함 - candidates + client_inquiries 통합 조회."""
    _check_admin(request)

    conn = _get_conn()
    try:
        items: list[dict] = []

        # ── candidates 조회 ──────────────────────────────────────────────
        if source != "inquiry":
            where_parts = ["(is_deleted IS NULL OR is_deleted=0)"]
            params: list = []

            if source and source != "all":
                where_parts.append("source = ?")
                params.append(source)
            if status and status != "all":
                where_parts.append("inbox_status = ?")
                params.append(status)
            if search:
                safe_q = _sanitize_search(search)
                if safe_q:
                    where_parts.append(
                        "(full_name LIKE ? OR email LIKE ? OR nationality LIKE ?)"
                    )
                    like_val = f"%{safe_q}%"
                    params.extend([like_val, like_val, like_val])

            where_sql = " AND ".join(where_parts)
            order = "created_at DESC" if sort != "oldest" else "created_at ASC"

            rows = conn.execute(
                f"""SELECT candidate_id, full_name, email, nationality,
                           current_location, area_prefs, source, inbox_status,
                           notes, assigned_to, created_at, updated_at,
                           last_activity, gmail_message_id, read_at
                    FROM candidates
                    WHERE {where_sql}
                    ORDER BY {order}""",
                params,
            ).fetchall()

            for r in rows:
                items.append({
                    "id": str(r["candidate_id"]),
                    "type": "candidate",
                    "name": r["full_name"] or "",
                    "email": r["email"] or "",
                    "nationality": r["nationality"] or "",
                    "location": r["current_location"] or "",
                    "area_prefs": r["area_prefs"] or "",
                    "source": r["source"] or "website",
                    "inbox_status": r["inbox_status"] or "new",
                    "notes": r["notes"] or "",
                    "assigned_to": r["assigned_to"] or "",
                    "created_at": r["created_at"] or "",
                    "updated_at": r["updated_at"] or "",
                    "last_activity": r["last_activity"] or "",
                    "read_at": r["read_at"] or "",
                })

        # ── client_inquiries 조회 ────────────────────────────────────────
        if source in (None, "all", "inquiry"):
            inq_where = ["(is_deleted IS NULL OR is_deleted=0)"]
            inq_params: list = []

            if status and status != "all":
                inq_where.append("inbox_status = ?")
                inq_params.append(status)
            if search:
                safe_q = _sanitize_search(search)
                if safe_q:
                    inq_where.append(
                        "(school_name LIKE ? OR contact_name LIKE ? OR email LIKE ?)"
                    )
                    like_val = f"%{safe_q}%"
                    inq_params.extend([like_val, like_val, like_val])

            inq_where_sql = " AND ".join(inq_where)
            order = "submitted_at DESC" if sort != "oldest" else "submitted_at ASC"

            inq_rows = conn.execute(
                f"""SELECT id, school_name, email, contact_name, phone,
                           location, inbox_status, notes, assigned_to,
                           submitted_at, last_activity, read_at
                    FROM client_inquiries
                    WHERE {inq_where_sql}
                    ORDER BY {order}""",
                inq_params,
            ).fetchall()

            for r in inq_rows:
                items.append({
                    "id": str(r["id"]),
                    "type": "inquiry",
                    "name": r["contact_name"] or r["school_name"] or "",
                    "email": r["email"] or "",
                    "nationality": "",
                    "location": r["location"] or "",
                    "area_prefs": "",
                    "source": "inquiry",
                    "inbox_status": r["inbox_status"] or "new",
                    "school_name": r["school_name"] or "",
                    "notes": r["notes"] or "",
                    "assigned_to": r["assigned_to"] or "",
                    "created_at": r["submitted_at"] or "",
                    "updated_at": "",
                    "last_activity": r["last_activity"] or "",
                    "read_at": r["read_at"] or "",
                })

        # 정렬
        items.sort(key=lambda x: x.get("created_at", ""), reverse=(sort != "oldest"))
        total = len(items)

        # 페이지네이션
        start = (page - 1) * per_page
        paged = items[start:start + per_page]

        return ok(data={
            "items": paged,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if per_page else 1,
        })

    except HTTPException:
        raise
    except Exception as e:
        _log.error("inbox fetch error: %s", e, exc_info=True)
        raise HTTPException(500, "수신함 데이터를 불러올 수 없습니다.")
    finally:
        conn.close()


# ── PATCH /api/admin/inbox/{id}/status ────────────────────────────────────────
@router.patch("/inbox/{item_id}/status")
async def admin_inbox_update_status(item_id: str, body: StatusUpdate, request: Request):
    """수신함 상태 변경 + read_at 타임스탬프."""
    _check_admin(request)

    if body.status not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status. Valid: {', '.join(sorted(VALID_STATUSES))}")

    now_iso = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    try:
        # candidates 먼저 시도 (candidate_id로 매칭)
        r = conn.execute(
            "SELECT candidate_id FROM candidates WHERE candidate_id = ?", (item_id,)
        ).fetchone()
        if r:
            conn.execute(
                """UPDATE candidates
                   SET inbox_status = ?, last_activity = ?, read_at = COALESCE(read_at, ?)
                   WHERE candidate_id = ?""",
                (body.status, now_iso, now_iso, item_id),
            )
            conn.commit()
            _stats_cache["ts"] = 0  # 캐시 무효화
            return ok(message=f"Status updated to {body.status}")

        # client_inquiries
        r = conn.execute(
            "SELECT id FROM client_inquiries WHERE id = ?", (item_id,)
        ).fetchone()
        if r:
            conn.execute(
                """UPDATE client_inquiries
                   SET inbox_status = ?, last_activity = ?, read_at = COALESCE(read_at, ?)
                   WHERE id = ?""",
                (body.status, now_iso, now_iso, item_id),
            )
            conn.commit()
            _stats_cache["ts"] = 0
            return ok(message=f"Status updated to {body.status}")

        raise HTTPException(404, "Item not found")

    except HTTPException:
        raise
    except Exception as e:
        _log.error("inbox status update error: %s", e)
        raise HTTPException(500, "상태 변경 실패")
    finally:
        conn.close()


# ── GET /api/admin/inbox/{id} — 상세 조회 ─────────────────────────────────────
@router.get("/inbox/{item_id}")
async def admin_inbox_detail(item_id: str, request: Request):
    """수신함 항목 상세 — 지원자 또는 구인문의."""
    _check_admin(request)

    conn = _get_conn()
    try:
        # candidates 먼저
        r = conn.execute(
            "SELECT * FROM candidates WHERE candidate_id = ?", (item_id,)
        ).fetchone()
        if r:
            detail = dict(r)
            return ok(data={"type": "candidate", "detail": detail})

        # client_inquiries
        r = conn.execute(
            "SELECT * FROM client_inquiries WHERE id = ?", (item_id,)
        ).fetchone()
        if r:
            detail = dict(r)
            return ok(data={"type": "inquiry", "detail": detail})

        raise HTTPException(404, "Item not found")

    except HTTPException:
        raise
    except Exception as e:
        _log.error("inbox detail error: %s", e)
        raise HTTPException(500, "상세 정보를 불러올 수 없습니다.")
    finally:
        conn.close()


# ── PATCH /api/admin/inbox/{id}/notes — 메모 저장 ────────────────────────────
class NotesUpdate(BaseModel):
    notes: str = Field("", max_length=5000)


@router.patch("/inbox/{item_id}/notes")
async def admin_inbox_update_notes(item_id: str, body: NotesUpdate, request: Request):
    """수신함 항목 메모 저장."""
    _check_admin(request)

    now_iso = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    try:
        cur = conn.execute(
            "UPDATE candidates SET notes = ?, last_activity = ? WHERE candidate_id = ?",
            (body.notes, now_iso, item_id),
        )
        if cur.rowcount > 0:
            conn.commit()
            return ok(message="메모 저장 완료")

        cur = conn.execute(
            "UPDATE client_inquiries SET notes = ?, last_activity = ? WHERE id = ?",
            (body.notes, now_iso, item_id),
        )
        if cur.rowcount > 0:
            conn.commit()
            return ok(message="메모 저장 완료")

        raise HTTPException(404, "Item not found")

    except HTTPException:
        raise
    except Exception as e:
        _log.error("notes update error: %s", e)
        raise HTTPException(500, "메모 저장 실패")
    finally:
        conn.close()


# ── PATCH /api/admin/inbox/{id}/assign — 담당자 배정 ─────────────────────────
class AssignUpdate(BaseModel):
    assigned_to: str = Field("", max_length=100)


@router.patch("/inbox/{item_id}/assign")
async def admin_inbox_assign(item_id: str, body: AssignUpdate, request: Request):
    """수신함 항목 담당자 배정."""
    _check_admin(request)

    now_iso = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    try:
        cur = conn.execute(
            "UPDATE candidates SET assigned_to = ?, last_activity = ? WHERE candidate_id = ?",
            (body.assigned_to, now_iso, item_id),
        )
        if cur.rowcount > 0:
            conn.commit()
            return ok(message=f"담당자 배정: {body.assigned_to}")

        cur = conn.execute(
            "UPDATE client_inquiries SET assigned_to = ?, last_activity = ? WHERE id = ?",
            (body.assigned_to, now_iso, item_id),
        )
        if cur.rowcount > 0:
            conn.commit()
            return ok(message=f"담당자 배정: {body.assigned_to}")

        raise HTTPException(404, "Item not found")

    except HTTPException:
        raise
    except Exception as e:
        _log.error("assign update error: %s", e)
        raise HTTPException(500, "담당자 배정 실패")
    finally:
        conn.close()


# ── POST /api/admin/inbox/bulk ────────────────────────────────────────────────
@router.post("/inbox/bulk")
async def admin_inbox_bulk(body: BulkAction, request: Request):
    """일괄 상태 변경 / 담당자 배정."""
    _check_admin(request)

    if not _rate_ok(_get_ip_hash(request)):
        raise HTTPException(429, "요청이 너무 많습니다. 잠시 후 다시 시도해주세요.")

    if body.action not in ("mark_status", "assign"):
        raise HTTPException(400, "Invalid action. Valid: mark_status, assign")

    if body.action == "mark_status" and body.value not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status: {body.value}")

    if len(body.ids) > 100:
        raise HTTPException(400, "최대 100건까지 일괄 처리 가능합니다.")

    now_iso = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    updated = 0
    try:
        for item_id in body.ids:
            safe_id = str(item_id).strip()
            if not safe_id:
                continue

            if body.action == "mark_status":
                # candidates
                cur = conn.execute(
                    """UPDATE candidates SET inbox_status = ?, last_activity = ?
                       WHERE candidate_id = ?""",
                    (body.value, now_iso, safe_id),
                )
                if cur.rowcount > 0:
                    updated += 1
                    continue
                # client_inquiries
                cur = conn.execute(
                    """UPDATE client_inquiries SET inbox_status = ?, last_activity = ?
                       WHERE id = ?""",
                    (body.value, now_iso, safe_id),
                )
                if cur.rowcount > 0:
                    updated += 1

            elif body.action == "assign":
                cur = conn.execute(
                    """UPDATE candidates SET assigned_to = ?, last_activity = ?
                       WHERE candidate_id = ?""",
                    (body.value, now_iso, safe_id),
                )
                if cur.rowcount > 0:
                    updated += 1
                    continue
                cur = conn.execute(
                    """UPDATE client_inquiries SET assigned_to = ?, last_activity = ?
                       WHERE id = ?""",
                    (body.value, now_iso, safe_id),
                )
                if cur.rowcount > 0:
                    updated += 1

        conn.commit()
        _stats_cache["ts"] = 0
        return ok(data={"updated": updated}, message=f"{updated} items updated")

    except HTTPException:
        raise
    except Exception as e:
        _log.error("bulk action error: %s", e)
        raise HTTPException(500, "일괄 처리 실패")
    finally:
        conn.close()


# ── GET /api/admin/stats ──────────────────────────────────────────────────────
@router.get("/stats")
async def admin_stats(request: Request):
    """전체 통계 (60초 TTL 캐시)."""
    _check_admin(request)

    now = _time.time()
    if _stats_cache["data"] and (now - _stats_cache["ts"]) < _STATS_TTL:
        return ok(data=_stats_cache["data"])

    conn = _get_conn()
    try:
        stats: dict = {}
        utc_now = datetime.now(timezone.utc)

        # 총 지원자
        r = conn.execute(
            "SELECT COUNT(*) AS n FROM candidates WHERE (is_deleted IS NULL OR is_deleted=0)"
        ).fetchone()
        stats["total_candidates"] = r["n"]

        # 최근 7일 신규
        week_ago = (utc_now - timedelta(days=7)).strftime("%Y-%m-%d")
        r = conn.execute(
            "SELECT COUNT(*) AS n FROM candidates WHERE (is_deleted IS NULL OR is_deleted=0) AND created_at >= ?",
            (week_ago,),
        ).fetchone()
        stats["new_candidates"] = r["n"]

        # 이번달
        month_start = utc_now.strftime("%Y-%m-01")
        r = conn.execute(
            "SELECT COUNT(*) AS n FROM candidates WHERE (is_deleted IS NULL OR is_deleted=0) AND created_at >= ?",
            (month_start,),
        ).fetchone()
        stats["this_month_candidates"] = r["n"]

        # 지난달
        first_of_month = utc_now.replace(day=1)
        last_month_end = first_of_month.strftime("%Y-%m-01")
        last_month_start = (first_of_month - timedelta(days=1)).replace(day=1).strftime("%Y-%m-01")
        r = conn.execute(
            "SELECT COUNT(*) AS n FROM candidates WHERE (is_deleted IS NULL OR is_deleted=0) AND created_at >= ? AND created_at < ?",
            (last_month_start, last_month_end),
        ).fetchone()
        stats["last_month_candidates"] = r["n"]

        # 총 구인 문의
        r = conn.execute(
            "SELECT COUNT(*) AS n FROM client_inquiries WHERE (is_deleted IS NULL OR is_deleted=0)"
        ).fetchone()
        stats["total_inquiries"] = r["n"]

        # 이번달 구인 문의
        r = conn.execute(
            "SELECT COUNT(*) AS n FROM client_inquiries WHERE (is_deleted IS NULL OR is_deleted=0) AND submitted_at >= ?",
            (month_start,),
        ).fetchone()
        stats["this_month_inquiries"] = r["n"]

        # 활성 구인
        try:
            r = conn.execute(
                "SELECT COUNT(*) AS n FROM jobs WHERE status='open'"
            ).fetchone()
            stats["active_jobs"] = r["n"] if r else 0
        except Exception:
            stats["active_jobs"] = 0

        # 커뮤니티 게시글
        try:
            r = conn.execute(
                "SELECT COUNT(*) AS n FROM community_posts WHERE is_deleted=0"
            ).fetchone()
            stats["community_posts"] = r["n"] if r else 0
        except Exception:
            stats["community_posts"] = 0

        # 채널별 (by_source)
        by_source = {}
        for row in conn.execute(
            """SELECT COALESCE(source, 'unknown') AS src, COUNT(*) AS cnt
               FROM candidates WHERE (is_deleted IS NULL OR is_deleted=0)
               GROUP BY src ORDER BY cnt DESC"""
        ).fetchall():
            if row["cnt"] > 0:
                by_source[row["src"]] = row["cnt"]
        stats["by_source"] = by_source

        # 상태별 (by_status)
        by_status = {}
        for row in conn.execute(
            """SELECT COALESCE(status, 'Unknown') AS st, COUNT(*) AS cnt
               FROM candidates WHERE (is_deleted IS NULL OR is_deleted=0)
               GROUP BY st ORDER BY cnt DESC"""
        ).fetchall():
            if row["cnt"] > 0:
                by_status[row["st"]] = row["cnt"]
        stats["by_status"] = by_status

        # 캐시 저장
        _stats_cache["data"] = stats
        _stats_cache["ts"] = _time.time()

        return ok(data=stats)

    except HTTPException:
        raise
    except Exception as e:
        _log.error("stats error: %s", e, exc_info=True)
        raise HTTPException(500, "통계 데이터를 불러올 수 없습니다.")
    finally:
        conn.close()


# ── GET /api/admin/stats/monthly ──────────────────────────────────────────────
@router.get("/stats/monthly")
async def admin_stats_monthly(request: Request):
    """최근 6개월 월별 접수 추이."""
    _check_admin(request)

    conn = _get_conn()
    try:
        months: list[dict] = []
        utc_now = datetime.now(timezone.utc)

        for i in range(5, -1, -1):
            # 각 월의 시작 계산
            target = utc_now.replace(day=1)
            for _ in range(i):
                target = (target - timedelta(days=1)).replace(day=1)

            m_start = target.strftime("%Y-%m-01")
            if target.month == 12:
                m_end_dt = target.replace(year=target.year + 1, month=1)
            else:
                m_end_dt = target.replace(month=target.month + 1)
            m_end = m_end_dt.strftime("%Y-%m-01")

            r = conn.execute(
                """SELECT COUNT(*) AS n FROM candidates
                   WHERE (is_deleted IS NULL OR is_deleted=0)
                     AND created_at >= ? AND created_at < ?""",
                (m_start, m_end),
            ).fetchone()

            months.append({
                "month": target.strftime("%Y-%m"),
                "label": target.strftime("%m월"),
                "count": r["n"] if r else 0,
            })

        return ok(data=months)

    except Exception as e:
        _log.error("monthly stats error: %s", e)
        return ok(data=[])
    finally:
        conn.close()


# ── GET /api/admin/stats/by-source ────────────────────────────────────────────
SOURCE_LABELS = {
    "website": "웹사이트",
    "web_form": "웹폼",
    "google_form": "구글폼",
    "google_sheet": "구글시트",
    "email": "이메일",
    "manual": "수동입력",
    "import": "가져오기",
}


@router.get("/stats/by-source")
async def admin_stats_by_source(request: Request):
    """채널별 접수 현황."""
    _check_admin(request)

    conn = _get_conn()
    try:
        sources: list[dict] = []

        rows = conn.execute(
            """SELECT COALESCE(source, 'unknown') AS src, COUNT(*) AS cnt
               FROM candidates WHERE (is_deleted IS NULL OR is_deleted=0)
               GROUP BY src ORDER BY cnt DESC"""
        ).fetchall()

        for r in rows:
            if r["cnt"] > 0:
                sources.append({
                    "source": r["src"],
                    "label": SOURCE_LABELS.get(r["src"], r["src"]),
                    "count": r["cnt"],
                })

        # inquiries 합산
        r = conn.execute(
            "SELECT COUNT(*) AS n FROM client_inquiries WHERE (is_deleted IS NULL OR is_deleted=0)"
        ).fetchone()
        if r and r["n"] > 0:
            sources.append({
                "source": "inquiry",
                "label": "구인문의",
                "count": r["n"],
            })

        return ok(data=sources)

    except Exception as e:
        _log.error("by-source stats error: %s", e)
        return ok(data=[])
    finally:
        conn.close()
