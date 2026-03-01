"""
BRIDGE Admin Dashboard
======================
master.db (SQLite) 기반 완전한 CRUD 관리 패널.
이전 Excel 방식 전면 대체.

실행:
  streamlit run "Q:/Claudework/bridge base/admin_dashboard.py" --server.port 8501

탭:
  [1] 구직자 관리   — 검색/필터/상태변경/상세보기/CSV 내보내기
  [2] 구인 포지션   — 검색/필터/HOT 토글/상태관리
  [3] 구인처 문의   — 학교 문의 열람 및 상태 처리
  [4] Supabase 이관 — 드라이런·실제 이관·뷰 SQL 검토
  [5] 시스템        — DB 통계·사진 업로드·로그
"""
from __future__ import annotations

import hmac
import io
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

# ── 경로 ─────────────────────────────────────────────────────────────────────
BASE_DIR   = Path("Q:/Claudework/bridge base")
DB_PATH    = BASE_DIR / "master.db"
PHOTO_DIR  = BASE_DIR / "original_candidates" / "photos"
LOG_PATH   = BASE_DIR / "logs" / "system.log"
VIEWS_SQL  = BASE_DIR / "supabase_public_views.sql"
MIGRATOR   = BASE_DIR / "supabase_migrator.py"
PLAN_JSON  = BASE_DIR / "migration_plan.json"

PHOTO_DIR.mkdir(parents=True, exist_ok=True)

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

# ── 페이지 설정 ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BRIDGE Admin",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
.stApp { background:#0b0f1a; color:#dde6f5; }
.stTabs [data-baseweb="tab-list"] { background:#111827; border-radius:8px; gap:4px; padding:4px; }
.stTabs [data-baseweb="tab"]      { color:#6b8ab8; border-radius:6px; padding:6px 16px; }
.stTabs [aria-selected="true"]    { background:#1e3a5f !important; color:#5b9cf6 !important; }
div[data-testid="metric-container"] { background:#111827; border:1px solid #1e3a5f;
    border-radius:8px; padding:12px 18px; }
.stDataFrame { border:1px solid #1e3a5f !important; border-radius:8px; }
.block-container { padding-top:1.2rem; }
</style>
""", unsafe_allow_html=True)


# ── 인증 ─────────────────────────────────────────────────────────────────────
def authenticate() -> bool:
    admin_pwd = os.environ.get("ADMIN_PASSWORD", "bridge2026").strip()
    if st.session_state.get("auth_ok"):
        return True
    st.markdown("""
    <div style='text-align:center;padding:60px 0 20px'>
      <div style='font-size:36px;font-weight:800;color:#5b9cf6;letter-spacing:4px;'>
        🔐 BRIDGE ADMIN
      </div>
      <div style='color:#4a6a9a;margin-top:8px;font-size:13px;'>
        RESTRICTED ACCESS — AUTHORISED PERSONNEL ONLY
      </div>
    </div>""", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1, 1])
    with col:
        pwd = st.text_input("SYSTEM KEY", type="password", label_visibility="collapsed",
                            placeholder="Enter access key…")
        if pwd:
            if hmac.compare_digest(pwd.strip().encode("utf-8"), admin_pwd.encode("utf-8")):
                st.session_state["auth_ok"] = True
                st.rerun()
            else:
                st.error("ACCESS DENIED")
    return False


# ── DB 헬퍼 ───────────────────────────────────────────────────────────────────
@st.cache_resource
def get_conn():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def run_query(sql: str, params: tuple = ()) -> pd.DataFrame:
    conn = get_conn()
    try:
        return pd.read_sql_query(sql, conn, params=params)
    except Exception as e:
        st.error(f"DB 오류: {e}")
        return pd.DataFrame()


def execute(sql: str, params: tuple = ()):
    conn = get_conn()
    conn.execute(sql, params)
    conn.commit()


def table_exists(name: str) -> bool:
    conn = get_conn()
    r = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return r is not None


# ── KPI 행 ────────────────────────────────────────────────────────────────────
def show_kpis():
    cols = st.columns(5)
    metrics = []

    if table_exists("candidates"):
        total = run_query("SELECT COUNT(*) n FROM candidates").iloc[0, 0]
        active = run_query("SELECT COUNT(*) n FROM candidates WHERE status='Active'").iloc[0, 0]
        metrics += [("구직자 전체", f"{total:,}"), ("Active", f"{active:,}")]
    else:
        metrics += [("구직자", "—"), ("Active", "—")]

    if table_exists("jobs"):
        jobs_n = run_query("SELECT COUNT(*) n FROM jobs").iloc[0, 0]
        hot_n  = run_query(
            "SELECT COUNT(*) n FROM jobs WHERE daily_hours < 7.0 OR is_hot=1"
        ).iloc[0, 0] if "is_hot" in run_query(
            "PRAGMA table_info(jobs)"
        )["name"].tolist() else run_query(
            "SELECT COUNT(*) n FROM jobs WHERE daily_hours < 7.0"
        ).iloc[0, 0]
        metrics += [("포지션", f"{jobs_n:,}"), ("HOT", f"{hot_n:,}")]
    else:
        metrics += [("포지션", "—"), ("HOT", "—")]

    if table_exists("client_inquiries"):
        ci = run_query("SELECT COUNT(*) n FROM client_inquiries").iloc[0, 0]
        metrics.append(("구인처 문의", f"{ci:,}"))
    else:
        metrics.append(("구인처 문의", "—"))

    for col, (label, val) in zip(cols, metrics):
        col.metric(label, val)


# ════════════════════════════════════════════════════════════
#  TAB 1 — 구직자 관리
# ════════════════════════════════════════════════════════════
def tab_candidates():
    st.subheader("구직자 관리")

    if not table_exists("candidates"):
        st.warning("candidates 테이블이 없습니다. `build_candidates_db.py`를 먼저 실행하세요.")
        return

    # ── 필터 행 ─────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
    search = c1.text_input("🔍 이름·이메일·국적 검색", placeholder="검색어…", label_visibility="collapsed")
    status_filter = c2.selectbox("상태", ["ALL", "Active", "Inactive", "Placed", "Blacklist"],
                                 label_visibility="collapsed")
    nat_filter = c3.text_input("국적 필터", placeholder="예: 미국, 캐나다", label_visibility="collapsed")
    limit = c4.number_input("최대 행수", 50, 2000, 200, step=50, label_visibility="collapsed", key="cand_limit")

    # ── SQL 구성 ─────────────────────────────────────────────
    conditions = []
    params: list = []

    if search:
        conditions.append("(full_name LIKE ? OR email LIKE ? OR nationality LIKE ?)")
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    if status_filter != "ALL":
        conditions.append("status = ?"); params.append(status_filter)
    if nat_filter:
        conditions.append("nationality LIKE ?"); params.append(f"%{nat_filter}%")

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    df = run_query(f"""
        SELECT candidate_id, full_name, email, nationality, dob,
               current_location, start_date, desired_salary, e_visa,
               mobile_phone, status, source_file
        FROM candidates {where}
        ORDER BY created_at DESC
        LIMIT {int(limit)}
    """, tuple(params))

    st.caption(f"조회: {len(df):,}건")

    # ── 데이터 테이블 ────────────────────────────────────────
    if df.empty:
        st.info("조건에 맞는 구직자가 없습니다.")
        return

    selected_rows = st.dataframe(
        df,
        use_container_width=True,
        height=400,
        on_select="rerun",
        selection_mode="single-row",
    )

    # ── 단일 선택 시 상세 패널 ───────────────────────────────
    sel_idx = (selected_rows.selection.rows or [None])[0]
    if sel_idx is not None:
        cid = df.iloc[sel_idx]["candidate_id"]
        _candidate_detail(cid)

    # ── 일괄 상태 변경 ───────────────────────────────────────
    st.divider()
    with st.expander("⚙️ 일괄 상태 변경"):
        ids_input = st.text_area("candidate_id 목록 (한 줄에 하나)", height=80)
        new_status = st.selectbox("변경할 상태", ["Active", "Inactive", "Placed", "Blacklist"])
        if st.button("적용", type="primary"):
            ids = [x.strip() for x in ids_input.splitlines() if x.strip()]
            if ids:
                for cid in ids:
                    execute("UPDATE candidates SET status=?, updated_at=? WHERE candidate_id=?",
                            (new_status, datetime.now(timezone.utc).isoformat(), cid))
                st.success(f"{len(ids)}건 → {new_status}")
                st.cache_data.clear()
                st.rerun()

    # ── CSV 내보내기 ─────────────────────────────────────────
    st.divider()
    col_export, _ = st.columns([2, 6])
    csv = df.to_csv(index=False).encode("utf-8-sig")
    col_export.download_button(
        "📥 CSV 내보내기",
        data=csv,
        file_name=f"candidates_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )


def _candidate_detail(cid: str):
    """선택한 구직자 전체 레코드 상세 패널."""
    row = run_query("SELECT * FROM candidates WHERE candidate_id=?", (cid,))
    if row.empty:
        return
    r = row.iloc[0]

    with st.expander(f"📋 상세 프로필 — {r.get('full_name','?')}  ({cid})", expanded=True):
        col1, col2, col3 = st.columns(3)

        # 기본 정보
        with col1:
            st.markdown("**기본 정보**")
            st.write(f"이름: `{r.get('full_name','')}`")
            st.write(f"이메일: `{r.get('email','')}`")
            st.write(f"국적: {r.get('nationality','')} / 혈통: {r.get('ancestry','')}")
            st.write(f"생년: {r.get('dob','')} / 성별: {r.get('gender','')}")
            st.write(f"현재 위치: {r.get('current_location','')}")

        # 연락처 (PII — 어드민만 열람)
        with col2:
            st.markdown("**연락처 (관리자 전용)**")
            st.code(r.get("mobile_phone", "—"))
            st.code(r.get("kakaotalk", "—"))
            st.write(f"비자: {r.get('e_visa','')} / ARC: {r.get('arc_holders','')}")
            st.write(f"여권: {r.get('passport','')}")
            st.write(f"범죄기록: {r.get('criminal_record','')}")

        # 경력/급여
        with col3:
            st.markdown("**경력 및 급여**")
            st.write(f"경력: {r.get('experience','')}")
            st.write(f"고용형태: {r.get('employment','')}")
            st.write(f"현 급여: {r.get('current_salary','')} | 희망: {r.get('desired_salary','')}")
            st.write(f"자격증: {r.get('certification','')}")
            st.write(f"시작 가능: {r.get('start_date','')}")

        # 선호 / 서류
        st.markdown("**선호 조건**")
        st.write(
            f"지역: {r.get('area_prefs','')} | 연령대: {r.get('target','')} | "
            f"직종: {r.get('job_prefs','')} | 숙소: {r.get('housing','')}"
        )

        # 상태 변경
        new_st = st.selectbox("상태 변경", ["Active","Inactive","Placed","Blacklist"],
                               index=["Active","Inactive","Placed","Blacklist"].index(
                                   r.get("status","Active")
                               ), key=f"st_{cid}")
        if st.button("저장", key=f"save_{cid}"):
            execute("UPDATE candidates SET status=?, updated_at=? WHERE candidate_id=?",
                    (new_st, datetime.now(timezone.utc).isoformat(), cid))
            st.success(f"상태 변경: {new_st}")
            st.cache_data.clear()
            st.rerun()


# ════════════════════════════════════════════════════════════
#  TAB 2 — 구인 포지션
# ════════════════════════════════════════════════════════════
def tab_jobs():
    st.subheader("구인 포지션 관리")

    if not table_exists("jobs"):
        st.warning("jobs 테이블이 없습니다.")
        return

    # jobs 컬럼 확인
    cols_info = run_query("PRAGMA table_info(jobs)")
    col_names = cols_info["name"].tolist()
    has_is_hot  = "is_hot"   in col_names
    has_status  = "status"   in col_names
    has_loaded  = "loaded_at" in col_names

    # ── 필터 ────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
    city_f   = c1.text_input("도시 필터", placeholder="Seoul, Busan…", label_visibility="collapsed")
    hot_only = c2.checkbox("HOT만 (< 7h/day)")
    if has_status:
        st_f = c3.selectbox("상태", ["ALL","open","filled","hold","cancelled"],
                             label_visibility="collapsed")
    else:
        st_f = "ALL"
    limit = c4.number_input("최대 행수", 50, 2000, 200, step=50, label_visibility="collapsed", key="jobs_limit")

    # ── SQL ────────────────────────────────────────────────
    conditions = []
    params: list = []
    if city_f:
        conditions.append("city LIKE ?"); params.append(f"%{city_f}%")
    if hot_only:
        conditions.append("daily_hours < 7.0")
    if has_status and st_f != "ALL":
        conditions.append("status = ?"); params.append(st_f)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    select_cols = (
        "id, job_code, seq, city, district, teaching_age, "
        "daily_hours, salary_min, salary_max, salary_raw, housing, "
        "vacation, native_count, start_date"
    )
    if has_is_hot:  select_cols += ", is_hot"
    if has_status:  select_cols += ", status"
    if has_loaded:  select_cols += ", loaded_at"

    df = run_query(
        f"SELECT {select_cols} FROM jobs {where} ORDER BY daily_hours ASC LIMIT {int(limit)}",
        tuple(params)
    )

    st.caption(f"조회: {len(df):,}건 | HOT (< 7h): {(df['daily_hours'] < 7).sum() if 'daily_hours' in df.columns else '—'}건")

    if df.empty:
        st.info("조건에 맞는 포지션이 없습니다.")
        return

    sel = st.dataframe(
        df.style.apply(
            lambda row: ["background:#1a2a1a" if row.get("daily_hours", 99) < 7 else "" for _ in row],
            axis=1
        ) if "daily_hours" in df.columns else df,
        use_container_width=True,
        height=500,
        on_select="rerun",
        selection_mode="single-row",
    )

    # ── 상세 편집 ────────────────────────────────────────────
    sel_idx = (sel.selection.rows or [None])[0]
    if sel_idx is not None:
        row   = df.iloc[sel_idx]
        jid   = int(row["id"])

        with st.expander(f"✏️ 포지션 편집 — Job {row.get('job_code','?')} / {row.get('city','?')}", expanded=True):
            ec1, ec2 = st.columns(2)
            with ec1:
                st.write(f"**일일 시간**: {row.get('daily_hours','—')}h")
                st.write(f"**급여**: {row.get('salary_raw','—')}")
                st.write(f"**대상 연령**: {row.get('teaching_age','—')}")
                st.write(f"**숙소**: {row.get('housing','—')}")
                st.write(f"**시작일**: {row.get('start_date','—')}")
            with ec2:
                if has_status:
                    new_status = st.selectbox("상태", ["open","filled","hold","cancelled"],
                                               index=["open","filled","hold","cancelled"].index(
                                                   str(row.get("status","open"))
                                               ), key=f"jst_{jid}")
                if has_is_hot:
                    new_hot = st.checkbox("HOT 포지션", value=bool(row.get("is_hot", False)),
                                           key=f"hot_{jid}")

            if st.button("저장", key=f"jsave_{jid}", type="primary"):
                updates = []
                upd_params = []
                if has_status:
                    updates.append("status=?"); upd_params.append(new_status)
                if has_is_hot:
                    updates.append("is_hot=?"); upd_params.append(int(new_hot))
                if updates:
                    upd_params.append(jid)
                    execute(f"UPDATE jobs SET {', '.join(updates)} WHERE id=?",
                            tuple(upd_params))
                    st.success("저장 완료")
                    st.cache_data.clear()
                    st.rerun()

    # ── CSV 내보내기 ─────────────────────────────────────────
    st.divider()
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 CSV 내보내기",
        data=csv,
        file_name=f"jobs_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )


# ════════════════════════════════════════════════════════════
#  TAB 3 — 구인처 문의
# ════════════════════════════════════════════════════════════
def tab_inquiries():
    st.subheader("구인처 문의 (학교)")

    if not table_exists("client_inquiries"):
        st.warning("client_inquiries 테이블이 없습니다.")
        return

    ci_cols = run_query("PRAGMA table_info(client_inquiries)")["name"].tolist()
    has_status = "status" in ci_cols

    c1, c2 = st.columns([4, 2])
    search = c1.text_input("학교명 검색", label_visibility="collapsed", placeholder="학교명…")
    st_f   = c2.selectbox("상태", ["ALL","pending","matched","filled","cancelled"],
                           label_visibility="collapsed") if has_status else "ALL"

    conds, params = [], []
    if search:
        conds.append("school_name LIKE ?"); params.append(f"%{search}%")
    if has_status and st_f != "ALL":
        conds.append("status = ?"); params.append(st_f)

    where = "WHERE " + " AND ".join(conds) if conds else ""

    select_ci = (
        "id, school_name, location, contact_name, phone, email, "
        "start_date, vacancies, teaching_age, working_hours, salary_raw, "
        "housing_type, benefits, memo"
    )
    if has_status: select_ci += ", status"
    select_ci += ", loaded_at" if "loaded_at" in ci_cols else ""

    df = run_query(
        f"SELECT {select_ci} FROM client_inquiries {where} ORDER BY id DESC LIMIT 500",
        tuple(params)
    )

    st.caption(f"조회: {len(df):,}건")

    sel = st.dataframe(df, use_container_width=True, height=420,
                       on_select="rerun", selection_mode="single-row")

    # ── 상세 + 상태 변경 ─────────────────────────────────────
    sel_idx = (sel.selection.rows or [None])[0]
    if sel_idx is not None:
        row = df.iloc[sel_idx]
        iid = int(row["id"])

        with st.expander(f"📋 문의 상세 — {row.get('school_name','?')}", expanded=True):
            d1, d2 = st.columns(2)
            with d1:
                st.markdown("**학교 정보**")
                st.write(f"학교명: **{row.get('school_name','')}**")
                st.write(f"위치: {row.get('location','')}")
                st.write(f"담당자: {row.get('contact_name','')}")
                st.write(f"📞 {row.get('phone','')}  ✉ {row.get('email','')}")
            with d2:
                st.markdown("**채용 조건**")
                st.write(f"시작일: {row.get('start_date','')} | 인원: {row.get('vacancies','')}")
                st.write(f"대상: {row.get('teaching_age','')} | 일정: {row.get('working_hours','')}")
                st.write(f"급여: {row.get('salary_raw','')} | 숙소: {row.get('housing_type','')}")
                if row.get("memo"): st.info(f"메모: {row['memo']}")

            if has_status:
                new_st = st.selectbox("상태 변경", ["pending","matched","filled","cancelled"],
                                       index=["pending","matched","filled","cancelled"].index(
                                           str(row.get("status","pending"))
                                       ), key=f"cist_{iid}")
                if st.button("저장", key=f"cisave_{iid}", type="primary"):
                    execute("UPDATE client_inquiries SET status=? WHERE id=?", (new_st, iid))
                    st.success(f"상태 변경: {new_st}")
                    st.cache_data.clear()
                    st.rerun()


# ════════════════════════════════════════════════════════════
#  TAB 4 — Supabase 이관
# ════════════════════════════════════════════════════════════
def tab_migration():
    st.subheader("Supabase 이관 제어판")

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "")

    # ── 연결 상태 ────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        if supabase_url and "여기에" not in supabase_url:
            st.success(f"✅ SUPABASE_URL 설정됨\n`{supabase_url[:40]}…`")
        else:
            st.error("❌ SUPABASE_URL 미설정 — .env 확인")
    with col2:
        if supabase_key and "여기에" not in supabase_key:
            st.success("✅ SUPABASE_SERVICE_KEY 설정됨")
        else:
            st.error("❌ SUPABASE_SERVICE_KEY 미설정")

    st.divider()

    # ── 플랜 생성 & 미리보기 ────────────────────────────────
    st.markdown("#### 1단계 — 실행 계획 생성 (Dry-run)")
    if st.button("📋 Dry-run 실행", help="master.db 분석 후 migration_plan.json 생성. 업로드 안 함."):
        with st.spinner("분석 중…"):
            result = subprocess.run(
                [sys.executable, str(MIGRATOR), "--plan"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                cwd=str(BASE_DIR)
            )
        if result.returncode == 0:
            st.success("계획 생성 완료")
            st.text(result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)
        else:
            st.error(result.stderr[-2000:])

    if PLAN_JSON.exists():
        import json
        plan = json.loads(PLAN_JSON.read_text(encoding="utf-8"))
        with st.expander(f"📊 migration_plan.json 미리보기  ({PLAN_JSON.stat().st_mtime:.0f})", expanded=False):
            tables = plan.get("tables", {})
            cols = st.columns(len(tables))
            for col, (tname, tdata) in zip(cols, tables.items()):
                col.metric(tname, f"{tdata.get('count',0):,}건")
            st.json(plan.get("insights", {}))
            if plan.get("warnings"):
                for w in plan["warnings"]:
                    st.warning(w)

    st.divider()

    # ── DDL 보기 ─────────────────────────────────────────────
    st.markdown("#### 2단계 — Supabase SQL Editor에서 실행할 DDL")
    if st.button("📄 스키마 DDL 출력"):
        result = subprocess.run(
            [sys.executable, str(MIGRATOR), "--schema"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(BASE_DIR)
        )
        st.code(result.stdout, language="sql")

    if VIEWS_SQL.exists():
        with st.expander("🔐 Public Views SQL (supabase_public_views.sql)"):
            st.code(VIEWS_SQL.read_text(encoding="utf-8"), language="sql")

    st.divider()

    # ── 실제 이관 ────────────────────────────────────────────
    st.markdown("#### 3단계 — 실제 업로드")
    if not (supabase_url and supabase_key and
            "여기에" not in supabase_url and "여기에" not in supabase_key):
        st.warning("SUPABASE_URL / SUPABASE_SERVICE_KEY를 .env에 입력한 뒤 재실행하세요.")
    else:
        tbl = st.selectbox("이관할 테이블", ["all","candidates","jobs","employers"])
        st.warning("⚠️ 실제 Supabase에 업로드됩니다. Dry-run 완료 후 실행하세요.")
        if st.button("🚀 이관 실행", type="primary"):
            with st.spinner("Supabase 업로드 중…"):
                result = subprocess.run(
                    [sys.executable, str(MIGRATOR), "--table", tbl],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    cwd=str(BASE_DIR)
                )
            if result.returncode == 0:
                st.success("이관 완료")
                st.text(result.stdout[-3000:])
            else:
                st.error(result.stderr[-2000:])


# ════════════════════════════════════════════════════════════
#  TAB 5 — 시스템
# ════════════════════════════════════════════════════════════
def tab_system():
    st.subheader("시스템 현황")

    # ── DB 통계 ─────────────────────────────────────────────
    st.markdown("#### DB 통계")
    db_size = DB_PATH.stat().st_size / 1024 if DB_PATH.exists() else 0
    sm1, sm2, sm3 = st.columns(3)
    sm1.metric("DB 파일 크기", f"{db_size:,.0f} KB")
    sm2.metric("DB 경로", str(DB_PATH))
    sm3.metric("최종 수정", datetime.fromtimestamp(DB_PATH.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
               if DB_PATH.exists() else "—")

    if DB_PATH.exists():
        tables = run_query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tbl_data = []
        for tname in tables["name"].tolist():
            cnt = run_query(f"SELECT COUNT(*) n FROM [{tname}]").iloc[0, 0]
            tbl_data.append({"테이블": tname, "레코드 수": cnt})
        st.dataframe(pd.DataFrame(tbl_data), use_container_width=False, height=200)

    # ── 사진 업로드 ──────────────────────────────────────────
    st.divider()
    st.markdown("#### 구직자 사진 업로드")
    with st.form("photo_form", clear_on_submit=True):
        p1, p2 = st.columns([2, 2])
        uname = p1.text_input("구직자 이름 (저장 파일명)")
        ufile = p2.file_uploader("사진 (JPG / PNG)", type=["jpg","jpeg","png"])
        if st.form_submit_button("업로드"):
            if uname and ufile:
                safe = re.sub(r'[^a-zA-Z0-9가-힣_\-]', '', uname).strip()
                dest = PHOTO_DIR / f"{safe}.jpg"
                dest.write_bytes(ufile.getbuffer())
                st.success(f"저장 완료: {dest}")
            else:
                st.warning("이름과 파일을 모두 입력하세요.")

    existing = sorted(PHOTO_DIR.glob("*.jpg")) + sorted(PHOTO_DIR.glob("*.png"))
    if existing:
        st.caption(f"저장된 사진: {len(existing)}장")
        pcols = st.columns(8)
        for i, p in enumerate(existing[:16]):
            with pcols[i % 8]:
                try:
                    from PIL import Image
                    st.image(Image.open(p), caption=p.stem, use_container_width=True)
                except Exception:
                    st.text(p.stem)

    # ── 로그 ────────────────────────────────────────────────
    st.divider()
    st.markdown("#### 시스템 로그")
    if LOG_PATH.exists():
        lines = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
        st.code("\n".join(lines[-80:]), language="text")
    else:
        st.info("로그 파일 없음")

    # ── 캐시 초기화 ──────────────────────────────────────────
    st.divider()
    if st.button("🔄 캐시 초기화 (데이터 새로고침)"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("초기화 완료")
        st.rerun()


# ════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════
def main():
    if not authenticate():
        st.stop()

    # ── 헤더 ─────────────────────────────────────────────────
    st.markdown("""
    <div style='background:linear-gradient(135deg,#0d1b3e,#1a2f5e,#0d1b3e);
         border:1px solid #2a4080;border-radius:12px;
         padding:16px 28px;margin-bottom:20px;
         display:flex;justify-content:space-between;align-items:center;'>
      <div>
        <div style='font-size:22px;font-weight:800;color:#5b9cf6;letter-spacing:3px;'>
          🔐 BRIDGE ADMIN
        </div>
        <div style='color:#4a6a9a;font-size:12px;margin-top:4px;'>
          INTERNAL DATA MANAGEMENT — RESTRICTED
        </div>
      </div>
      <div style='color:#4ecdc4;font-family:monospace;font-size:14px;'>
        master.db  ·  4 tables
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI 행 ───────────────────────────────────────────────
    show_kpis()

    st.divider()

    # ── 탭 ───────────────────────────────────────────────────
    t1, t2, t3, t4, t5 = st.tabs([
        "👤 구직자",
        "💼 구인 포지션",
        "🏫 구인처 문의",
        "☁️ Supabase 이관",
        "⚙️ 시스템",
    ])

    with t1: tab_candidates()
    with t2: tab_jobs()
    with t3: tab_inquiries()
    with t4: tab_migration()
    with t5: tab_system()


if __name__ == "__main__":
    main()
