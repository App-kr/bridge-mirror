import openpyxl, sqlite3, hashlib, datetime, sys, os
sys.stdout.reconfigure(encoding="utf-8")

BASE = "Q:/Claudework/bridge base"
CAND_XLSX = BASE + "/original_candidates/CANDIDATES_MASTER_COMBINED.xlsx"
JOBS_XLSX = BASE + "/original_jobs/JOBS_MASTER_COMBINED.xlsx"
DB_PATH   = BASE + "/master.db"
LOG_PATH  = BASE + "/tasks/import_report_full.txt"

lines = []
def p(msg):
    print(msg)
    lines.append(msg)

# 1. PRE checksum + backup
conn = sqlite3.connect(DB_PATH)
h = hashlib.sha256(chr(10).join(conn.iterdump()).encode()).hexdigest()
conn.close()
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
with open(BASE + "/tasks/db_checksum.log", "a") as lf:
    lf.write(datetime.datetime.now().isoformat() + " PRE-FULL-IMPORT " + h + chr(10))
import shutil
shutil.copy(DB_PATH, DB_PATH + ".backup_" + ts)
p("PRE checksum: " + h[:16] + "... | backup: master.db.backup_" + ts)

# 2. CANDIDATES IMPORT
p(chr(10) + "=== CANDIDATES_MASTER_COMBINED.xlsx -> candidates table ===")

wb = openpyxl.load_workbook(CAND_XLSX, read_only=True, data_only=True)
sh = wb['Sheet1']

COL_MAP = {
    16: "preferences",
    18: "notice",
    19: "applied",
    22: "interview_time",
    24: "major",
    33: "religion",
    39: "consent",
    43: "placed_company",
    44: "placed_salary",
    45: "start_month",
    46: "housing_detail",
    47: "referral_fee",
    51: "visa_type",
    53: "education_level",
    54: "health_info",
    57: "tattoo",
    58: "piercings",
    59: "married",
    60: "korean_criminal_record",
    61: "documents_passport",
    64: "notes",
}

def cv(v):
    if v is None: return None
    s = str(v).strip()
    return s if s and s not in ("None", "nan") else None
