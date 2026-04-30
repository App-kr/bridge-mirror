"""jobs_clean.txt 의 잡코드만 jobs_clean.json 에 남김.
사용자가 .txt 편집해서 잡 지운 경우 → .json 동기화.
"""
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

base = Path(__file__).resolve().parent
txt = base / "jobs_clean.txt"
js  = base / "jobs_clean.json"

# 1. .txt 의 unique Job 번호 추출
codes_in_txt = set()
for m in re.finditer(r'Job\.\s*(\d+)', txt.read_text(encoding="utf-8")):
    codes_in_txt.add(m.group(1))
print(f".txt unique Job 번호: {len(codes_in_txt)}건")

# 2. .json 로드
data = json.loads(js.read_text(encoding="utf-8"))
before = len(data["jobs"])

# 3. 잡코드 정규화 후 매칭
def _norm(jc):
    return re.sub(r"[^0-9]", "", str(jc))

filtered = [j for j in data["jobs"] if _norm(j.get("job_code", "")) in codes_in_txt]
removed = before - len(filtered)
print(f".json 원래: {before}건 → 필터 후: {len(filtered)}건 (제거 {removed}건)")

# 4. 백업 + 저장
ts = datetime.now().strftime("%Y%m%d_%H%M")
js_bak = base / f"jobs_clean.json.bak_{ts}"
shutil.copy(str(js), str(js_bak))
print(f".json 백업: {js_bak.name}")

data["jobs"] = filtered
data["count"] = len(filtered)
data["generated_at"] = datetime.now().isoformat(timespec="seconds")
js.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f".json 갱신 완료: {len(filtered)}건")

# 5. K드라이브 백업
k_dir = Path(f"K:/Bridge_RPA_Backup/data_sync_{ts}")
k_dir.mkdir(parents=True, exist_ok=True)
shutil.copy(str(txt), str(k_dir / "jobs_clean.txt"))
shutil.copy(str(js), str(k_dir / "jobs_clean.json"))
shutil.copy(str(js_bak), str(k_dir / js_bak.name))
print(f"K 백업: {k_dir}")
