import pandas as pd
from pathlib import Path
import os

# 현재 스크립트 위치에서 주변을 샅샅이 뒤집니다.
BASE_DIR = Path(__file__).parent

def find_excel_in_folder(folder_name):
    """지정한 폴더명 내부나 하위 폴더에서 'new'가 포함된 엑셀을 최우선으로 찾습니다."""
    # 현재 위치 및 한 단계 하위 폴더까지 모두 검색
    search_paths = [
        BASE_DIR / folder_name,
        BASE_DIR / "bridge base" / folder_name
    ]
    
    for path in search_paths:
        if path.exists():
            # 'new' 혹은 'New'가 들어간 엑셀 우선 검색
            files = list(path.rglob("*new*.xlsx")) + list(path.rglob("*New*.xlsx")) + list(path.rglob("*.xlsx"))
            # 임시 파일(~$ 시작) 제외
            valid_files = [f for f in files if not f.name.startswith('~$')]
            if valid_files:
                return valid_files[0]
    return None

def run_bridge_engine():
    print("🚀 Bridge Base 데이터 정밀 엔진 가동 (심층 탐색 모드)...")

    # 1. 구직자 데이터 (New 시트 우선)
    cand_file = find_excel_in_folder("original_candidates")
    if cand_file:
        try:
            print(f"📂 발견된 구직자 파일: {cand_file}")
            df_c = pd.read_excel(cand_file)
            print(f"✅ 구직자 데이터 {len(df_c)}행 로드 성공!")
        except Exception as e:
            print(f"⚠️ 구직자 읽기 실패: {e}")
    else:
        print("❌ 'original_candidates' 폴더나 파일을 찾을 수 없습니다.")

    # 2. 구인자 데이터 (설문지 + 과거DB)
    job_file = find_excel_in_folder("original_jobs")
    if job_file:
        try:
            print(f"📂 발견된 구인자 파일: {job_file}")
            df_j = pd.read_excel(job_file)
            print(f"✅ 구인자 데이터 {len(df_j)}행 로드 성공!")
        except Exception as e:
            print(f"⚠️ 구인자 읽기 실패: {e}")
    else:
        print("❌ 'original_jobs' 폴더나 파일을 찾을 수 없습니다.")

if __name__ == "__main__":
    run_bridge_engine()