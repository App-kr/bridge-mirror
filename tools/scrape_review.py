#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bridge 구 홈페이지 /review 게시판 → 새 웹 master.db 마이그레이션 스크립트

사용법:
  Q:\Claudework\bridge base\ 폴더에서 실행:
    python -X utf8 tools/scrape_review.py

  → 실행하면 아이디/비밀번호 입력 프롬프트 표시
  → 비밀번호는 입력해도 화면에 안 보임 (getpass)
  → 파일 어디에도 저장되지 않음

결과:
  - master.db testimonials 테이블에 실제 리뷰 삽입
  - sort_order=1000 → 가상 데이터(sort_order=0)보다 항상 먼저 표시
  - 이미지는 구 사이트 URL 그대로 photo_url에 저장
"""

BASE_URL    = "http://bridgejob.co.kr"
BOARD_TABLE = "review"
DB_PATH     = "master.db"
DELAY_SEC   = 0.5

import requests
import sqlite3
import re
import time
import sys
import getpass
from datetime import datetime, timezone


# ── 세션 로그인 ────────────────────────────────────────────────
def login(session: requests.Session, gid: str, gpw: str) -> bool:
    resp = session.post(
        f"{BASE_URL}/bbs/login_check.php",
        data={
            "mb_id":         gid,
            "mb_password":   gpw,
            "url":           f"{BASE_URL}/",
            "mb_save_login": "1",
        },
        allow_redirects=True,
        timeout=15,
    )
    return "logout" in resp.text.lower() or resp.url == f"{BASE_URL}/"


# ── 실제 wr_id 수집 ───────────────────────────────────────────
def get_all_wr_ids(session: requests.Session) -> list:
    """
    여러 경로를 순서대로 시도해 실제 wr_id 추출.
    1) 일반 게시판 목록 (로그인 시 href 포함)
    2) admin 경로 여러 개 시도
    3) 위 실패 시 debug HTML 저장 후 종료
    """
    wr_ids = set()
    page = 1
    while True:
        resp = session.get(
            f"{BASE_URL}/bbs/board.php",
            params={"bo_table": BOARD_TABLE, "page": page},
            timeout=15,
        )
        # 로그인 시 /review/숫자 형태로 링크 노출됨
        found = re.findall(rf'/{BOARD_TABLE}/(\d+)', resp.text)
        if not found:
            break
        new = {int(x) for x in found} - wr_ids
        if not new:
            break
        wr_ids.update(new)
        print(f"  페이지 {page}: {sorted(new, reverse=True)[:5]} ({len(new)}개)")
        page += 1
        time.sleep(DELAY_SEC)
    return sorted(wr_ids, reverse=True)


# ── 개별 게시글 파싱 ───────────────────────────────────────────
def parse_post(html: str, wr_id: int) -> dict:
    # 제목
    title_m = (
        re.search(r'<h2[^>]*class="[^"]*bo_v_tit[^"]*"[^>]*>(.*?)</h2>', html, re.DOTALL) or
        re.search(r'<span[^>]*class="[^"]*bo_v_tit[^"]*"[^>]*>(.*?)</span>', html, re.DOTALL) or
        re.search(r'<title>([^<|]+)', html)
    )
    title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip() if title_m else f"Review #{wr_id}"
    title = re.sub(r'\s*\|\s*BRIDGE.*$', '', title).strip()

    # 작성자
    author_m = (
        re.search(r'class="sv_member[^"]*">([^<]+)<', html) or
        re.search(r'class="[^"]*member[^"]*">([^<]+)<', html)
    )
    author = author_m.group(1).strip() if author_m else "Teacher"

    # 날짜
    date_m = (
        re.search(r'class="[^"]*sv_date[^"]*"[^>]*>\s*([0-9]{2,4}[-./][0-9]{1,2}[-./][0-9]{1,2})', html) or
        re.search(r'([0-9]{4}[-./][0-9]{2}[-./][0-9]{2})', html)
    )
    raw_date = date_m.group(1) if date_m else "2024-01-01"
    created_at = "2024-01-01T00:00:00Z"
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            created_at = datetime.strptime(raw_date[:10], fmt).strftime("%Y-%m-%dT%H:%M:%SZ")
            break
        except ValueError:
            continue

    # 본문 (여러 패턴 시도 — gnuboard 스킨마다 다름)
    content_m = (
        re.search(r'<div[^>]*id="bo_v_con"[^>]*>(.*?)</div>\s*<div', html, re.DOTALL) or
        re.search(r'<div[^>]*class="[^"]*bo_v_con[^"]*"[^>]*>(.*?)</div>\s*<div', html, re.DOTALL) or
        re.search(r'bo_v_con["\'][^>]*>(.*?)<(?:div|section|article)', html, re.DOTALL) or
        re.search(r'<div[^>]*id="bo_v_con"[^>]*>(.*)', html, re.DOTALL)  # 끝까지
    )
    review_text = ""
    if content_m:
        raw = content_m.group(1)
        text = re.sub(r'<br\s*/?>', '\n', raw)
        text = re.sub(r'<p[^>]*>', '\n', text)
        text = re.sub(r'</p>', '\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        for ent, ch in [('&nbsp;', ' '), ('&lt;', '<'), ('&gt;', '>'), ('&amp;', '&'), ('&quot;', '"')]:
            text = text.replace(ent, ch)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        review_text = text.strip()

    if not review_text or len(review_text) < 10:
        return None

    # 이미지 (원본 우선, 없으면 썸네일)
    img_urls = re.findall(
        r'src="((?:http://bridgejob\.co\.kr)?/data/file/review/(?!thumb)[^"]+)"', html
    )
    if not img_urls:
        img_urls = re.findall(
            r'src="((?:http://bridgejob\.co\.kr)?/data/file/review/[^"]+)"', html
        )
    photo_url = None
    if img_urls:
        url = img_urls[0]
        if not url.startswith("http"):
            url = BASE_URL + url
        photo_url = url

    # 국가 감지
    country = "USA"
    country_map = {
        "canada": "Canada", "canadian": "Canada",
        "australia": "Australia", "australian": "Australia",
        "uk": "UK", "united kingdom": "UK", "england": "UK", "british": "UK",
        "ireland": "Ireland", "irish": "Ireland",
        "new zealand": "New Zealand", "kiwi": "New Zealand",
        "south africa": "South Africa", "south african": "South Africa",
    }
    text_lower = (title + " " + review_text).lower()
    for kw, cn in country_map.items():
        if kw in text_lower:
            country = cn
            break

    return {
        "name":        author,
        "country":     country,
        "photo_url":   photo_url,
        "rating":      5,
        "review_text": review_text[:2000],
        "sort_order":  1000,
        "is_visible":  1,
        "is_deleted":  0,
        "created_at":  created_at,
    }


# ── DB 삽입 ────────────────────────────────────────────────────
def insert_to_db(posts: list) -> int:
    conn = sqlite3.connect(DB_PATH)
    now  = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    inserted = 0
    for p in posts:
        conn.execute(
            """INSERT INTO testimonials
               (name, country, photo_url, rating, review_text, sort_order,
                is_visible, is_deleted, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (p["name"], p["country"], p["photo_url"], p["rating"],
             p["review_text"], p["sort_order"], p["is_visible"],
             p["is_deleted"], p["created_at"], now),
        )
        inserted += 1
    conn.commit()
    conn.close()
    return inserted


# ── 메인 ───────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("Bridge /review 게시판 마이그레이션 스크립트")
    print("=" * 60)

    # Windows 자격 증명 관리자에서 불러오기
    # 없으면 입력받고 저장 → 다음부터 자동
    import keyring
    SERVICE = "bridgejob_scraper"
    gid = keyring.get_password(SERVICE, "id") or ""
    gpw = keyring.get_password(SERVICE, "pw") or ""
    if not gid or not gpw:
        print("\n처음 실행 — 저장된 계정 없음. 입력하면 암호화 저장됩니다.")
        gid = input("  그누보드 아이디: ").strip()
        gpw = getpass.getpass("  비밀번호 (안 보임): ")
        keyring.set_password(SERVICE, "id", gid)
        keyring.set_password(SERVICE, "pw", gpw)
        print("  ✅ Windows 자격 증명 관리자에 저장됨 (다음부터 자동)")
    else:
        print(f"  ✅ 저장된 계정 사용: {gid}")

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    # 1. 로그인
    print("\n[1/4] 로그인 중...")
    if not login(session, gid, gpw):
        print("❌ 로그인 실패! ID/PW 확인해주세요.")
        sys.exit(1)
    print("✅ 로그인 성공")

    # 2. wr_id 목록
    print("\n[2/4] 게시글 목록 수집 중...")
    wr_ids = get_all_wr_ids(session)
    if not wr_ids:
        print("❌ 게시글을 찾지 못했습니다.")
        sys.exit(1)
    print(f"✅ 총 {len(wr_ids)}개 게시글 발견: {min(wr_ids)}~{max(wr_ids)}")

    # 3. 개별 크롤링
    print(f"\n[3/4] 게시글 내용 수집 중...")

    # 첫 글 HTML 덤프 (디버그용)
    debug_resp = session.get(
        f"{BASE_URL}/bbs/board.php",
        params={"bo_table": BOARD_TABLE, "wr_id": wr_ids[0]},
        timeout=15,
    )
    with open("tools/debug_post.html", "w", encoding="utf-8") as f:
        f.write(debug_resp.text)
    print(f"  디버그: tools/debug_post.html 저장됨 (wr_id={wr_ids[0]})")

    posts, failed = [], []
    for i, wr_id in enumerate(wr_ids, 1):
        try:
            resp = session.get(
                f"{BASE_URL}/{BOARD_TABLE}/{wr_id}",
                timeout=15,
            )
            post = parse_post(resp.text, wr_id)
            if post:
                posts.append(post)
                print(f"  [{i}/{len(wr_ids)}] wr_id={wr_id} ✅  {post['name'][:20]} | {post['country']} | {len(post['review_text'])}자")
            else:
                print(f"  [{i}/{len(wr_ids)}] wr_id={wr_id} ⚠️  내용 없음 (스킵)")
            time.sleep(DELAY_SEC)
        except Exception as e:
            failed.append(wr_id)
            print(f"  [{i}/{len(wr_ids)}] wr_id={wr_id} ❌ {e}")

    print(f"\n  수집: {len(posts)}개 성공 / {len(failed)}개 실패")

    # 4. DB 삽입
    print(f"\n[4/4] master.db에 삽입 중...")
    inserted = insert_to_db(posts)
    print(f"✅ {inserted}개 삽입 완료")

    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM testimonials WHERE is_visible=1 AND is_deleted=0").fetchone()[0]
    real  = conn.execute("SELECT COUNT(*) FROM testimonials WHERE sort_order=1000").fetchone()[0]
    conn.close()

    print("\n" + "=" * 60)
    print("완료!")
    print(f"  실제 리뷰 (sort_order=1000): {real}개  ← 새 웹에서 먼저 표시")
    print(f"  가상 데이터 (sort_order=0) : {total - real}개")
    print(f"  전체: {total}개")
    print("\n다음 단계: Render에 api_server.py 재배포하면 새 웹에 즉시 반영")
    print("=" * 60)

    if failed:
        print(f"\n⚠️  실패 wr_id: {failed}")


if __name__ == "__main__":
    main()
