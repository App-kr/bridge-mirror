import pandas as pd
import sqlite3
import os
from pathlib import Path

# 1. 경로 설정
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "master.db"
OUTPUT_FILE = BASE_DIR / "unified_bridge_data.xlsx"

def run_cleanup_robot():
    print("🚀 데이터 통합 로봇 가동 시작 (Scarlett 전용)...")
    
    # --- [섹션 A: 구인처 데이터 추출] ---
    jobs_df = pd.DataFrame()
    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        try:
            query = "SELECT name FROM sqlite_master WHERE type='table';"
            tables = pd.read_sql_query(query, conn)['name'].tolist()
            all_tables = [pd.read_sql_query(f"SELECT * FROM {table}", conn) for table in tables]
            # 비어있지 않은 데이터만 합치기 (FutureWarning 방지)
            all_tables = [df for df in all_tables if not df.empty]
            if all_tables:
                jobs_df = pd.concat(all_tables, ignore_index=True)
                print(f"✅ 구인처 데이터 {len(jobs_df)}건 추출 완료.")
        finally:
            conn.close()

    # --- [섹션 B: 구직자 데이터 통합] ---
    candidate_files = list(BASE_DIR.glob("*.csv")) + list(BASE_DIR.glob("*.xlsx"))
    all_cands = []
    
    for file in candidate_files:
        if file.name == OUTPUT_FILE.name or file.name == "data_unifier.py": continue
        try:
            print(f"📦 읽는 중: {file.name}")
            if file.suffix == '.csv':
                # 오류 수정: read_csv에는 'errors' 대신 'on_bad_lines' 사용
                df = pd.read_csv(file, encoding='utf-8-sig', on_bad_lines='skip')
            else:
                df = pd.read_excel(file)
            all_cands.append(df)
        except Exception as e:
            print(f"⚠️ {file.name} 읽기 실패: {e}")
    
    candidates_df = pd.DataFrame()
    if all_cands:
        candidates_df = pd.concat([df for df in all_cands if not df.empty], ignore_index=True)
        print(f"✅ 구직자 데이터 {len(candidates_df)}건 통합 완료.")

    # --- [섹션 C: 마스터 엑셀 저장] ---
    try:
        with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
            if not candidates_df.empty:
                candidates_df.to_excel(writer, sheet_name='Candidates_Master', index=False)
            if not jobs_df.empty:
                jobs_df.to_excel(writer, sheet_name='Jobs_Master', index=False)
        print(f"\n✨ 작업 완료! 최종 파일: {OUTPUT_FILE.name}")
        print("이 작업은 원본을 유지한 채 복사본만 생성했습니다.")
    except Exception as e:
        print(f"❌ 파일 저장 중 오류 발생: {e}")

if __name__ == "__main__":
    run_cleanup_robot()