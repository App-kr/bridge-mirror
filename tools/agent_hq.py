"""
BRIDGE Agent HQ -- 에이전트 통제실
====================================
경로: Q:/Claudework/bridge base/
실행: streamlit run "Q:/Claudework/bridge base/agent_hq.py" --server.port 8502
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import streamlit as st

# ── 경로 (bridge base 기준) ───────────────────────────────────────────────────
BASE_DIR    = Path("Q:/Claudework/bridge base")
DB_PATH     = BASE_DIR / "master.db"
CAND_DB     = DB_PATH   # candidates 테이블이 bridge base master.db에 통합됨
LOG_PATH    = BASE_DIR / "logs/system.log"
INTAKE_CAND = BASE_DIR / "intake/candidates"
INTAKE_JOBS = BASE_DIR / "intake/jobs"
STATE_FILE  = BASE_DIR / "sheets_state.json"
SA_JSON     = BASE_DIR / "google_service_account.json"

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass

# ── 페이지 설정 ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BRIDGE Agent HQ",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
.stApp { background: #0a0e1a; color: #e0e6f0; }
.hq-header {
    background: linear-gradient(135deg, #0d1b3e 0%, #1a2f5e 50%, #0d1b3e 100%);
    border: 1px solid #2a4080; border-radius: 12px;
    padding: 20px 30px; margin-bottom: 20px;
    display: flex; justify-content: space-between; align-items: center;
    box-shadow: 0 0 30px rgba(42,100,200,0.3);
}
.hq-title { font-size:26px; font-weight:800; color:#5b9cf6; letter-spacing:3px; margin:0; }
.hq-subtitle { color:#7a9cc8; font-size:13px; margin:4px 0 0; }
.hq-time { color:#4ecdc4; font-size:20px; font-family:monospace; }
.kpi-card {
    background: linear-gradient(145deg, #111827, #1a2535);
    border: 1px solid #2a3f5f; border-radius:10px;
    padding:18px 20px; text-align:center;
    box-shadow: 0 4px 15px rgba(0,0,0,0.4);
}
.kpi-value { font-size:36px; font-weight:800; line-height:1; }
.kpi-label { font-size:12px; color:#7a9cc8; margin-top:6px; letter-spacing:1px; }
.kpi-blue  .kpi-value { color:#5b9cf6; }
.kpi-green .kpi-value { color:#4ade80; }
.kpi-red   .kpi-value { color:#f87171; }
.kpi-amber .kpi-value { color:#fbbf24; }
.kpi-teal  .kpi-value { color:#4ecdc4; }
.kpi-purple .kpi-value { color:#a78bfa; }
.panel-title {
    font-size:12px; font-weight:700; color:#5b9cf6;
    letter-spacing:2px; text-transform:uppercase;
    border-bottom:1px solid #1e3a5f; padding-bottom:8px; margin-bottom:12px;
}
.badge-ok   { background:#064e2b; color:#4ade80; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:700; }
.badge-warn { background:#713f12; color:#fbbf24; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:700; }
.badge-err  { background:#4c1019; color:#f87171; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:700; }
.log-ok   { color:#4ade80; font-size:11px; font-family:monospace; }
.log-err  { color:#f87171; font-size:11px; font-family:monospace; }
.log-warn { color:#fbbf24; font-size:11px; font-family:monospace; }
.log-info { color:#94a3b8; font-size:11px; font-family:monospace; }
.file-item {
    background:#1a2535; border-left:3px solid #5b9cf6;
    padding:6px 10px; margin:4px 0; border-radius:0 6px 6px 0; font-size:12px;
}
.file-hot { border-left-color:#f87171; }
</style>
""", unsafe_allow_html=True)


# ── DB 통계 ───────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def get_stats() -> dict:
    s = {}
    # bridge base DB
    try:
        conn = sqlite3.connect(str(DB_PATH))
        s["jobs"]            = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        s["hot_jobs"]        = conn.execute("SELECT COUNT(*) FROM jobs WHERE daily_hours < 7.0").fetchone()[0]
        s["client_inquiries"]= conn.execute("SELECT COUNT(*) FROM client_inquiries").fetchone()[0]
        s["ad_posts"]        = conn.execute("SELECT COUNT(*) FROM ad_posts").fetchone()[0]
        s["db_size_kb"]      = round(DB_PATH.stat().st_size / 1024)

        # 최근 구인처 5건
        s["recent_clients"] = conn.execute(
            "SELECT school_name, location, salary_raw, loaded_at FROM client_inquiries ORDER BY loaded_at DESC LIMIT 6"
        ).fetchall()

        # 최근 HOT 구인 5건
        s["recent_hot"] = conn.execute(
            "SELECT job_code, location, salary_min, salary_max, working_hours FROM jobs WHERE daily_hours < 7.0 ORDER BY loaded_at DESC LIMIT 5"
        ).fetchall()

        # 지역 분포
        s["city_top"] = conn.execute(
            "SELECT city, COUNT(*) n FROM jobs WHERE city!='' GROUP BY city ORDER BY n DESC LIMIT 5"
        ).fetchall()

        conn.close()
    except Exception as e:
        s["bridge_err"] = str(e)

    # 구직자 DB (Codex testing)
    try:
        conn2 = sqlite3.connect(str(CAND_DB))
        s["candidates"]  = conn2.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
        s["cand_active"] = conn2.execute("SELECT COUNT(*) FROM candidates WHERE status='Active'").fetchone()[0]
        s["recent_cands"] = conn2.execute(
            "SELECT candidate_id, full_name, nationality, e_visa, created_at FROM candidates ORDER BY created_at DESC LIMIT 6"
        ).fetchall()
        s["nat_top"] = conn2.execute(
            "SELECT nationality, COUNT(*) n FROM candidates WHERE nationality!='' GROUP BY nationality ORDER BY n DESC LIMIT 5"
        ).fetchall()
        conn2.close()
    except Exception as e:
        s["cand_err"] = str(e)
        s["candidates"]  = 0
        s["cand_active"] = 0

    return s


@st.cache_data(ttl=10)
def get_log_lines(n: int = 35) -> list:
    for log in [LOG_PATH, BASE_DIR / "logs/ad_poster.log"]:
        if log.exists():
            try:
                text  = log.read_text(encoding="utf-8", errors="replace")
                lines = [l for l in text.splitlines() if l.strip()]
                return lines[-n:]
            except Exception:
                pass
    return []


def get_intake_files() -> dict:
    result = {}
    for key, path in [("cand", INTAKE_CAND), ("jobs", INTAKE_JOBS)]:
        if path.exists():
            files = sorted([f for f in path.iterdir() if f.is_file()],
                           key=lambda f: f.stat().st_mtime, reverse=True)
            result[key] = files
        else:
            result[key] = []
    return result


def system_checks() -> list:
    checks = []
    checks.append({"name": "master.db (구인)", "ok": DB_PATH.exists(),
                   "detail": f"{round(DB_PATH.stat().st_size/1024)}KB" if DB_PATH.exists() else "없음"})
    checks.append({"name": "candidates DB",    "ok": CAND_DB.exists(),
                   "detail": "3,059명" if CAND_DB.exists() else "없음"})
    checks.append({"name": "Service Account",  "ok": SA_JSON.exists(),
                   "detail": "bridge-agent@..." if SA_JSON.exists() else "없음"})
    cand_id = os.getenv("GOOGLE_SHEETS_CANDIDATES_ID", "")
    job_id  = os.getenv("GOOGLE_SHEETS_JOBS_ID", "")
    checks.append({"name": "Sheets (구직자)", "ok": bool(cand_id),
                   "detail": cand_id[:18]+"..." if cand_id else "미설정"})
    checks.append({"name": "Sheets (구인처)", "ok": bool(job_id),
                   "detail": job_id[:18]+"..." if job_id else "미설정"})
    checks.append({"name": "intake/candidates", "ok": INTAKE_CAND.exists(), "detail": "OK"})
    checks.append({"name": "intake/jobs",       "ok": INTAKE_JOBS.exists(), "detail": "OK"})
    return checks


def run_pull() -> str:
    puller = BASE_DIR / "google_sheets_puller.py"
    try:
        r = subprocess.run(
            [sys.executable, str(puller), "--once"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60, cwd=str(BASE_DIR)
        )
        return (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return "[TIMEOUT] 60초 초과"
    except Exception as e:
        return f"[ERROR] {e}"


# ── UI ────────────────────────────────────────────────────────────────────────
now_kst = datetime.now(timezone(timedelta(hours=9)))

st.markdown(f"""
<div class="hq-header">
  <div>
    <div class="hq-title">🛰️ BRIDGE Agent HQ</div>
    <div class="hq-subtitle">채용 자동화 통제실 &nbsp;|&nbsp; Q:/Claudework/bridge base &nbsp;|&nbsp; Pull 방식 · 포트 개방 없음</div>
  </div>
  <div class="hq-time">{now_kst.strftime('%Y-%m-%d %H:%M:%S')} KST</div>
</div>
""", unsafe_allow_html=True)

# 컨트롤 바
c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    auto = st.toggle("자동 새로고침 30초", value=False)
with c2:
    if st.button("🔄 새로고침", use_container_width=True):
        st.cache_data.clear(); st.rerun()
with c3:
    if st.button("📥 Sheets 당기기", use_container_width=True):
        with st.spinner("Google Sheets Pull 중..."):
            out = run_pull()
        st.cache_data.clear()
        st.code(out[:600], language="text")

if auto:
    time.sleep(30); st.rerun()

st.markdown("---")

# ── KPI ───────────────────────────────────────────────────────────────────────
stats = get_stats()
kpi_cols = st.columns(6)
kpis = [
    ("kpi-blue",   "👤", stats.get("candidates", 0),      "전체 구직자"),
    ("kpi-green",  "✅", stats.get("cand_active", 0),     "활성 구직자"),
    ("kpi-amber",  "🏫", stats.get("client_inquiries", 0),"구인처 문의"),
    ("kpi-purple", "💼", stats.get("jobs", 0),            "구인 포지션"),
    ("kpi-red",    "🔥", stats.get("hot_jobs", 0),        "HOT 포지션"),
    ("kpi-teal",   "📢", stats.get("ad_posts", 0),        "광고 게시"),
]
for col, (cls, icon, val, label) in zip(kpi_cols, kpis):
    with col:
        st.markdown(f'<div class="kpi-card {cls}"><div class="kpi-value">{icon} {val:,}</div>'
                    f'<div class="kpi-label">{label}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── 3컬럼 ─────────────────────────────────────────────────────────────────────
left, mid, right = st.columns([1.2, 1.6, 1.2])

with left:
    st.markdown('<div class="panel-title">⚙️ 시스템 체크</div>', unsafe_allow_html=True)
    for c in system_checks():
        badge = '<span class="badge-ok">OK</span>' if c["ok"] else '<span class="badge-err">없음</span>'
        st.markdown(f'{badge} &nbsp; **{c["name"]}** &nbsp; '
                    f'<span style="color:#7a9cc8;font-size:11px">{c["detail"]}</span>',
                    unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="panel-title">📂 Intake 대기열</div>', unsafe_allow_html=True)
    intake = get_intake_files()
    pending = intake["cand"] + intake["jobs"]
    if not pending:
        st.markdown('<span class="badge-ok">CLEAR</span> &nbsp; 대기 파일 없음', unsafe_allow_html=True)
    else:
        for f in pending[:6]:
            kind = "👤" if "cand" in str(f.parent) else "💼"
            st.markdown(f'<div class="file-item">{kind} {f.name[:40]}</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="panel-title">🌏 지역 분포 TOP 5</div>', unsafe_allow_html=True)
    total_j = stats.get("jobs", 1) or 1
    for name, cnt in stats.get("city_top", []):
        pct = round(cnt / total_j * 100, 1)
        bar = "█" * int(pct / 3)
        st.markdown(f'<span style="color:#5b9cf6;font-size:12px">{name[:6]:<6}</span> '
                    f'<span style="color:#4ade80;font-family:monospace">{bar}</span> '
                    f'<span style="color:#7a9cc8;font-size:11px">{cnt}건 ({pct}%)</span>',
                    unsafe_allow_html=True)

with mid:
    st.markdown('<div class="panel-title">📡 실시간 로그</div>', unsafe_allow_html=True)
    lines = get_log_lines(40)
    log_html = ""
    for line in reversed(lines):
        if "ERROR" in line or "실패" in line or "FAIL" in line:
            css = "log-err"
        elif "경고" in line or "WARN" in line:
            css = "log-warn"
        elif "완료" in line or "OK" in line or "저장" in line or "성공" in line:
            css = "log-ok"
        else:
            css = "log-info"
        short = line[:112] + ("…" if len(line) > 112 else "")
        log_html += f'<div class="{css}">{short}</div>'

    st.markdown(
        f'<div style="height:320px;overflow-y:auto;background:#080d18;padding:10px;'
        f'border-radius:8px;border:1px solid #1e3a5f">{log_html or "<div class=log-info>로그 없음</div>"}</div>',
        unsafe_allow_html=True
    )

    st.markdown("---")
    st.markdown('<div class="panel-title">🔥 HOT 구인 (daily_hours &lt; 7h)</div>', unsafe_allow_html=True)
    for row in stats.get("recent_hot", []):
        job_code, loc, sal_min, sal_max, wh = row
        sal_str = f"{sal_min}~{sal_max}m" if sal_min and sal_max else (f"{sal_min}m" if sal_min else "미상")
        st.markdown(
            f'<div class="file-item file-hot"><b style="color:#fbbf24">{job_code}</b> '
            f'<span style="color:#94a3b8"> | {loc or "위치미상"}</span> '
            f'<span style="color:#4ade80"> | {sal_str} KRW</span></div>',
            unsafe_allow_html=True
        )

with right:
    st.markdown('<div class="panel-title">📋 최근 등록 구직자</div>', unsafe_allow_html=True)
    for row in stats.get("recent_cands", []):
        sid, name, nat, visa, created = row
        dt = created[:10] if created else ""
        st.markdown(
            f'<div class="file-item">'
            f'<span style="color:#fbbf24;font-size:10px">#{sid}</span> '
            f'<b style="color:#e0e6f0">{(name or "")[:16]}</b><br>'
            f'<span style="color:#7a9cc8;font-size:10px">{nat} | {visa} | {dt}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.markdown('<div class="panel-title">🏫 최근 구인처 문의</div>', unsafe_allow_html=True)
    for row in stats.get("recent_clients", []):
        school, loc, sal, loaded = row
        dt = loaded[:10] if loaded else ""
        st.markdown(
            f'<div class="file-item">'
            f'<b style="color:#a78bfa">{(school or "미상")[:20]}</b><br>'
            f'<span style="color:#7a9cc8;font-size:10px">{loc or ""} | {sal or ""} | {dt}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.markdown('<div class="panel-title">🔗 Sheets 동기화 상태</div>', unsafe_allow_html=True)
    if STATE_FILE.exists():
        try:
            state_data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            cand_id = os.getenv("GOOGLE_SHEETS_CANDIDATES_ID", "")
            job_id  = os.getenv("GOOGLE_SHEETS_JOBS_ID", "")
            for sid, n in state_data.items():
                label = "구직자" if sid == cand_id else "구인처"
                st.markdown(
                    f'<span class="badge-ok">SYNCED</span> &nbsp; **{label}** '
                    f'<span style="color:#7a9cc8;font-size:11px">{n}행 처리</span>',
                    unsafe_allow_html=True
                )
        except Exception:
            pass
    else:
        st.markdown('<span class="badge-warn">PENDING</span> &nbsp; Pull 전', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="panel-title">💾 DB 무결성</div>', unsafe_allow_html=True)
    db_mod = datetime.fromtimestamp(DB_PATH.stat().st_mtime, tz=timezone(timedelta(hours=9)))
    st.markdown(f"""
<div style="font-size:12px;color:#94a3b8;line-height:2">
구인처 DB: <b style="color:#5b9cf6">{stats.get('db_size_kb',0):,}KB</b><br>
수정일시: <b style="color:#4ecdc4">{db_mod.strftime('%m/%d %H:%M')} KST</b><br>
구직자: <b style="color:#4ade80">{stats.get('candidates',0):,}명</b>
  (Active {stats.get('cand_active',0)})<br>
구인처: <b style="color:#fbbf24">{stats.get('client_inquiries',0):,}건</b><br>
포지션: <b style="color:#f87171">{stats.get('jobs',0):,}건</b>
  (HOT {stats.get('hot_jobs',0)})<br>
광고: <b style="color:#a78bfa">{stats.get('ad_posts',0):,}건</b>
</div>
""", unsafe_allow_html=True)

st.markdown("---")
with st.expander("📖 파이프라인 구조"):
    st.markdown("""
```
[Google Forms 제출]
        ↓ Google Sheets 자동 기록
google_sheets_puller.py  (Pull · 5분 간격 · 포트 개방 없음)
        ↓ CSV 저장
Q:/Claudework/bridge base/intake/candidates|jobs/
        ↓
email_watcher.py  (Gmail/Naver 첨부파일 · 5분 폴링)
        ↓

>> 모든 경로가 bridge base 기준 <<
```
""")
