"""
tools/notion_daily_log.py
=========================
Claude Code 세션 작업 내역을 Notion + Obsidian에 자동 기록.

실행 방식:
  - Claude Code Stop 훅에서 자동 호출
  - 수동: python tools/notion_daily_log.py [메모]
  - 즐겨찾기: python tools/notion_daily_log.py --star "이 방법이 최고였다"

Notion 구조:
  지정 페이지 하위
  ├ ⭐ 하이라이트 (고정 토글 — 좋았던 작업 모음)
  └ 날짜별 토글 (오래된 것 90일 후 자동 삭제)
      ├ 세션 시간
      ├ git 커밋 목록
      └ work_state 요약

Obsidian 자동 백업:
  Q:/Claudework/bridge base/docs/obsidian/BRIDGE_작업일지.md 에 추가

설정 (pw.py로 BX에 저장):
  NOTION_TOKEN    — Notion Integration Token (secret_xxx)
  NOTION_PAGE_ID  — 메모 저장할 페이지 ID
"""

import sys
import os
import re
import json
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request as UrlRequest, urlopen
from urllib.error import HTTPError

BASE = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))
OBSIDIAN_LOG = BASE / "docs" / "obsidian" / "BRIDGE_작업일지.md"
KEEP_DAYS = 90          # 이보다 오래된 날짜 토글 자동 삭제
HIGHLIGHT_TITLE = "⭐ 하이라이트"

# ── BX에서 키 읽기 ─────────────────────────────────────────────────────────
def _bx_read(key: str) -> str:
    sys.path.insert(0, str(BASE))
    try:
        from tools.bx import _read
        return _read(key) or ""
    except Exception:
        return ""


def _get_credentials() -> tuple[str, str]:
    token = os.environ.get("NOTION_TOKEN") or _bx_read("NOTION_TOKEN")
    page_id = os.environ.get("NOTION_PAGE_ID") or _bx_read("NOTION_PAGE_ID")
    raw = page_id.strip()
    m = re.search(r"([0-9a-f]{32})", raw.replace("-", "").lower())
    clean_id = m.group(1) if m else raw.replace("-", "")
    return token.strip(), clean_id


# ── Notion API 헬퍼 ───────────────────────────────────────────────────────
NOTION_API = "https://api.notion.com/v1"
NOTION_VER = "2022-06-28"


def _notion_req(token: str, method: str, path: str, body: dict = None) -> dict:
    url = f"{NOTION_API}{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    req = UrlRequest(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VER,
        "Content-Type": "application/json",
    })
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body_txt = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Notion API {e.code}: {body_txt[:300]}")


def _get_children(token: str, block_id: str) -> list:
    resp = _notion_req(token, "GET", f"/blocks/{block_id}/children?page_size=100")
    return resp.get("results", [])


def _block_text(blk: dict) -> str:
    t = blk.get("type", "")
    rich = blk.get(t, {}).get("rich_text", [])
    return "".join(r.get("plain_text", "") for r in rich)


# ── 하이라이트 토글 조회/생성 ────────────────────────────────────────────────
def _get_or_create_highlight_toggle(token: str, page_id: str) -> str:
    blocks = _get_children(token, page_id)
    for blk in blocks:
        if blk.get("type") == "toggle" and HIGHLIGHT_TITLE in _block_text(blk):
            return blk["id"]
    res = _notion_req(token, "PATCH", f"/blocks/{page_id}/children", {"children": [{
        "object": "block", "type": "toggle",
        "toggle": {"rich_text": [{"type": "text",
            "text": {"content": HIGHLIGHT_TITLE},
            "annotations": {"bold": True, "color": "yellow"}}],
            "children": []},
    }]})
    return res["results"][0]["id"]


# ── 날짜 토글 조회/생성 ──────────────────────────────────────────────────────
def _get_or_create_today_toggle(token: str, page_id: str, today_str: str) -> str:
    blocks = _get_children(token, page_id)
    for blk in blocks:
        if blk.get("type") == "toggle" and today_str in _block_text(blk):
            return blk["id"]
    res = _notion_req(token, "PATCH", f"/blocks/{page_id}/children", {"children": [{
        "object": "block", "type": "toggle",
        "toggle": {"rich_text": [{"type": "text",
            "text": {"content": today_str},
            "annotations": {"bold": True, "color": "blue"}}],
            "children": []},
    }]})
    return res["results"][0]["id"]


# ── 오래된 날짜 토글 자동 삭제 ──────────────────────────────────────────────
def _auto_cleanup(token: str, page_id: str):
    """KEEP_DAYS보다 오래된 날짜 토글 삭제."""
    blocks = _get_children(token, page_id)
    cutoff = datetime.now(KST) - timedelta(days=KEEP_DAYS)
    deleted = 0
    for blk in blocks:
        if blk.get("type") != "toggle":
            continue
        text = _block_text(blk)
        if HIGHLIGHT_TITLE in text:
            continue  # 하이라이트 토글은 절대 삭제 안 함
        # "2026년 04월 09일" 형식 파싱
        m = re.search(r"(\d{4})년\s*(\d{2})월\s*(\d{2})일", text)
        if not m:
            continue
        try:
            blk_date = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=KST)
        except ValueError:
            continue
        if blk_date < cutoff:
            try:
                _notion_req(token, "DELETE", f"/blocks/{blk['id']}")
                deleted += 1
            except Exception:
                pass
    if deleted:
        print(f"[notion_daily_log] 🗑 {deleted}개 오래된 항목 삭제 ({KEEP_DAYS}일 초과)")


# ── git 커밋 수집 ─────────────────────────────────────────────────────────
def _get_today_commits() -> list[str]:
    today_kst = datetime.now(KST).strftime("%Y-%m-%d")
    try:
        result = subprocess.run(
            ["git", "-C", str(BASE), "log",
             "--after", f"{today_kst}T00:00:00+09:00",
             "--format=%h %s"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        return [l.strip() for l in result.stdout.splitlines() if l.strip()][:20]
    except Exception:
        return []


# ── work_state 요약 ──────────────────────────────────────────────────────
def _get_work_state_summary() -> str:
    ws = BASE / ".claude" / "work_state.md"
    if not ws.exists():
        return ""
    lines = ws.read_text(encoding="utf-8", errors="replace").splitlines()
    collecting, snippet = False, []
    for line in lines:
        if line.startswith("## ✅") and not collecting:
            collecting = True
            snippet.append(line)
        elif collecting:
            if line.startswith("## ") and not line.startswith("## ✅"):
                break
            snippet.append(line)
            if len(snippet) > 25:
                snippet.append("...")
                break
    return "\n".join(snippet[:25])


# ── Notion 세션 블록 추가 ────────────────────────────────────────────────
def _append_session_blocks(token: str, toggle_id: str, commits: list[str],
                           ws_summary: str, memo: str):
    now_kst = datetime.now(KST).strftime("%H:%M")
    children = [{"object": "block", "type": "heading_3",
        "heading_3": {"rich_text": [{"type": "text",
            "text": {"content": f"세션 {now_kst} KST"}}]}}]

    if memo:
        children.append({"object": "block", "type": "callout",
            "callout": {"icon": {"type": "emoji", "emoji": "📝"},
                "rich_text": [{"type": "text", "text": {"content": memo}}],
                "color": "yellow_background"}})

    if commits:
        children.append({"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text",
                "text": {"content": "Git 커밋"}, "annotations": {"bold": True}}]}})
        for c in commits:
            children.append({"object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text",
                    "text": {"content": c}, "annotations": {"code": True}}]}})
    else:
        children.append({"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text",
                "text": {"content": "커밋 없음"}, "annotations": {"color": "gray"}}]}})

    if ws_summary:
        children.append({"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text",
                "text": {"content": "작업 요약"}, "annotations": {"bold": True}}]}})
        children.append({"object": "block", "type": "quote",
            "quote": {"rich_text": [{"type": "text",
                "text": {"content": ws_summary[:1800]}}]}})

    children.append({"object": "block", "type": "divider", "divider": {}})
    _notion_req(token, "PATCH", f"/blocks/{toggle_id}/children",
                {"children": children[:100]})


# ── 하이라이트 저장 ──────────────────────────────────────────────────────
def _append_highlight(token: str, page_id: str, text: str):
    hl_id = _get_or_create_highlight_toggle(token, page_id)
    now_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    _notion_req(token, "PATCH", f"/blocks/{hl_id}/children", {"children": [
        {"object": "block", "type": "bulleted_list_item",
         "bulleted_list_item": {"rich_text": [
             {"type": "text", "text": {"content": f"[{now_str}] "},
              "annotations": {"color": "gray"}},
             {"type": "text", "text": {"content": text},
              "annotations": {"bold": True}},
         ]}},
    ]})
    print(f"[notion_daily_log] ⭐ 하이라이트 저장: {text[:50]}")


# ── Obsidian 백업 ─────────────────────────────────────────────────────────
def _sync_obsidian(commits: list[str], ws_summary: str, memo: str):
    try:
        now_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
        today_str = datetime.now(KST).strftime("%Y-%m-%d")
        lines = [f"\n## {today_str} {now_str[:5]} KST"]
        if memo:
            lines.append(f"> {memo}")
        if commits:
            lines.append("**커밋**")
            for c in commits:
                lines.append(f"- `{c}`")
        if ws_summary:
            lines.append("**요약**")
            lines.append(ws_summary[:500])
        lines.append("---")
        with open(OBSIDIAN_LOG, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"[notion_daily_log] 📓 Obsidian 동기화 완료")
    except Exception as e:
        print(f"[notion_daily_log] Obsidian 동기화 실패: {e}")


# ── 메인 ─────────────────────────────────────────────────────────────────
def run(memo: str = "", star: bool = False):
    token, page_id = _get_credentials()
    if not token:
        print("[notion_daily_log] NOTION_TOKEN 없음 — pw.py에서 저장 필요")
        return False
    if not page_id:
        print("[notion_daily_log] NOTION_PAGE_ID 없음 — pw.py에서 저장 필요")
        return False

    today_str = datetime.now(KST).strftime("%Y년 %m월 %d일 (%a)")
    commits = _get_today_commits()
    ws_summary = _get_work_state_summary()

    try:
        if star and memo:
            _append_highlight(token, page_id, memo)
            return True

        # 오래된 항목 정리 (90일 초과)
        _auto_cleanup(token, page_id)

        # 오늘 토글에 세션 기록
        toggle_id = _get_or_create_today_toggle(token, page_id, today_str)
        _append_session_blocks(token, toggle_id, commits, ws_summary, memo)

        # Obsidian 백업
        _sync_obsidian(commits, ws_summary, memo)

        now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
        print(f"[notion_daily_log] ✅ 완료 ({now_kst} KST) — 커밋 {len(commits)}건")
        return True
    except Exception as e:
        print(f"[notion_daily_log] ❌ 실패: {e}")
        return False


if __name__ == "__main__":
    args = sys.argv[1:]
    is_star = "--star" in args
    if is_star:
        args.remove("--star")
    extra_memo = " ".join(args)
    ok = run(extra_memo, star=is_star)
    sys.exit(0 if ok else 1)
