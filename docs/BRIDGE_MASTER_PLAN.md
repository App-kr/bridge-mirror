# BRIDGE ENTERPRISE MASTER PLAN v3.0
> Generated: 2026-02-24 | Status: PRODUCTION | Protocol: MAO_V3.0

---

## 1. PROJECT OVERVIEW

| Item | Value |
|------|-------|
| Product | bridgejob.co.kr — Korean ESL Teacher Recruitment Platform |
| Owner | Private / Scarlett |
| Stack | FastAPI (Python) + Next.js 15 (TypeScript) + Supabase (PostgreSQL) |
| Root | `Q:\Claudework\bridge base\` |
| Frontend | `web_frontend/` → Next.js 15, Tailwind CSS, TypeScript |
| Backend | `api_server.py` → FastAPI, Uvicorn |
| Security | `security_vault.py` → AES-256-GCM field encryption |
| Pipeline | `auto_pipeline_v2.py` → master.db → Supabase |
| RPA | `craigslist_auto_rpa.py` → Selenium Chrome auto-posting |

---

## 2. CONFIRMED ARCHITECTURE DECISIONS

### 2.1 Database Architecture (Supabase / PostgreSQL)

#### candidates table — 42 Fields
```
id (UUID PK), full_name* [ENCRYPT], email* [ENCRYPT], nationality, ancestry,
dob, gender, current_location, marital_status, dependents, pets,
education, major, certification, e_visa, arc_holders, passport* [ENCRYPT],
criminal_record* [ENCRYPT], doc_status, start_date, area_prefs, target_age,
job_prefs, experience, reference, interview_time, current_salary, desired_salary,
housing, personal_considerations, religion* [ENCRYPT], health_info* [ENCRYPT],
criminal_record_check* [ENCRYPT], kakaotalk* [ENCRYPT], mobile_phone* [ENCRYPT],
how_to, file_urls, agreement, facts, admin_notes,
source, status, dedup_key, token_hash, token_expires_at, is_deleted,
created_at, updated_at
```

#### client_inquiries table — 43 Fields
```
id (UUID PK), contact_name* [ENCRYPT], contact_email* [ENCRYPT],
contact_position, phone* [ENCRYPT], business_registration* [ENCRYPT],
school_name (stored as school_name_kr), school_name_en, school_type,
school_location, hiring_history, native_count, vacancies,
working_hours, working_days, teaching_age, class_size, avg_lessons,
prep_time, contract_type, break_time, job_responsibilities,
monthly_salary (stored as salary_raw), housing_provided, housing_type,
housing_detail, paid_vacation, vacation_includes, travel_support,
meal_provided, meal_allowance, benefits, sick_leave,
preferred_candidate, start_date, memo_kr, memo_en,
privacy_policy, source, status, admin_notes, is_deleted,
created_at, updated_at
```

#### AES-256 Encrypted Fields
- candidates: full_name, email, mobile_phone, kakaotalk, passport,
  criminal_record, religion, health_info, criminal_record_check
- client_inquiries: contact_name, contact_email, phone, business_registration

#### RULES
- Zero physical DELETE: `is_deleted = TRUE` only (Soft Delete forever)
- All changes → AuditLog table (action, table, record_id, changed_by, old_val, new_val, ts)
- dedup_key: `lower(name_no_space)_birthyear_nationality`
- JWT magic link (HS256, 30-day TTL) → stored in localStorage as `bridge_apply_token`
- Source field: `'web_form'` | `'google_form'` (parallel operation, same schema)

### 2.2 Security — 5-Layer Architecture

```
Layer 1: Supabase DB Views (public_jobs, public_candidates)
         → Strip school_name, contact, phone, email, employer_id at DB level
         → Frontend anon key only reads these views

Layer 2: AES-256-GCM Field Encryption (security_vault.py)
         → encrypt_field(), decrypt_field(), is_encrypted()
         → BRIDGE_FIELD_KEY in .env

Layer 3: PIIMaskingMiddleware (api_server.py)
         → Redacts PII from all JSON responses via regex
         → Blocked keys: school_name, contact_name, phone, email, address
         → Korean phone regex: 010-\d{4}-\d{4}
         → Bypassed for /api/admin/ routes WITH valid X-Admin-Key

Layer 4: security_check() in craigslist_auto_rpa.py
         → Validates ad body before posting (phone, email, school name patterns)
         → redact_pii() masks any leakage in logs → [REDACTED_PII]

Layer 5: Admin RBAC
         → X-Admin-Key header (ADMIN_API_KEY env var)
         → Admin routes: /api/admin/candidates, /api/admin/inquiries, /api/admin/ad-posts
         → Rate limiting: 60 req/min public, 300 req/min admin
```

### 2.3 API Endpoints (api_server.py — FastAPI)

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| GET | /api/jobs | None | Public job list |
| GET | /api/jobs/{id} | None | Single job (safe fields only) |
| POST | /api/apply | None | Candidate application (42 fields) |
| POST | /api/inquiry | None | Employer inquiry (43 fields) |
| GET | /api/community/{board} | None | Community posts |
| POST | /api/community/{board} | None | New post |
| GET | /api/admin/candidates | Admin | Candidate grid (decrypted PII) |
| PATCH | /api/admin/candidates/{id} | Admin | Inline edit (status, notes) |
| DELETE | /api/admin/candidates/{id} | Admin | Soft delete |
| GET | /api/admin/ad-posts | Admin | Craigslist post log |

### 2.4 Frontend Design System (2026 Light Theme)

```
Colors:    White #ffffff / Black #111827 / Light Grey #f9fafb / Mid Grey #e5e7eb
Accent:    Blue #2563eb (CTAs ONLY — Apply, Submit, Search)
Fonts:     Inter (next/font/google) + Pretendard Variable (CDN)
Cards:     bg-white, rounded-2xl, border-gray-200, shadow-sm
Theme:     Light — NO dark mode
CSS File:  globals.css — classes: .btn-primary, .btn-secondary, .btn-ghost,
           .card, .card-flat, .badge, .badge-hot, .badge-pt, .badge-open,
           .badge-visa, .input, .select, .textarea, .label, .section-heading,
           .tog, .tog-on (toggle buttons), .trust-badge
```

### 2.5 Form Architecture (3-Step Wizard Modal)

#### Candidate Apply Form — 3 Steps
- Step 1 "Your Profile": how_to, name, email, phone, kakaotalk, nationality,
  ancestry, dob, gender, marital_status, dependents, pets, current_location
- Step 2 "Experience & Preferences": education, major, certification,
  e_visa, arc_holders, passport, criminal_record, doc_status,
  start_date, area_prefs, target_age, housing, interview_time,
  job_prefs, experience, reference, current_salary, desired_salary,
  personal_considerations, file_urls
- Step 3 "Sensitive & Agreement": religion, health_info, criminal_record_check,
  admin_notes, agreement ✓, facts ✓, [Submit + 🔒 AES-256 trust badge]

#### Employer Inquiry Form — 3 Steps
- Step 1 "Contact & School": email, contact_name, contact_position, phone,
  business_registration, school_name, school_name_en, school_location,
  hiring_history, vacancies, native_count
- Step 2 "Teaching Conditions": start_date, contract_type, teaching_age,
  working_days, schedule, working_hours, class_size, avg_lessons, prep_time,
  break_time, job_responsibilities, preferred_candidate, salary_raw,
  housing_type, housing_provided, housing_detail
- Step 3 "Benefits & Agreement": travel_support, paid_vacation, vacation_includes,
  sick_leave, meal_provided, meal_allowance, benefits, memo_kr, memo_en,
  privacy_policy ✓, [Submit + 🔒 AES-256 trust badge]

#### Quick Apply Slide Panel (jobs page)
- Same 3-step wizard embedded in fixed right-side panel (z-50)
- Width: max-w-2xl, Full height, overflow-y-auto
- Backdrop: bg-black/40, backdrop-blur-sm, z-40
- Animation: slideIn 0.28s ease-out (translateX 100% → 0)
- Pre-fills job.job_id in admin_notes

#### Payment Section (inquiry form ONLY)
- Bank Transfer: Large card (🏦, 국민은행 123-456-789012, 예금주: 브릿지 리크루트먼트)
- PayPal: Large card (bg-[#003087], PayPal SVG icon)
- ⛔ Credit card UI: PERMANENTLY OMITTED from DOM — never render

### 2.6 RPA Rules (craigslist_auto_rpa.py) — IMMUTABLE

| Rule | Value |
|------|-------|
| Platform | Craigslist Seoul |
| Category | Seoul > Jobs > Education (jo, value=102) |
| Processing | Sequential only — NO parallel posting |
| Title prefix | ◾◾◾◾ (4 squares — Unicode \u25fe × 4) |
| Image | B.png ONLY (`images/B.png`) — NOT B.jpg |
| Upload wait | `time.sleep(15)` after send_keys before done button click |
| Security | security_check() validates body pre-post, redact_pii() on all logs |
| Scheduler | Windows Task Scheduler: PT4H48M (288 min), `run_rpa.bat` |
| Desktop | bridge_desktop_agent.py (Tkinter) — manual trigger UI |

### 2.7 Data Flow

```
master.db (SQLite)
    → auto_pipeline_v2.py (ProcessPool: encrypt, ThreadPool: upsert)
    → Supabase candidates / client_inquiries / public_jobs (VIEW)

Web form (42/43 fields)
    → POST /api/apply or /api/inquiry
    → AES-256 encrypt PII fields
    → Supabase UPSERT (dedup_key or JWT token)
    → Return JWT token → localStorage

craigslist_auto_rpa.py
    → SELECT ad_posts from master.db (status='pending')
    → Selenium: login → fill form → attach B.png → sleep(15) → submit
    → UPDATE ad_posts SET status='posted', posted_url=...

Admin (/admin/candidates)
    → GET /api/admin/candidates (X-Admin-Key)
    → PIIMaskingMiddleware bypassed
    → _decrypt_row() decrypts all ENCRYPT fields
    → AG Grid v35 inline edit → PATCH /api/admin/candidates/{id}
```

---

## 3. MAO V3.0 PROTOCOL COMPLIANCE

### Implemented ✅
- AES-256-GCM field encryption (security_vault.py)
- Soft Delete universal (is_deleted flag, no physical DELETE)
- PII masking in all API responses ([REDACTED_PII] in logs)
- Admin RBAC (X-Admin-Key, PIIMaskingMiddleware bypass)
- craigslist security_check() pre-post validation
- PWA manifest + service worker (/sw.js)
- ISR (60s revalidate on homepage)
- 3-step wizard modal forms

### Pending / In Progress 🔄
- AuditLog table (Supabase: audit_log with action/table/record_id/old_val/new_val)
- React Query for admin dashboard (candidate grid real-time refresh)
- WebSocket for live job feed updates
- Rate limiting middleware (60 req/min public, 300 req/min admin)
- CSP headers (Content-Security-Policy via Next.js headers config)

---

## 4. ENVIRONMENT VARIABLES

```env
# Backend (.env)
BRIDGE_FIELD_KEY=<AES-256 key material>
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=<anon key>
SUPABASE_SERVICE_KEY=<service key — NEVER in frontend>
ADMIN_API_KEY=<admin secret>
JWT_SECRET=<same as BRIDGE_FIELD_KEY or separate>
CRAIGSLIST_EMAIL=<email>
CRAIGSLIST_PASSWORD=<password>
CRAIGSLIST_CITY=seoul

# Frontend (.env.local)
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key>
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_ADMIN_KEY=<admin secret — used by admin pages only>
```

---

## 5. FILE MAP

```
Q:\Claudework\bridge base\
├── api_server.py           ← FastAPI main (42+43 field models, JWT, admin endpoints)
├── security_vault.py       ← AES-256-GCM encrypt/decrypt
├── auto_pipeline_v2.py     ← master.db → Supabase pipeline
├── craigslist_auto_rpa.py  ← Selenium RPA (B.png, 4 squares, 15s sleep)
├── bridge_desktop_agent.py ← Tkinter control panel
├── run_rpa.bat             ← Scheduler wrapper
├── setup_scheduler.ps1     ← Windows Task Scheduler registration
├── master.db               ← SQLite (ad_posts, jobs source)
├── images/B.png            ← ONLY approved Craigslist attachment image
├── supabase_migration_full_schema.sql ← Full DB schema migration
├── BRIDGE_MASTER_PLAN.md   ← THIS FILE
└── web_frontend/
    ├── src/app/
    │   ├── globals.css     ← Design system (light theme, .tog, .trust-badge)
    │   ├── layout.tsx      ← Root layout (Inter + Pretendard, white nav)
    │   ├── page.tsx        ← Homepage (SSR, hero + search + hot jobs)
    │   ├── jobs/page.tsx   ← Job list + Quick Apply slide panel
    │   ├── apply/page.tsx  ← Candidate form (3-step wizard, 42 fields)
    │   ├── inquiry/page.tsx← Employer form (3-step wizard, 43 fields)
    │   ├── admin/page.tsx  ← Ad posts dashboard
    │   ├── admin/candidates/page.tsx ← AG Grid candidate management
    │   └── community/      ← Boards (general, visa)
    ├── src/components/
    │   ├── JobCard.tsx     ← Public job card (light theme, Quick Apply)
    │   ├── ApplyPanel.tsx  ← 3-step slide panel (jobs page)
    │   ├── MarkdownBody.tsx← Community post renderer
    │   └── NewPostForm.tsx ← Community new post
    └── src/lib/supabase.ts ← Supabase client (anon key ONLY)
```

---

## 6. ABSOLUTE RULES (ZERO-TOLERANCE)

1. ⛔ **NO physical DELETE** — `is_deleted = TRUE` always
2. ⛔ **NO service key in frontend** — anon key only in browser
3. ⛔ **NO credit card UI** — Bank Transfer + PayPal ONLY
4. ⛔ **B.jpg** → Must be **B.png** — immutable
5. ⛔ **◾◾◾** (3) → Must be **◾◾◾◾** (4) in all Craigslist titles — immutable
6. ⛔ **parallel posting** → Sequential ONLY in RPA
7. ✅ **15-second hard sleep** after image send_keys before done button
8. ✅ **AES-256 trust badge** on ALL form submit buttons
9. ✅ **[REDACTED_PII]** in all terminal logs and error outputs
10. ✅ **Soft Delete + AuditLog** on every admin PATCH/DELETE action
