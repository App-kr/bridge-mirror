"""
통합 수신함 API 모듈
- api_server.py에서 import하여 라우터 등록
- 기존 파일 수정 최소화: api_server.py에 2줄 추가만 필요
"""
import hashlib
import json
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


# ── 보안 헬퍼 ────────────────────────────────────────────────────────────────
_RATE_LIMIT: dict[str, list[float]] = {}


def _rate_ok(ip_hash: str, window: int = 300, max_posts: int = 30) -> bool:
    """5분 안에 최대 30건 (벌크 기준)."""
    now = _time.time()
    ts = _RATE_LIMIT.get(ip_hash, [])
    ts = [t for t in ts if now - t < window]
    if len(ts) >= max_posts:
        return False
    ts.append(now)
    _RATE_LIMIT[ip_hash] = ts
    return True


def _sanitize_search(raw: str) -> str:
    """Supabase .or_() 필터에 안전한 검색어로 변환.
    특수문자를 제거하여 필터 조작 방지."""
    # 알파벳, 숫자, 한글, 공백만 허용
    return re.sub(r"[^a-zA-Z0-9가-힣ㄱ-ㅎㅏ-ㅣ\s@.\-]", "", raw).strip()[:100]


def _validate_date(date_str: str) -> bool:
    """YYYY-MM-DD 형식 검증."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _get_ip_hash(request: Request) -> str:
    """클라이언트 IP 해시."""
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


# ── Supabase 클라이언트 (lazy import) ─────────────────────────────────────────
_svc_client = None


def _get_supabase():
    global _svc_client
    if _svc_client is None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SERVICE_KEY", "")
        if not url or not key:
            return None
        from supabase import create_client
        _svc_client = create_client(url, key)
    return _svc_client


# ── 응답 모델 ─────────────────────────────────────────────────────────────────
VALID_STATUSES = {"new", "reviewed", "contacted", "interview", "hired", "rejected"}
VALID_SOURCES = {"website", "google_form", "email", "inquiry"}


class StatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=20)


class NotesUpdate(BaseModel):
    notes: str = Field("", max_length=5000)


class AssignUpdate(BaseModel):
    assigned_to: str = Field("", max_length=50)


class BulkAction(BaseModel):
    ids: list[str] = Field(..., min_items=1, max_items=100)
    action: str = Field(...)  # "status" | "assign"
    value: str = Field(...)   # status value or assignee name


# ── GET /api/admin/inbox ──────────────────────────────────────────────────────
@router.get("/inbox")
async def admin_inbox(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    source: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort: str = "newest",
):
    """통합 수신함 - 페이지네이션 + 필터."""
    _check_admin(request)

    items: list[dict] = []
    total = 0

    # Supabase에서 candidates + client_inquiries 조회
    sb = _get_supabase()
    if sb:
        try:
            # candidates 조회
            cq = sb.table("candidates").select(
                "id,full_name,email,nationality,current_location,area_prefs,"
                "status,source,inbox_status,notes,assigned_to,created_at,updated_at,"
                "last_activity,gmail_message_id,parsed_data",
                count="exact"
            ).eq("is_deleted", False)

            if source and source != "all" and source != "inquiry":
                cq = cq.eq("source", source)
            if status and status != "all":
                cq = cq.eq("inbox_status", status)
            if search:
                safe_q = _sanitize_search(search)
                if safe_q:
                    cq = cq.or_(f"full_name.ilike.%{safe_q}%,email.ilike.%{safe_q}%,nationality.ilike.%{safe_q}%")
            if date_from:
                if not _validate_date(date_from):
                    raise HTTPException(400, "date_from 형식이 올바르지 않습니다 (YYYY-MM-DD)")
                cq = cq.gte("created_at", date_from)
            if date_to:
                if not _validate_date(date_to):
                    raise HTTPException(400, "date_to 형식이 올바르지 않습니다 (YYYY-MM-DD)")
                cq = cq.lte("created_at", date_to + "T23:59:59")

            if sort == "oldest":
                cq = cq.order("created_at", desc=False)
            else:
                cq = cq.order("created_at", desc=True)

            # inquiry 소스 필터일 때 candidates는 스킵
            if source != "inquiry":
                c_result = cq.range(0, 999).execute()
                for c in (c_result.data or []):
                    items.append({
                        "id": c["id"],
                        "type": "candidate",
                        "name": c.get("full_name") or "",
                        "email": c.get("email") or "",
                        "nationality": c.get("nationality") or "",
                        "location": c.get("current_location") or "",
                        "area_prefs": c.get("area_prefs") or "",
                        "source": c.get("source") or "website",
                        "inbox_status": c.get("inbox_status") or "new",
                        "notes": c.get("notes") or "",
                        "assigned_to": c.get("assigned_to") or "",
                        "created_at": c.get("created_at") or "",
                        "updated_at": c.get("updated_at") or "",
                        "last_activity": c.get("last_activity") or "",
                        "gmail_message_id": c.get("gmail_message_id") or "",
                        "parsed_data": c.get("parsed_data"),
                    })

            # client_inquiries 조회
            if source in (None, "all", "inquiry"):
                iq = sb.table("client_inquiries").select(
                    "id,school_name,email,contact_name,phone,location,status,"
                    "created_at,updated_at",
                    count="exact"
                )
                if search:
                    safe_q = _sanitize_search(search)
                    if safe_q:
                        iq = iq.or_(f"school_name.ilike.%{safe_q}%,contact_name.ilike.%{safe_q}%,email.ilike.%{safe_q}%")
                if date_from:
                    iq = iq.gte("created_at", date_from)
                if date_to:
                    iq = iq.lte("created_at", date_to + "T23:59:59")

                iq = iq.order("created_at", desc=(sort != "oldest"))
                i_result = iq.range(0, 999).execute()

                for i in (i_result.data or []):
                    items.append({
                        "id": i["id"],
                        "type": "inquiry",
                        "name": i.get("contact_name") or i.get("school_name") or "",
                        "email": i.get("email") or "",
                        "nationality": "",
                        "location": i.get("location") or "",
                        "area_prefs": "",
                        "source": "inquiry",
                        "inbox_status": _map_inquiry_status(i.get("status", "pending")),
                        "school_name": i.get("school_name") or "",
                        "notes": "",
                        "assigned_to": "",
                        "created_at": i.get("created_at") or "",
                        "updated_at": i.get("updated_at") or "",
                        "last_activity": "",
                    })

        except Exception as e:
            _log.error("inbox fetch error: %s", e, exc_info=True)
            raise HTTPException(500, "수신함 데이터를 불러올 수 없습니다.")

    # 정렬
    items.sort(key=lambda x: x.get("created_at", ""), reverse=(sort != "oldest"))
    total = len(items)

    # 페이지네이션
    start = (page - 1) * per_page
    end = start + per_page
    paged = items[start:end]

    return ok(data={
        "items": paged,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if per_page else 1,
    })


def _map_inquiry_status(st: str) -> str:
    """client_inquiries 상태를 inbox 상태로 매핑."""
    mapping = {
        "pending": "new",
        "matched": "contacted",
        "filled": "hired",
        "cancelled": "rejected",
    }
    return mapping.get(st, "new")


# ── GET /api/admin/inbox/{id} ─────────────────────────────────────────────────
@router.get("/inbox/{item_id}")
async def admin_inbox_detail(item_id: str, request: Request):
    """수신함 상세 - 지원자/문의 상세 정보."""
    _check_admin(request)

    sb = _get_supabase()
    if not sb:
        raise HTTPException(500, "Supabase not configured")

    # candidates에서 먼저 조회
    try:
        result = sb.table("candidates").select("*").eq("id", item_id).eq("is_deleted", False).execute()
        if result.data and len(result.data) > 0:
            item = result.data[0]
            return ok(data={
                "type": "candidate",
                "detail": item,
            })
    except Exception:
        pass

    # client_inquiries에서 조회
    try:
        result = sb.table("client_inquiries").select("*").eq("id", item_id).execute()
        if result.data and len(result.data) > 0:
            item = result.data[0]
            return ok(data={
                "type": "inquiry",
                "detail": item,
            })
    except Exception:
        pass

    raise HTTPException(404, "Item not found")


# ── PATCH /api/admin/inbox/{id}/status ────────────────────────────────────────
@router.patch("/inbox/{item_id}/status")
async def admin_inbox_update_status(item_id: str, body: StatusUpdate, request: Request):
    """수신함 상태 변경."""
    _check_admin(request)

    if body.status not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status. Valid: {', '.join(VALID_STATUSES)}")

    sb = _get_supabase()
    if not sb:
        raise HTTPException(500, "Supabase not configured")

    now_iso = datetime.now(timezone.utc).isoformat()

    # candidates 먼저 시도
    try:
        result = sb.table("candidates").select("id").eq("id", item_id).execute()
        if result.data and len(result.data) > 0:
            sb.table("candidates").update({
                "inbox_status": body.status,
                "last_activity": now_iso,
                "updated_at": now_iso,
            }).eq("id", item_id).execute()
            return ok(message=f"Status updated to {body.status}")
    except HTTPException:
        raise
    except Exception as e:
        _log.error("inbox status update error: %s", e)

    # client_inquiries
    try:
        result = sb.table("client_inquiries").select("id").eq("id", item_id).execute()
        if result.data and len(result.data) > 0:
            sb.table("client_inquiries").update({
                "status": _reverse_map_status(body.status),
                "updated_at": now_iso,
            }).eq("id", item_id).execute()
            return ok(message=f"Status updated to {body.status}")
    except HTTPException:
        raise
    except Exception as e:
        _log.error("inquiry status update error: %s", e)

    raise HTTPException(404, "Item not found")


def _reverse_map_status(inbox_status: str) -> str:
    """inbox 상태를 client_inquiries 상태로 역매핑."""
    mapping = {
        "new": "pending",
        "reviewed": "pending",
        "contacted": "matched",
        "interview": "matched",
        "hired": "filled",
        "rejected": "cancelled",
    }
    return mapping.get(inbox_status, "pending")


# ── PATCH /api/admin/inbox/{id}/notes ─────────────────────────────────────────
@router.patch("/inbox/{item_id}/notes")
async def admin_inbox_update_notes(item_id: str, body: NotesUpdate, request: Request):
    """관리자 메모 수정."""
    _check_admin(request)

    sb = _get_supabase()
    if not sb:
        raise HTTPException(500, "Supabase not configured")

    now_iso = datetime.now(timezone.utc).isoformat()

    # candidates 먼저
    try:
        result = sb.table("candidates").select("id").eq("id", item_id).execute()
        if result.data and len(result.data) > 0:
            sb.table("candidates").update({
                "notes": body.notes,
                "last_activity": now_iso,
            }).eq("id", item_id).execute()
            return ok(message="Notes updated")
    except Exception as e:
        _log.error("notes update error: %s", e)

    raise HTTPException(404, "Item not found")


# ── PATCH /api/admin/inbox/{id}/assign ────────────────────────────────────────
@router.patch("/inbox/{item_id}/assign")
async def admin_inbox_assign(item_id: str, body: AssignUpdate, request: Request):
    """담당자 배정."""
    _check_admin(request)

    sb = _get_supabase()
    if not sb:
        raise HTTPException(500, "Supabase not configured")

    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        result = sb.table("candidates").select("id").eq("id", item_id).execute()
        if result.data and len(result.data) > 0:
            sb.table("candidates").update({
                "assigned_to": body.assigned_to,
                "last_activity": now_iso,
            }).eq("id", item_id).execute()
            return ok(message=f"Assigned to {body.assigned_to}")
    except Exception as e:
        _log.error("assign error: %s", e)

    raise HTTPException(404, "Item not found")


# ── POST /api/admin/inbox/bulk ────────────────────────────────────────────────
@router.post("/inbox/bulk")
async def admin_inbox_bulk(body: BulkAction, request: Request):
    """일괄 상태 변경 / 담당자 배정."""
    _check_admin(request)

    if not _rate_ok(_get_ip_hash(request)):
        raise HTTPException(429, "요청이 너무 많습니다. 잠시 후 다시 시도해주세요.")

    if body.action not in ("status", "assign"):
        raise HTTPException(400, "Invalid action. Valid: status, assign")

    if body.action == "status" and body.value not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status: {body.value}")

    sb = _get_supabase()
    if not sb:
        raise HTTPException(500, "Supabase not configured")

    now_iso = datetime.now(timezone.utc).isoformat()
    updated = 0

    for item_id in body.ids:
        try:
            if body.action == "status":
                sb.table("candidates").update({
                    "inbox_status": body.value,
                    "last_activity": now_iso,
                }).eq("id", item_id).execute()
            elif body.action == "assign":
                sb.table("candidates").update({
                    "assigned_to": body.value,
                    "last_activity": now_iso,
                }).eq("id", item_id).execute()
            updated += 1
        except Exception as e:
            _log.warning("bulk action failed for %s: %s", item_id, e)

    return ok(data={"updated": updated}, message=f"{updated} items updated")


# ── GET /api/admin/stats ──────────────────────────────────────────────────────
@router.get("/stats")
async def admin_stats(request: Request):
    """전체 통계: 총 지원수, 신규, 채널별, 상태별."""
    _check_admin(request)

    stats: dict = {}
    sb = _get_supabase()

    if sb:
        try:
            # 총 지원자
            all_c = sb.table("candidates").select("id", count="exact").eq("is_deleted", False).execute()
            stats["total_candidates"] = all_c.count if all_c.count is not None else len(all_c.data or [])

            # 신규 (inbox_status = 'new')
            new_c = sb.table("candidates").select("id", count="exact").eq(
                "is_deleted", False
            ).eq("inbox_status", "new").execute()
            stats["new_candidates"] = new_c.count if new_c.count is not None else len(new_c.data or [])

            # 이번달 지원자
            now = datetime.now(timezone.utc)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
            this_month = sb.table("candidates").select("id", count="exact").eq(
                "is_deleted", False
            ).gte("created_at", month_start).execute()
            stats["this_month_candidates"] = this_month.count if this_month.count is not None else len(this_month.data or [])

            # 지난달 지원자
            last_month_end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_month_start = (last_month_end - timedelta(days=1)).replace(day=1).isoformat()
            last_month = sb.table("candidates").select("id", count="exact").eq(
                "is_deleted", False
            ).gte("created_at", last_month_start).lt("created_at", month_start).execute()
            stats["last_month_candidates"] = last_month.count if last_month.count is not None else len(last_month.data or [])

            # 채널별
            sources = {}
            for src in ["website", "google_form", "email", "manual", "import", "web_form", "google_sheet"]:
                src_q = sb.table("candidates").select("id", count="exact").eq(
                    "is_deleted", False
                ).eq("source", src).execute()
                cnt = src_q.count if src_q.count is not None else len(src_q.data or [])
                if cnt > 0:
                    sources[src] = cnt
            stats["by_source"] = sources

            # 상태별
            statuses = {}
            for st in ["new", "reviewed", "contacted", "interview", "hired", "rejected"]:
                st_q = sb.table("candidates").select("id", count="exact").eq(
                    "is_deleted", False
                ).eq("inbox_status", st).execute()
                cnt = st_q.count if st_q.count is not None else len(st_q.data or [])
                if cnt > 0:
                    statuses[st] = cnt
            stats["by_status"] = statuses

            # 구인 문의
            inquiries = sb.table("client_inquiries").select("id", count="exact").execute()
            stats["total_inquiries"] = inquiries.count if inquiries.count is not None else len(inquiries.data or [])

            # 이번달 구인 문의
            inq_month = sb.table("client_inquiries").select("id", count="exact").gte(
                "created_at", month_start
            ).execute()
            stats["this_month_inquiries"] = inq_month.count if inq_month.count is not None else len(inq_month.data or [])

            # 활성 구인 (open 상태 jobs)
            try:
                jobs = sb.table("jobs").select("id", count="exact").eq("status", "open").execute()
                stats["active_jobs"] = jobs.count if jobs.count is not None else len(jobs.data or [])
            except Exception:
                stats["active_jobs"] = 0

        except HTTPException:
            raise
        except Exception as e:
            _log.error("stats error: %s", e, exc_info=True)
            raise HTTPException(500, "통계 데이터를 불러올 수 없습니다.")

    # SQLite 통계
    if _ADMIN_DB_PATH.exists():
        conn = _get_conn()
        try:
            r = conn.execute("SELECT COUNT(*) FROM community_posts WHERE is_deleted=0").fetchone()
            stats["community_posts"] = r[0] if r else 0
        except Exception:
            stats["community_posts"] = 0
        finally:
            conn.close()

    return ok(data=stats)


# ── GET /api/admin/stats/monthly ──────────────────────────────────────────────
@router.get("/stats/monthly")
async def admin_stats_monthly(request: Request):
    """최근 6개월 월별 접수 추이."""
    _check_admin(request)

    sb = _get_supabase()
    if not sb:
        return ok(data=[])

    months: list[dict] = []
    now = datetime.now(timezone.utc)

    try:
        for i in range(5, -1, -1):
            # 각 월의 시작/끝 계산
            d = now.replace(day=1) - timedelta(days=i * 30)
            m_start = d.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if m_start.month == 12:
                m_end = m_start.replace(year=m_start.year + 1, month=1)
            else:
                m_end = m_start.replace(month=m_start.month + 1)

            result = sb.table("candidates").select("id", count="exact").eq(
                "is_deleted", False
            ).gte("created_at", m_start.isoformat()).lt("created_at", m_end.isoformat()).execute()

            cnt = result.count if result.count is not None else len(result.data or [])
            months.append({
                "month": m_start.strftime("%Y-%m"),
                "label": m_start.strftime("%m월"),
                "count": cnt,
            })
    except Exception as e:
        _log.error("monthly stats error: %s", e)

    return ok(data=months)


# ── GET /api/admin/stats/by-source ────────────────────────────────────────────
@router.get("/stats/by-source")
async def admin_stats_by_source(request: Request):
    """채널별 접수 현황."""
    _check_admin(request)

    sb = _get_supabase()
    if not sb:
        return ok(data=[])

    sources: list[dict] = []
    source_labels = {
        "website": "웹사이트",
        "web_form": "웹폼",
        "google_form": "구글폼",
        "google_sheet": "구글시트",
        "email": "이메일",
        "manual": "수동입력",
        "import": "가져오기",
    }

    try:
        for src, label in source_labels.items():
            result = sb.table("candidates").select("id", count="exact").eq(
                "is_deleted", False
            ).eq("source", src).execute()
            cnt = result.count if result.count is not None else len(result.data or [])
            if cnt > 0:
                sources.append({"source": src, "label": label, "count": cnt})

        # inquiries
        inq = sb.table("client_inquiries").select("id", count="exact").execute()
        cnt = inq.count if inq.count is not None else len(inq.data or [])
        if cnt > 0:
            sources.append({"source": "inquiry", "label": "구인문의", "count": cnt})

    except Exception as e:
        _log.error("by-source stats error: %s", e)

    return ok(data=sources)
