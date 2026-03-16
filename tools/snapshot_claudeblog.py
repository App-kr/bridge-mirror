# -*- coding: utf-8 -*-
"""
ClaudeBlog 파일 스냅샷 백업
"""
import shutil
import os
from pathlib import Path
from datetime import datetime

SRC = Path("Q:/Claudework/ClaudeBlog")
DST_BASE = Path("Q:/Claudework/bridge base/backups")

ts = datetime.now().strftime("%Y%m%d_%H%M%S")
dst = DST_BASE / f"ClaudeBlog_{ts}"
dst.mkdir(parents=True, exist_ok=True)

# 백업 대상
targets = [
    SRC / "modules",
    SRC / "tests",
    SRC / "main.py",
    SRC / "config.json",
    SRC / "requirements.txt",
]

for t in targets:
    if t.is_dir():
        shutil.copytree(t, dst / t.name, dirs_exist_ok=True)
        print(f"[DIR]  {t.name}/ -> {dst.name}/")
    elif t.is_file():
        shutil.copy2(t, dst / t.name)
        print(f"[FILE] {t.name} -> {dst.name}/")
    else:
        print(f"[SKIP] {t.name} not found")

# 백업 파일 목록 출력 (RULE-0C: 반드시 목록 확인)
print(f"\n=== 백업 확인: {dst} ===")
for f in sorted(dst.rglob("*")):
    rel = f.relative_to(dst)
    if f.is_file():
        print(f"  {rel}  ({f.stat().st_size:,} bytes)")

print(f"\n[DONE] 백업 경로: {dst}")
