#!/usr/bin/env python3
"""
Resume Pipeline v2.0 — 과거 후보자 일괄 큐 등록 스크립트
========================================================

용도: 기존 후보자 중 cv_original_s3_key 있으나 cv_processed_status != 'done' 인
      건들을 durable queue 에 멱등 등록. 워커가 순차 처리.

실행:
  python tools/resume_backfill.py               # 전체 스캔 (dry-run)
  python tools/resume_backfill.py --apply       # 실제 큐 등록
  python tools/resume_backfill.py --apply --limit 50
  python tools/resume_backfill.py --apply --since-days 30
  python tools/resume_backfill.py --apply --source web_form

안전:
  - 멱등 enqueue (중복 호출 무해)
  - 100건 배치마다 2분 대기 (Render 부하 완화)
  - 로컬 PC에서만 실행 (RENDER_API 네트워크 호출 없음, DB 직접 조작 아님)
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

from tools.pipeline_v2 import enqueue_resume_process, log_event  # noqa: E402


def _db() -> sqlite3.Connection:
    p = os.getenv("BRIDGE_DB_PATH") or os.getenv("DB_PATH") or str(BASE / "master.db")
    c = sqlite3.connect(p)
    c.execute("PRAGMA busy_timeout = 5000")
    c.row_factory = sqlite3.Row
    return c


def find_candidates(
    limit: int = 0,
    since_days: int = 0,
    source: str = "",
) -> list[dict]:
    """
    조건에 맞는 후보자 조회:
      - cv_original_s3_key 또는 file_uploads 에 CV 있음
      - cv_processed_status != 'done' (또는 cv_processed_s3_key 없음)
    """
    conn = _db()
    try:
        where = [
            "c.status != 'Deleted'",
            "(c.cv_processed_status IS NULL OR c.cv_processed_status != 'done' OR c.cv_processed_s3_key IS NULL)",
        ]
        params: list = []

        if since_days > 0:
            threshold = (datetime.now(tz=timezone.utc) - timedelta(days=since_days)).isoformat()
            where.append("c.created_at >= ?")
            params.append(threshold)

        if source:
            where.append("c.source = ?")
            params.append(source)

        where_sql = " AND ".join(where)
        limit_sql = f"LIMIT {int(limit)}" if limit > 0 else ""

        sql = f"""
            SELECT
                c.candidate_id,
                c.sheet_number,
                c.cv_processed_status,
                c.cv_processed_s3_key,
                c.cv_original_s3_key,
                COALESCE(
                    c.cv_original_s3_key,
                    (SELECT fu.s3_key FROM file_uploads fu
                     WHERE fu.entity_id = c.candidate_id
                       AND fu.file_type IN ('cv','cover_letter')
                       AND fu.s3_key IS NOT NULL AND fu.s3_key != ''
                       AND (fu.is_deleted = 0 OR fu.is_deleted IS NULL)
                     ORDER BY fu.id DESC LIMIT 1)
                ) AS resolved_cv_key,
                c.created_at,
                c.source
            FROM candidates c
            WHERE {where_sql}
            ORDER BY c.sheet_number DESC
            {limit_sql}
        """
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Resume backfill")
    parser.add_argument("--apply", action="store_true", help="실제 큐 등록 (기본 dry-run)")
    parser.add_argument("--limit", type=int, default=0, help="최대 처리 건수 (0=무제한)")
    parser.add_argument("--since-days", type=int, default=0, help="최근 N일 이내만")
    parser.add_argument("--source", type=str, default="", help="source 필터 (web_form 등)")
    parser.add_argument("--batch-size", type=int, default=100, help="배치 크기")
    parser.add_argument("--batch-delay", type=int, default=120, help="배치 간 대기 (초)")
    args = parser.parse_args()

    rows = find_candidates(limit=args.limit, since_days=args.since_days, source=args.source)

    total = len(rows)
    with_cv = [r for r in rows if r.get("resolved_cv_key")]
    without_cv = [r for r in rows if not r.get("resolved_cv_key")]

    print(f"[SCAN] 대상 후보자: {total}명")
    print(f"  - CV 있음 (enqueue 대상): {len(with_cv)}명")
    print(f"  - CV 없음 (skip): {len(without_cv)}명")

    if not args.apply:
        print("\n[DRY-RUN] --apply 플래그로 실제 등록 가능")
        print("\n샘플 CV 보유 (상위 5):")
        for r in with_cv[:5]:
            print(f"  #{r['sheet_number']} cid={r['candidate_id']} key={(r['resolved_cv_key'] or '')[:70]}")
        return 0

    print("\n[APPLY] 큐 등록 시작...")
    enqueued = 0
    skipped = 0
    errors = 0
    for i, r in enumerate(with_cv):
        try:
            job_id = enqueue_resume_process(
                candidate_id=str(r["candidate_id"]),
                cv_s3_key=str(r["resolved_cv_key"]),
                trigger=f"backfill_{datetime.now(tz=timezone.utc).strftime('%Y%m%d')}",
            )
            enqueued += 1
            if (i + 1) % 10 == 0:
                print(f"  [{i+1}/{len(with_cv)}] enqueued #{r['sheet_number']} job_id={job_id}")
        except Exception as e:
            errors += 1
            print(f"  [ERROR] #{r.get('sheet_number')}: {e}")

        # 배치 간 대기
        if args.batch_delay > 0 and (i + 1) % args.batch_size == 0 and i + 1 < len(with_cv):
            print(f"  [BATCH] {args.batch_size}건 처리 — {args.batch_delay}초 대기...")
            time.sleep(args.batch_delay)

    log_event(
        "backfill_run",
        details={
            "total_scanned": total,
            "with_cv": len(with_cv),
            "without_cv": len(without_cv),
            "enqueued": enqueued,
            "errors": errors,
            "filters": {
                "limit": args.limit,
                "since_days": args.since_days,
                "source": args.source,
            },
        },
        severity="info",
    )

    print(f"\n[DONE] enqueued={enqueued} errors={errors} skipped={skipped}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
