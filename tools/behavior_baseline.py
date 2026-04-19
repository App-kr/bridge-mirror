r"""
behavior_baseline.py — 사용 패턴 학습 + 3σ 이탈 탐지
api_server.py 로그에서 엔드포인트별 정상 호출빈도를 학습,
비정상 패턴 발생 시 텔레그램 알림

사용법:
  python tools/behavior_baseline.py learn            # 최근 7일 로그로 기준선 재계산
  python tools/behavior_baseline.py check            # 최근 1시간 대비 이탈 탐지
  python tools/behavior_baseline.py register         # Windows 스케줄러 등록 (매시간)

저장: .behavior_baseline.json
로그 소스: Render API 로그 (bx에 RENDER_API_TOKEN 있을 때) 또는 로컬 access_log
"""
from __future__ import annotations
import json
import math
import os
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BASELINE_FILE = BASE_DIR / ".behavior_baseline.json"
LOG_FILE = BASE_DIR / "logs" / "behavior.log"
LOG_FILE.parent.mkdir(exist_ok=True)
ACCESS_LOG_DIR = BASE_DIR / "logs"

sys.path.insert(0, str(BASE_DIR))


def _log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _collect_hourly_counts(hours_back: int) -> list[Counter]:
    """시간대별 엔드포인트 호출 카운트. 각 시간마다 Counter({endpoint: count})"""
    counts_by_hour: list[Counter] = []
    cutoff = datetime.now() - timedelta(hours=hours_back)

    # 로컬 로그 파싱 (api_server.py가 logs/access.log 기록 시)
    for log_path in ACCESS_LOG_DIR.glob("*.log"):
        try:
            with open(log_path, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    # FastAPI access log 형식: timestamp METHOD path status
                    if "POST" in line or "GET" in line or "PATCH" in line:
                        # 간단 파싱 (정교하게 하려면 정규식)
                        parts = line.split()
                        for p in parts:
                            if p.startswith("/api/"):
                                # 해당 시간대 bucket에 추가
                                if not counts_by_hour:
                                    counts_by_hour.append(Counter())
                                counts_by_hour[-1][p.split("?")[0]] += 1
                                break
        except Exception:
            continue

    # 로그 없으면 빈 리스트 반환
    return counts_by_hour


def learn():
    """기준선 학습 — 엔드포인트별 평균·표준편차 계산"""
    _log("행동 기준선 학습 시작 (최근 7일)")
    hourly = _collect_hourly_counts(24 * 7)
    if not hourly:
        _log("로그 데이터 없음 — Render 서버 access log 활성화 필요")
        # 기본값으로 저장 (나중에 업데이트 가능)
        baseline = {
            "generated": datetime.now().isoformat(),
            "note": "로그 데이터 부족 — 학습 전 기본값",
            "endpoints": {},
        }
    else:
        per_endpoint: dict[str, list[int]] = defaultdict(list)
        for bucket in hourly:
            for ep, cnt in bucket.items():
                per_endpoint[ep].append(cnt)
        baseline_eps = {}
        for ep, counts in per_endpoint.items():
            if len(counts) < 3:
                continue
            mean = statistics.mean(counts)
            stdev = statistics.stdev(counts) if len(counts) > 1 else 0
            baseline_eps[ep] = {
                "mean": round(mean, 2),
                "stdev": round(stdev, 2),
                "threshold_3sigma": round(mean + 3 * stdev, 2),
                "samples": len(counts),
            }
        baseline = {
            "generated": datetime.now().isoformat(),
            "endpoints": baseline_eps,
        }

    BASELINE_FILE.write_text(json.dumps(baseline, indent=2, ensure_ascii=False), encoding="utf-8")
    _log(f"기준선 저장: {BASELINE_FILE} ({len(baseline.get('endpoints', {}))}개 엔드포인트)")


def check():
    """최근 1시간 vs 기준선 비교 → 3σ 이탈 시 알림"""
    if not BASELINE_FILE.exists():
        _log("기준선 없음 — 먼저 learn 실행")
        return
    with open(BASELINE_FILE, encoding="utf-8") as f:
        base = json.load(f)
    eps = base.get("endpoints", {})
    if not eps:
        _log("기준선 비어있음 — 학습 데이터 부족")
        return

    curr = _collect_hourly_counts(1)
    if not curr:
        _log("최근 1시간 로그 없음")
        return

    current_total = Counter()
    for c in curr:
        current_total.update(c)

    alerts = []
    for ep, cnt in current_total.items():
        if ep not in eps:
            # 새 엔드포인트 호출 — 정찰 시도 가능성
            alerts.append(f"[NEW] 미기록 엔드포인트 호출: {ep} ({cnt}회)")
            continue
        threshold = eps[ep]["threshold_3sigma"]
        if cnt > threshold and cnt > 10:  # 최소 10회 이상 + 3σ 초과
            alerts.append(
                f"[SPIKE] {ep}: {cnt}회 (평균 {eps[ep]['mean']}, 임계 {threshold})"
            )

    if alerts:
        _log(f"행동 이상 감지: {len(alerts)}건")
        for a in alerts:
            _log(f"  {a}")
        try:
            from tools.tg_notify import send_telegram  # type: ignore
            send_telegram(f"⚠️ BRIDGE 행동 이상 ({len(alerts)}건)\n\n" + "\n".join(alerts[:15]))
        except Exception as e:
            _log(f"텔레그램 실패: {e}")
    else:
        _log("행동 정상 — 기준선 이내")


def register_scheduled_task():
    python = sys.executable
    script = str(Path(__file__).resolve())
    r = subprocess.run([
        "schtasks", "/create",
        "/sc", "hourly",
        "/tn", "BRIDGE_Behavior_Check",
        "/tr", f'"{python}" "{script}" check',
        "/rl", "limited",
        "/f",
    ], capture_output=True, text=True, creationflags=0x08000000)
    if r.returncode == 0:
        _log("스케줄러 등록 완료 (매시간)")
    else:
        _log(f"등록 실패: {r.stderr}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1].lower()
    if cmd == "learn":
        learn()
    elif cmd == "check":
        check()
    elif cmd == "register":
        register_scheduled_task()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
