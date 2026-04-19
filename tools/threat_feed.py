r"""
threat_feed.py — 무료 공개 위협 인텔 피드 동기화
Spamhaus DROP + Firehol level1 → 로컬 블록리스트

사용법:
  python tools/threat_feed.py sync       # 최신 피드 다운로드 (매일 1회)
  python tools/threat_feed.py register   # Windows 작업 스케줄러에 등록 (매일 오전 3시)
  python tools/threat_feed.py check IP   # 특정 IP가 리스트에 있는지 확인

출력: data/threat_feed.txt
  형식: CIDR 네트워크 줄당 1개 (# 주석 허용)
  api_server.py가 이 파일을 로드해서 요청 IP와 매칭
"""
from __future__ import annotations
import ipaddress
import os
import socket
import ssl
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FEED_FILE = BASE_DIR / "data" / "threat_feed.txt"
FEED_FILE.parent.mkdir(exist_ok=True)
LOG_FILE = BASE_DIR / "logs" / "threat_feed.log"
LOG_FILE.parent.mkdir(exist_ok=True)

# 완전 무료, 회원가입 불필요, 회사 결제 유도 없음
FEEDS = [
    # Spamhaus DROP — 확인된 악성 /24 네트워크
    ("spamhaus_drop", "https://www.spamhaus.org/drop/drop.txt"),
    # Spamhaus eDROP — DROP + 추가 정보
    ("spamhaus_edrop", "https://www.spamhaus.org/drop/edrop.txt"),
    # Firehol level1 — 다양한 소스 종합 (가장 신뢰도 높음)
    ("firehol_level1", "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level1.netset"),
]


def _log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _fetch(url: str) -> str:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "BRIDGE-ThreatFeed/1.0"})
    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
        return r.read().decode("utf-8", errors="ignore")


def _parse(text: str) -> set[str]:
    """피드에서 CIDR만 추출 (주석 제거)"""
    result: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(";") or line.startswith("#"):
            continue
        # Spamhaus 형식: "x.x.x.x/y ; SBL..."
        cidr = line.split(";")[0].strip().split()[0]
        try:
            ipaddress.ip_network(cidr, strict=False)
            result.add(cidr)
        except ValueError:
            continue
    return result


def sync_feeds():
    all_cidrs: set[str] = set()
    sources: dict[str, int] = {}
    for name, url in FEEDS:
        try:
            _log(f"{name} 다운로드 중: {url}")
            text = _fetch(url)
            cidrs = _parse(text)
            sources[name] = len(cidrs)
            all_cidrs.update(cidrs)
            _log(f"  → {len(cidrs)}개 CIDR")
        except Exception as e:
            _log(f"  {name} 실패: {e}")
            sources[name] = 0

    if not all_cidrs:
        _log("모든 피드 실패 — 기존 파일 유지")
        return

    header = (
        f"# BRIDGE Threat Feed\n"
        f"# Generated: {datetime.now().isoformat()}\n"
        f"# Total CIDRs: {len(all_cidrs)}\n"
    )
    for name, cnt in sources.items():
        header += f"# {name}: {cnt}\n"
    header += "#\n"

    with open(FEED_FILE, "w", encoding="utf-8") as f:
        f.write(header)
        for c in sorted(all_cidrs):
            f.write(c + "\n")
    _log(f"저장 완료: {FEED_FILE} ({len(all_cidrs)}개 CIDR)")


def check_ip(ip_str: str):
    if not FEED_FILE.exists():
        print("피드 파일 없음 — 먼저 sync 실행")
        sys.exit(1)
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        print(f"잘못된 IP: {ip_str}")
        sys.exit(1)
    with open(FEED_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                net = ipaddress.ip_network(line, strict=False)
                if ip in net:
                    print(f"[HIT] {ip_str} → {line}")
                    return
            except ValueError:
                continue
    print(f"[CLEAN] {ip_str} — 블록리스트에 없음")


def register_scheduled_task():
    python = sys.executable
    script = str(Path(__file__).resolve())
    r = subprocess.run([
        "schtasks", "/create",
        "/sc", "daily",
        "/st", "03:00",
        "/tn", "BRIDGE_ThreatFeed_Sync",
        "/tr", f'"{python}" "{script}" sync',
        "/rl", "limited",
        "/f",
    ], capture_output=True, text=True, creationflags=0x08000000)
    if r.returncode == 0:
        _log("Windows 스케줄러 등록 완료 (매일 03:00)")
    else:
        _log(f"등록 실패: {r.stderr}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1].lower()
    if cmd == "sync":
        sync_feeds()
    elif cmd == "check" and len(sys.argv) >= 3:
        check_ip(sys.argv[2])
    elif cmd == "register":
        register_scheduled_task()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
