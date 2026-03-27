#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q 드라이브에서 완전 암호화 마스터 키 프로그램 찾기"""

import os
from pathlib import Path

def search_q_drive():
    print("\n" + "="*70)
    print("  🔍 Q드라이브 전체 검색 - 암호화 마스터 키 프로그램")
    print("="*70 + "\n")

    q_root = Path("Q:/")

    if not q_root.exists():
        print("❌ Q 드라이브에 접근할 수 없습니다.\n")
        return

    # 검색할 파일명 패턴
    search_patterns = [
        "마스터",
        "실행기",
        "encrypt",
        "master_key",
        "vault",
        "암호화",
        "main.py",
    ]

    found_files = []

    print("[검색중...]")

    try:
        for root, dirs, files in os.walk(q_root, topdown=True):
            # 깊이 제한 (너무 깊으면 타임아웃)
            if root.count(os.sep) - q_root.as_posix().count(os.sep) > 5:
                dirs[:] = []
                continue

            for file in files:
                for pattern in search_patterns:
                    if pattern.lower() in file.lower():
                        full_path = Path(root) / file
                        found_files.append(full_path)
                        print(f"  ✓ {full_path}")
                        break

    except Exception as e:
        print(f"⚠ 검색 중 오류: {e}")

    # 마스터렌더키관리 폴더 특별 검색
    print("\n[마스터렌더키관리 폴더 직접 확인]")
    master_dir = Path("Q:/마스터렌더키관리")

    if master_dir.exists():
        print(f"✓ 폴더 발견: {master_dir}")
        try:
            for item in master_dir.rglob("*"):
                if item.is_file():
                    print(f"  📄 {item.name} - {item}")
        except Exception as e:
            print(f"  ⚠ 폴더 읽기 오류: {e}")
    else:
        print(f"❌ 폴더를 찾을 수 없음: {master_dir}")

    print("\n" + "="*70)
    if found_files:
        print(f"✅ 발견된 파일: {len(found_files)}개")
    else:
        print("⚠ 찾을 수 없습니다.")
    print("="*70 + "\n")

if __name__ == "__main__":
    search_q_drive()
