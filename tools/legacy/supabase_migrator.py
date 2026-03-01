"""
BRIDGE Supabase Migrator — Global ATS Standard Schema
========================================================
Schema modeled after LinkedIn / Indeed patterns.
Four core entities: candidates · jobs · employers · applications

Pipeline:
  1. Read  master.db  (SQLite)
  2. Cleanse & normalise every field
  3. Write  migration_plan.json  (dry-run review)
  4. Push   to Supabase via service-role key

Usage:
  python supabase_migrator.py --plan          # generate JSON plan only
  python supabase_migrator.py --schema        # print DDL to stdout
  python supabase_migrator.py --table cand    # push candidates only
  python supabase_migrator.py                 # full migration

env (.env):
  SUPABASE_URL=https://xxxx.supabase.co
  SUPABASE_SERVICE_KEY=eyJ...
"""

# ─────────────────────────────────────────────────────────────────────────────
# STDLIB
# ─────────────────────────────────────────────────────────────────────────────
import io
import json
import os
import re
import sqlite3
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────────────────────────────────────
# ENV
# ─────────────────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(Path("Q:/Claudework/bridge base/.env"))
except ImportError:
    pass

try:
    from supabase import create_client, Client as SBClient
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False

BASE_DIR = Path("Q:/Claudework/bridge base")
DB_PATH  = BASE_DIR / "master.db"
PLAN_OUT = BASE_DIR / "migration_plan.json"

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")
BATCH = 100

# ─────────────────────────────────────────────────────────────────────────────
# NEW GLOBAL ATS SCHEMA  (PostgreSQL / Supabase)
# ─────────────────────────────────────────────────────────────────────────────
NEW_SCHEMA_SQL = """
-- ================================================================
--  BRIDGE ATS — Global Standard Schema  (LinkedIn / Indeed model)
--  Run this in Supabase SQL Editor BEFORE executing the migrator.
-- ================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- helper: auto-update updated_at
CREATE OR REPLACE FUNCTION trg_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

-- ────────────────────────────────────────────────────────────────
-- 1. EMPLOYERS  (schools / academies — derived from client_inquiries)
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS employers (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    legacy_id        INTEGER     UNIQUE,            -- client_inquiries.id
    company_name     TEXT        NOT NULL,
    company_type     TEXT,                          -- 등록기관·사설학원·유치원 etc.
    email            TEXT,
    phone            TEXT,
    phone_normalized TEXT,
    contact_name     TEXT,
    location_full    TEXT,
    city             TEXT,
    district         TEXT,
    is_active        BOOLEAN     NOT NULL DEFAULT true,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_employers_company_name ON employers(company_name);
CREATE INDEX IF NOT EXISTS idx_employers_city         ON employers(city);

CREATE TRIGGER trg_employers_upd
BEFORE UPDATE ON employers
FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

-- ────────────────────────────────────────────────────────────────
-- 2. CANDIDATES
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS candidates (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    legacy_id            TEXT        UNIQUE,        -- SQLite candidate_id (cnd_...)
    -- Identity
    email                TEXT,
    full_name            TEXT        NOT NULL,
    first_name           TEXT,
    last_name            TEXT,
    nationality          TEXT,
    ancestry             TEXT,
    date_of_birth        TEXT,
    gender               TEXT,
    current_location     TEXT,
    -- Contact  (RLS-protected — anon cannot SELECT)
    phone_primary        TEXT,
    phone_kakao          TEXT,
    -- Visa & Legal
    visa_types           JSONB       NOT NULL DEFAULT '[]',
    visa_raw             TEXT,
    arc_eligible         BOOLEAN,
    arc_expiry           TEXT,
    criminal_record      TEXT,
    passport_country     TEXT,
    -- Work preferences
    availability_date    TEXT,
    preferred_age_groups JSONB       NOT NULL DEFAULT '[]',
    preferred_locations  JSONB       NOT NULL DEFAULT '[]',
    housing_needed       TEXT,
    -- Career
    experience_text      TEXT,
    experience_years     INTEGER,
    employment_history   TEXT,
    certifications       JSONB       NOT NULL DEFAULT '[]',
    -- Salary (KRW millions, e.g. 2.5 = ₩2,500,000)
    salary_current       NUMERIC(6,2),
    salary_desired_min   NUMERIC(6,2),
    salary_desired_max   NUMERIC(6,2),
    salary_raw           TEXT,
    -- Documents
    documents_status     JSONB       NOT NULL DEFAULT '{}',
    references_avail     TEXT,
    -- System
    status               TEXT        NOT NULL DEFAULT 'Active'
                         CHECK (status IN ('Active','Inactive','Placed','Blacklist')),
    source               TEXT        NOT NULL DEFAULT 'import',
    source_file          TEXT,
    tags                 JSONB       NOT NULL DEFAULT '[]',
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_cand_email        ON candidates(email);
CREATE INDEX IF NOT EXISTS idx_cand_nationality  ON candidates(nationality);
CREATE INDEX IF NOT EXISTS idx_cand_status       ON candidates(status);
CREATE INDEX IF NOT EXISTS idx_cand_visa_types   ON candidates USING GIN(visa_types);
CREATE INDEX IF NOT EXISTS idx_cand_created      ON candidates(created_at DESC);

CREATE TRIGGER trg_candidates_upd
BEFORE UPDATE ON candidates
FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

-- ────────────────────────────────────────────────────────────────
-- 3. JOBS
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS jobs (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    legacy_id            INTEGER     UNIQUE,        -- SQLite jobs.id
    employer_id          UUID        REFERENCES employers(id),
    job_code             TEXT        NOT NULL,
    seq                  INTEGER     NOT NULL DEFAULT 1,
    title                TEXT,                      -- generated
    -- Location
    city                 TEXT,
    district             TEXT,
    location_full        TEXT,
    -- Employment
    employment_type      TEXT        NOT NULL DEFAULT 'full_time'
                         CHECK (employment_type IN ('full_time','part_time','contract')),
    start_date           TEXT,
    teaching_age_groups  JSONB       NOT NULL DEFAULT '[]',
    class_size           TEXT,
    -- Schedule
    working_hours        TEXT,
    hours_per_day        NUMERIC(4,2),
    hours_per_week       TEXT,
    -- Salary
    salary_min           NUMERIC(6,2),
    salary_max           NUMERIC(6,2),
    salary_raw           TEXT,
    -- Benefits
    housing_provided     BOOLEAN     NOT NULL DEFAULT false,
    housing_detail       TEXT,
    vacation_days        TEXT,
    visa_sponsorship     BOOLEAN     NOT NULL DEFAULT true,
    benefits             JSONB       NOT NULL DEFAULT '[]',
    native_count         TEXT,
    -- Flags
    is_hot               BOOLEAN     NOT NULL DEFAULT false,
    -- Status
    status               TEXT        NOT NULL DEFAULT 'open'
                         CHECK (status IN ('open','filled','hold','cancelled')),
    internal_notes       TEXT,
    source_file          TEXT,
    published_at         TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (job_code, seq)
);
CREATE INDEX IF NOT EXISTS idx_jobs_city          ON jobs(city);
CREATE INDEX IF NOT EXISTS idx_jobs_is_hot        ON jobs(is_hot);
CREATE INDEX IF NOT EXISTS idx_jobs_status        ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_hours         ON jobs(hours_per_day);
CREATE INDEX IF NOT EXISTS idx_jobs_age_groups    ON jobs USING GIN(teaching_age_groups);

CREATE TRIGGER trg_jobs_upd
BEFORE UPDATE ON jobs
FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

-- ────────────────────────────────────────────────────────────────
-- 4. APPLICATIONS  (candidate ↔ job junction — ATS pipeline)
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS applications (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id    UUID        NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    job_id          UUID        NOT NULL REFERENCES jobs(id)       ON DELETE CASCADE,
    status          TEXT        NOT NULL DEFAULT 'applied'
                    CHECK (status IN
                      ('applied','reviewing','interview','offered',
                       'rejected','hired','withdrawn')),
    applied_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    notes           TEXT,
    recruiter_notes TEXT,
    UNIQUE (candidate_id, job_id)
);
CREATE INDEX IF NOT EXISTS idx_app_candidate ON applications(candidate_id);
CREATE INDEX IF NOT EXISTS idx_app_job       ON applications(job_id);
CREATE INDEX IF NOT EXISTS idx_app_status    ON applications(status);

CREATE TRIGGER trg_applications_upd
BEFORE UPDATE ON applications
FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

-- ────────────────────────────────────────────────────────────────
-- 5. SYSTEM_LOGS
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS system_logs (
    id          BIGSERIAL   PRIMARY KEY,
    event_type  TEXT        NOT NULL,
    entity_type TEXT,
    entity_id   TEXT,
    action      TEXT,
    message     TEXT,
    payload     JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ────────────────────────────────────────────────────────────────
-- RLS
-- ────────────────────────────────────────────────────────────────
ALTER TABLE employers    ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidates   ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs         ENABLE ROW LEVEL SECURITY;
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;

-- Public: open job listings
CREATE POLICY "anon_read_open_jobs"
ON jobs FOR SELECT TO anon USING (status = 'open');

-- Public: candidate web-form apply
CREATE POLICY "anon_insert_candidate"
ON candidates FOR INSERT TO anon WITH CHECK (source = 'web_form');

-- Public: employer web-form inquiry
CREATE POLICY "anon_insert_employer"
ON employers FOR INSERT TO anon WITH CHECK (true);

-- Authenticated (admin): full access
CREATE POLICY "admin_employers"    ON employers    FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "admin_candidates"   ON candidates   FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "admin_jobs"         ON jobs         FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "admin_applications" ON applications FOR ALL TO authenticated USING (true) WITH CHECK (true);
"""

# ─────────────────────────────────────────────────────────────────────────────
# DATA CLEANSING FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

_VISA_PATTERNS = [
    (r'\bE[-\s]?2\b',  'E-2'),
    (r'\bE[-\s]?1\b',  'E-1'),
    (r'\bF[-\s]?4\b',  'F-4'),
    (r'\bF[-\s]?5\b',  'F-5'),
    (r'\bF[-\s]?6\b',  'F-6'),
    (r'\bF[-\s]?2\b',  'F-2'),
    (r'\bH[-\s]?2\b',  'H-2'),
    (r'\bD[-\s]?10\b', 'D-10'),
    (r'\bD[-\s]?6\b',  'D-6'),
    (r'\bG[-\s]?1\b',  'G-1'),
    (r'\bC[-\s]?3\b',  'C-3'),
]

def extract_visa_types(e_visa: str, arc_holders: str) -> list[str]:
    combined = f"{e_visa or ''} {arc_holders or ''}"
    found: list[str] = []
    for pattern, label in _VISA_PATTERNS:
        if re.search(pattern, combined, re.IGNORECASE) and label not in found:
            found.append(label)
    # Text indicators for ARC / F-visa holders
    if re.search(r'\barc\b', combined, re.IGNORECASE) and not found:
        found.append('ARC')
    return found


def extract_arc_expiry(arc_text: str) -> Optional[str]:
    """Try to pull a YYYY.MM.DD or YYYY/MM/DD date from arc_holders."""
    if not arc_text:
        return None
    m = re.search(r'(20\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})', arc_text)
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
    m2 = re.search(r'(20\d{2})[.\-/](\d{1,2})', arc_text)
    if m2:
        return f"{m2.group(1)}-{m2.group(2).zfill(2)}"
    return None


def normalize_phone(raw: str) -> Optional[str]:
    """
    Korean-aware phone normaliser.
    010-1234-5678 → +82-10-1234-5678
    1012345678   → +82-10-1234-5678
    Others       → cleaned digits only
    """
    if not raw:
        return None
    digits = re.sub(r'[^\d]', '', raw)
    if not digits:
        return None
    # Korean mobile: starts 010 (11 digits) or 10 (10 digits, missing leading 0)
    if re.match(r'^010\d{8}$', digits):
        return f"+82-10-{digits[3:7]}-{digits[7:]}"
    if re.match(r'^10\d{8}$', digits):
        return f"+82-10-{digits[2:6]}-{digits[6:]}"
    # Korean landline: 02-XXXX-XXXX (area code 02) or 0XX-XXX-XXXX
    if re.match(r'^02\d{7,8}$', digits):
        return f"+82-2-{digits[2:]}"
    if re.match(r'^0[3-9]\d{8,9}$', digits):
        return f"+82-{digits[1:3]}-{digits[3:]}"
    # Overseas or unknown: return as-is
    return digits or None


def parse_salary(raw: str) -> tuple[Optional[float], Optional[float]]:
    """
    Handles:
      '2.5'          → (2.5, 2.5)
      '2,3'          → (2.3, 2.3)  [comma as decimal]
      '2.5-2.8'      → (2.5, 2.8)
      '2,50m KRW'    → (2.5, 2.5)
    Returns float pair (millions KRW).
    """
    if not raw:
        return None, None
    # strip currency/units
    clean = re.sub(r'[KRWkrwmM₩,]', '', raw).strip()
    # replace comma-decimal with dot
    clean = re.sub(r'(\d),(\d)', r'\1.\2', clean)
    # range: two numbers
    m = re.findall(r'\d+\.?\d*', clean)
    if len(m) >= 2:
        try:
            lo, hi = float(m[0]), float(m[1])
            # sanity: KRW millions are typically 1.8 – 6.0
            if lo < 1:
                lo, hi = lo * 10, hi * 10
            return round(lo, 2), round(hi, 2)
        except ValueError:
            pass
    if len(m) == 1:
        try:
            v = float(m[0])
            if v < 1:
                v *= 10
            return round(v, 2), round(v, 2)
        except ValueError:
            pass
    return None, None


def extract_experience_years(text: str) -> Optional[int]:
    """Try to extract years from experience text."""
    if not text:
        return None
    m = re.search(r'(\d+)\s*(?:year|yr|년|년도)', text, re.IGNORECASE)
    if m:
        y = int(m.group(1))
        return y if y < 50 else None
    return None


def parse_certifications(cert_text: str) -> list[str]:
    """Split multi-line or comma-separated certifications."""
    if not cert_text:
        return []
    parts = re.split(r'[\n,;]+', cert_text)
    return [p.strip() for p in parts if p.strip()]


def split_name(full_name: str) -> tuple[str, str]:
    """Best-effort first/last split for Western names."""
    parts = (full_name or "").strip().split()
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:])
    return full_name or "", ""


_AGE_MAP = {
    r'pre[-\s]?k': 'pre_k',
    r'toddler':    'pre_k',
    r'kindy|kindergarten': 'kindergarten',
    r'elem':       'elementary',
    r'middle':     'middle',
    r'high':       'high',
    r'adult':      'adult',
}

def parse_age_groups(text: str) -> list[str]:
    if not text:
        return []
    found: list[str] = []
    lower = text.lower()
    for pattern, label in _AGE_MAP.items():
        if re.search(pattern, lower) and label not in found:
            found.append(label)
    return found


def parse_benefits(text: str) -> list[str]:
    if not text:
        return []
    parts = re.split(r'[,;\n]+', text)
    return [p.strip() for p in parts if p.strip() and len(p.strip()) > 2]


def clean(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def as_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return bool(v)
    if isinstance(v, str):
        return v.lower() in ('1', 'true', 'yes')
    return False


# ─────────────────────────────────────────────────────────────────────────────
# READ  master.db
# ─────────────────────────────────────────────────────────────────────────────

def read_db() -> dict[str, list[dict]]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    data: dict[str, list[dict]] = {}

    for table in ["candidates", "jobs", "client_inquiries", "ad_posts"]:
        try:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            data[table] = [dict(r) for r in rows]
        except sqlite3.OperationalError:
            data[table] = []

    conn.close()
    return data


# ─────────────────────────────────────────────────────────────────────────────
# TRANSFORM  →  new schema records
# ─────────────────────────────────────────────────────────────────────────────

def transform_candidates(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        s_min, s_max = parse_salary(clean(r.get("desired_salary")) or "")
        s_cur, _     = parse_salary(clean(r.get("current_salary")) or "")
        first, last  = split_name(r.get("full_name", ""))
        visa_types   = extract_visa_types(
            r.get("e_visa", ""),
            r.get("arc_holders", "")
        )
        arc_expiry   = extract_arc_expiry(r.get("arc_holders", ""))
        phone_norm   = normalize_phone(r.get("mobile_phone", ""))
        certs        = parse_certifications(r.get("certification", ""))
        age_groups   = parse_age_groups(r.get("target", ""))   # 'target' = teaching age pref
        pref_locs    = parse_benefits(r.get("area_prefs", "")) # reuse parser

        status = r.get("status", "Active")
        if status not in ("Active","Inactive","Placed","Blacklist"):
            status = "Active"

        out.append({
            "legacy_id":            clean(r.get("candidate_id")),
            "email":                clean(r.get("email")),
            "full_name":            clean(r.get("full_name")) or "Unknown",
            "first_name":           first or None,
            "last_name":            last or None,
            "nationality":          clean(r.get("nationality")),
            "ancestry":             clean(r.get("ancestry")),
            "date_of_birth":        clean(r.get("dob")),
            "gender":               clean(r.get("gender")),
            "current_location":     clean(r.get("current_location")),
            "phone_primary":        phone_norm,
            "phone_kakao":          clean(r.get("kakaotalk")),
            "visa_types":           visa_types,
            "visa_raw":             clean(r.get("e_visa")),
            "arc_eligible":         bool(r.get("arc_holders")),
            "arc_expiry":           arc_expiry,
            "criminal_record":      clean(r.get("criminal_record")),
            "passport_country":     clean(r.get("passport")),
            "availability_date":    clean(r.get("start_date")),
            "preferred_age_groups": age_groups,
            "preferred_locations":  pref_locs,
            "housing_needed":       clean(r.get("housing")),
            "experience_text":      clean(r.get("experience")),
            "experience_years":     extract_experience_years(r.get("experience","")),
            "employment_history":   clean(r.get("employment")),
            "certifications":       certs,
            "salary_current":       s_cur,
            "salary_desired_min":   s_min,
            "salary_desired_max":   s_max,
            "salary_raw":           clean(r.get("desired_salary")),
            "documents_status":     {
                "documents":  bool(r.get("documents")),
                "reference":  bool(r.get("reference")),
                "passport":   bool(r.get("passport")),
                "criminal":   bool(r.get("criminal_record")),
            },
            "references_avail":     clean(r.get("reference")),
            "status":               status,
            "source":               "import",
            "source_file":          clean(r.get("source_file")),
            "tags":                 [],
            "created_at":           clean(r.get("created_at")) or NOW,
            "updated_at":           clean(r.get("updated_at")) or NOW,
        })
    return out


def transform_employers(rows: list[dict]) -> list[dict]:
    """client_inquiries → employers (dedup by school_name + email)."""
    seen: set[str] = set()
    out  = []
    for r in rows:
        school = clean(r.get("school_name")) or "Unknown"
        email  = clean(r.get("email")) or ""
        key    = f"{school.lower()}|{email.lower()}"
        if key in seen:
            continue
        seen.add(key)

        # Extract city from location free text
        location = clean(r.get("location")) or ""
        city_m   = re.search(r'(서울|인천|수원|부산|대구|대전|광주|울산|세종|경기|제주|Busan|Seoul|Incheon|Suwon)',
                              location, re.IGNORECASE)
        city     = city_m.group(1) if city_m else None

        # Company type heuristic
        raw_type = clean(r.get("source_file")) or ""
        if re.search(r'유치원|kindergarten|kindy', location + school, re.IGNORECASE):
            ctype = "유치원"
        elif re.search(r'어학원|학원|academy', location + school, re.IGNORECASE):
            ctype = "사설학원"
        elif re.search(r'등록|registered', raw_type, re.IGNORECASE):
            ctype = "등록기관"
        else:
            ctype = "기타"

        phone_raw  = clean(r.get("phone"))
        phone_norm = normalize_phone(phone_raw)

        out.append({
            "legacy_id":        int(r["id"]) if r.get("id") else None,
            "company_name":     school,
            "company_type":     ctype,
            "email":            clean(r.get("email")),
            "phone":            phone_raw,
            "phone_normalized": phone_norm,
            "contact_name":     clean(r.get("contact_name")),
            "location_full":    location,
            "city":             city,
            "district":         None,
            "is_active":        True,
            "created_at":       clean(r.get("loaded_at")) or NOW,
            "updated_at":       NOW,
        })
    return out


def transform_jobs(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        age_groups   = parse_age_groups(r.get("teaching_age", ""))
        benefits_lst = parse_benefits(r.get("benefits", ""))
        hours        = r.get("daily_hours")
        try:
            hours = float(hours) if hours is not None else None
        except (TypeError, ValueError):
            hours = None

        s_min = r.get("salary_min")
        s_max = r.get("salary_max")
        try:
            s_min = float(s_min) if s_min is not None else None
        except (TypeError, ValueError):
            s_min = None
        try:
            s_max = float(s_max) if s_max is not None else None
        except (TypeError, ValueError):
            s_max = None

        is_hot = (hours is not None and hours < 7.0)
        is_pt  = as_bool(r.get("is_part_time", False))

        age_label = r.get("teaching_age", "")
        city      = clean(r.get("city")) or "Korea"
        title     = f"{city} {age_label} Teacher".strip() if age_label else f"{city} English Teacher"

        housing_raw  = clean(r.get("housing")) or ""
        housing_bool = bool(re.search(r'provid|furnished|furnished|제공|지원', housing_raw, re.IGNORECASE))

        out.append({
            "legacy_id":           int(r["id"]) if r.get("id") else None,
            "employer_id":         None,          # linked manually post-migration
            "job_code":            clean(r.get("job_code")) or "UNKNOWN",
            "seq":                 int(r.get("seq", 1)),
            "title":               title,
            "city":                clean(r.get("city")),
            "district":            clean(r.get("district")),
            "location_full":       clean(r.get("location")),
            "employment_type":     "part_time" if is_pt else "full_time",
            "start_date":          clean(r.get("start_date")),
            "teaching_age_groups": age_groups,
            "class_size":          clean(r.get("class_size")),
            "working_hours":       clean(r.get("working_hours")),
            "hours_per_day":       hours,
            "hours_per_week":      clean(r.get("teach_hrs_week")),
            "salary_min":          s_min,
            "salary_max":          s_max,
            "salary_raw":          clean(r.get("salary_raw")),
            "housing_provided":    housing_bool,
            "housing_detail":      housing_raw or None,
            "vacation_days":       clean(r.get("vacation")),
            "visa_sponsorship":    True,
            "benefits":            benefits_lst,
            "native_count":        clean(r.get("native_count")),
            "is_hot":              is_hot,
            "status":              "open",
            "internal_notes":      clean(r.get("internal_notes")),
            "source_file":         clean(r.get("source_file")),
            "published_at":        clean(r.get("loaded_at")) or NOW,
            "created_at":          clean(r.get("loaded_at")) or NOW,
            "updated_at":          NOW,
        })
    return out


# ─────────────────────────────────────────────────────────────────────────────
# EXECUTION PLAN
# ─────────────────────────────────────────────────────────────────────────────

def generate_plan(
    candidates: list[dict],
    employers:  list[dict],
    jobs:       list[dict],
) -> dict:
    def stat(recs: list[dict], fields: list[str]) -> dict:
        filled = {f: sum(1 for r in recs if r.get(f)) for f in fields}
        pct    = {f: round(filled[f] / len(recs) * 100, 1) if recs else 0 for f in fields}
        return {"count": len(recs), "fill_rate": pct}

    visa_dist: dict[str, int] = {}
    for c in candidates:
        for v in (c.get("visa_types") or []):
            visa_dist[v] = visa_dist.get(v, 0) + 1

    nat_dist: dict[str, int] = {}
    for c in candidates:
        n = c.get("nationality") or "Unknown"
        nat_dist[n] = nat_dist.get(n, 0) + 1
    top_nat = sorted(nat_dist.items(), key=lambda x: x[1], reverse=True)[:10]

    city_dist: dict[str, int] = {}
    for j in jobs:
        c = j.get("city") or "Unknown"
        city_dist[c] = city_dist.get(c, 0) + 1
    top_cities = sorted(city_dist.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "generated_at": NOW,
        "source_db":    str(DB_PATH),
        "target":       SUPABASE_URL or "NOT_CONFIGURED",
        "tables": {
            "employers": stat(employers, ["company_name","email","phone","city"]),
            "candidates": stat(candidates, [
                "email","phone_primary","visa_types","experience_years",
                "salary_desired_min","certifications","preferred_locations"
            ]),
            "jobs": stat(jobs, [
                "title","city","hours_per_day","salary_min","teaching_age_groups",
                "housing_provided","benefits"
            ]),
            "applications": {"count": 0, "note": "Empty — no historical data"},
        },
        "insights": {
            "hot_jobs":          sum(1 for j in jobs if j.get("is_hot")),
            "part_time_jobs":    sum(1 for j in jobs if j.get("employment_type") == "part_time"),
            "visa_distribution": visa_dist,
            "top_nationalities": dict(top_nat),
            "top_job_cities":    dict(top_cities),
            "candidates_with_visa": sum(1 for c in candidates if c.get("visa_types")),
            "candidates_placed":    sum(1 for c in candidates if c.get("status") == "Placed"),
            "housing_offered_jobs": sum(1 for j in jobs if j.get("housing_provided")),
        },
        "warnings": _collect_warnings(candidates, jobs),
    }


def _collect_warnings(candidates: list[dict], jobs: list[dict]) -> list[str]:
    w = []
    no_email = sum(1 for c in candidates if not c.get("email"))
    no_phone = sum(1 for c in candidates if not c.get("phone_primary"))
    if no_email > 100:
        w.append(f"{no_email} candidates have no email — web-form outreach unavailable")
    if no_phone > 500:
        w.append(f"{no_phone} candidates have no normalised phone number")
    dup_jobs = len(jobs) - len({(j["job_code"], j["seq"]) for j in jobs})
    if dup_jobs:
        w.append(f"{dup_jobs} duplicate (job_code, seq) pairs found — last write wins")
    return w


# ─────────────────────────────────────────────────────────────────────────────
# SUPABASE UPLOAD
# ─────────────────────────────────────────────────────────────────────────────

def _upsert(client: "SBClient", table: str, rows: list[dict], conflict_col: str) -> int:
    total = 0
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        try:
            client.table(table).upsert(chunk, on_conflict=conflict_col).execute()
            total += len(chunk)
            pct = int(total / len(rows) * 100)
            print(f"  [{table:16s}] {total:>5}/{len(rows)} ({pct:3d}%)", end="\r")
        except Exception as exc:
            print(f"\n  [WARN] {table} batch {i}–{i+BATCH}: {exc}")
    print()
    return total


def push(client: "SBClient", table_filter: str,
         employers_r: list[dict], candidates_r: list[dict], jobs_r: list[dict]) -> dict[str, int]:
    results: dict[str, int] = {}
    run_all = table_filter == "all"

    if run_all or table_filter in ("employers", "empl"):
        print(f"\n→ employers ({len(employers_r):,}건)")
        results["employers"] = _upsert(client, "employers", employers_r, "legacy_id")

    if run_all or table_filter in ("candidates", "cand"):
        print(f"\n→ candidates ({len(candidates_r):,}건)")
        results["candidates"] = _upsert(client, "candidates", candidates_r, "legacy_id")

    if run_all or table_filter in ("jobs",):
        print(f"\n→ jobs ({len(jobs_r):,}건)")
        results["jobs"] = _upsert(client, "jobs", jobs_r, "legacy_id")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="BRIDGE Global ATS Supabase Migrator")
    parser.add_argument("--plan",   action="store_true", help="JSON 실행 계획만 생성 (업로드 안 함)")
    parser.add_argument("--schema", action="store_true", help="새 DDL을 stdout에 출력")
    parser.add_argument("--table",  default="all",
                        choices=["all","candidates","cand","jobs","employers","empl"],
                        help="특정 테이블만 이관")
    args = parser.parse_args()

    if args.schema:
        print(NEW_SCHEMA_SQL)
        return

    print("=" * 60)
    print("  BRIDGE  →  Supabase  Global ATS Migrator")
    print(f"  Source : {DB_PATH}")
    print(f"  Target : {SUPABASE_URL[:45] + '...' if SUPABASE_URL else 'NOT SET'}")
    print("=" * 60)

    # 1. Read
    print("\n[1/4] master.db 읽는 중...")
    raw = read_db()
    print(f"  candidates     : {len(raw['candidates']):,}")
    print(f"  jobs           : {len(raw['jobs']):,}")
    print(f"  client_inquiries: {len(raw['client_inquiries']):,}")

    # 2. Transform
    print("\n[2/4] 데이터 변환 및 정규화...")
    employers_r  = transform_employers(raw["client_inquiries"])
    candidates_r = transform_candidates(raw["candidates"])
    jobs_r       = transform_jobs(raw["jobs"])
    print(f"  employers  : {len(employers_r):,}")
    print(f"  candidates : {len(candidates_r):,}")
    print(f"  jobs       : {len(jobs_r):,}")

    # 3. Plan
    print("\n[3/4] 실행 계획 생성...")
    plan = generate_plan(candidates_r, employers_r, jobs_r)
    PLAN_OUT.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  → {PLAN_OUT}")
    print(f"  HOT 포지션       : {plan['insights']['hot_jobs']}")
    print(f"  비자 소지 구직자  : {plan['insights']['candidates_with_visa']}")
    print(f"  경고             : {len(plan['warnings'])}")
    for w in plan["warnings"]:
        print(f"    ⚠  {w}")

    if args.plan:
        print("\n--plan 모드: 업로드 생략. migration_plan.json 확인 후 재실행하세요.")
        return

    # 4. Push
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("\n[ERROR] .env 에 SUPABASE_URL / SUPABASE_SERVICE_KEY 를 입력하세요.")
        print("  --plan 플래그로 먼저 계획을 검토하세요.")
        sys.exit(1)

    if not HAS_SUPABASE:
        print("[ERROR] pip install supabase")
        sys.exit(1)

    print("\n[4/4] Supabase 업로드...")
    client  = create_client(SUPABASE_URL, SUPABASE_KEY)
    results = push(client, args.table, employers_r, candidates_r, jobs_r)

    total = sum(results.values())
    print("\n" + "=" * 60)
    print(f"  완료: 총 {total:,}건 업로드")
    for t, n in results.items():
        print(f"    {t:16s}: {n:,}건")
    print("=" * 60)


if __name__ == "__main__":
    main()
