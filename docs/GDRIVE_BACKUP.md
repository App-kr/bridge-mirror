# BRIDGE Google Drive 자동 백업 시스템 — Claude Code 투입용

> FULL_STABILIZATION.md 다운로드 후 아래 폴더에 넣으세요:
> Q:\Claudework\bridge base\docs\sprints\
>
> 그다음 Claude Code에 아래 명령어를 붙여넣으면 자동실행됩니다:
> cat "Q:\Claudework\bridge base\docs\sprints\GDRIVE_BACKUP.md" 읽고 순서대로 작업해줘

---

## ██ 0. 백업 ██

```bash
cd "Q:\Claudework\bridge base"
git add -A && git commit -m "backup: pre-gdrive-backup-system"
```

---

## ██ 1. 사전 확인 ██

```bash
# Google Service Account 이미 있는지
ls "Q:\Claudework\.vault\google_service_account.json" 2>/dev/null && echo "SA키 있음" || echo "SA키 없음"

# 기존 sheet_sync.py에서 SA 사용 여부
grep -n "service_account\|ServiceAccount\|from_service_account" tools/sheet_sync.py 2>/dev/null | head -5

# google 관련 패키지
pip list 2>/dev/null | grep -i "google\|oauth\|api-python"

# 현재 백업 디렉토리
ls "Q:\Claudework\backups\" 2>/dev/null
```

**결과 보고 후 진행. SA키 이미 있으면 그대로 재사용.**

**중요**: 아래 파일 위치 탐색도 실행하여 실제 경로 파악:

```bash
echo "═══ 파일 위치 탐색 ═══"

echo "--- 원본 이력서/커버레터 ---"
for d in "tools/processed_docs/originals" "tools/processed_docs/incoming" "tools/resume_converter/input" "uploads"; do
  if [ -d "$d" ]; then
    cnt=$(find "$d" -type f | wc -l)
    echo "  $d: ${cnt}개 파일"
  else
    echo "  $d: 없음"
  fi
done

echo "--- 변환 이력서 ---"
for d in "tools/processed_docs/processed" "tools/resume_converter/output"; do
  if [ -d "$d" ]; then
    cnt=$(find "$d" -name "*.pdf" | wc -l)
    echo "  $d: ${cnt}개 PDF"
  else
    echo "  $d: 없음"
  fi
done

echo "--- 영상 파일 ---"
find . -maxdepth 4 \( -name "*.mp4" -o -name "*.mov" -o -name "*.avi" -o -name "*.webm" \) 2>/dev/null | head -10

echo "--- 구인자 문서 ---"
for d in "tools/employer_docs" "employer_data"; do
  if [ -d "$d" ]; then
    cnt=$(find "$d" -type f | wc -l)
    echo "  $d: ${cnt}개 파일"
  else
    echo "  $d: 없음"
  fi
done

echo "--- 전체 디스크 사용량 ---"
du -sh tools/processed_docs/ 2>/dev/null
du -sh tools/resume_converter/ 2>/dev/null
du -sh uploads/ 2>/dev/null
```

**탐색 결과를 기반으로 gdrive_backup.py의 경로 목록(RESUME_DIRS, ORIGINAL_DIRS, VIDEO_DIRS, EMPLOYER_DIRS)을 실제 존재하는 경로로 수정할 것. 없는 디렉토리는 제거하지 말고 유지 (향후 생성 시 자동 감지).**

---

## ██ 2. Google Drive 백업 유틸 생성 ██

파일: `tools/gdrive_backup.py`

```python
"""
BRIDGE Google Drive 자동 백업 시스템

백업 대상:
  1. master.db (SQLite DB) — 매일 (구직자+구인자 전체 데이터)
  2. 원본 이력서/커버레터 (지원자 제출 원본) — 신규분만
  3. 변환된 이력서 PDF (PII 제거본) — 신규분만
  4. 영상 파일 (mp4/mov 등 인트로 영상) — 신규분만
  5. 구인자(업체) 관련 문서 — 신규분만
  6. .env 제외한 설정 파일 — 주 1회

백업 위치:
  Google Drive → BRIDGE_Backups/ 폴더 (자동 생성)
  ├── db/              ← master.db 일별 덤프 (구직자+구인자 DB 전체)
  ├── originals/        ← 원본 이력서/커버레터 (제출 그대로)
  ├── resumes/          ← 변환 이력서 PDF (PII 제거본)
  ├── videos/           ← 인트로 영상 (mp4/mov)
  ├── employers/        ← 구인자 관련 문서
  └── config/           ← 설정 파일 스냅샷

사용법:
  # 전체 백업
  python tools/gdrive_backup.py --all

  # DB만
  python tools/gdrive_backup.py --db

  # 이력서만 (신규분)
  python tools/gdrive_backup.py --resumes

  # 설정만
  python tools/gdrive_backup.py --config

환경:
  SA 키: Q:\\Claudework\\.vault\\google_service_account.json
  또는 환경변수 GOOGLE_SERVICE_ACCOUNT_JSON (JSON 문자열)
"""
import os
import sys
import json
import glob
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from io import BytesIO

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("bridge.backup")

# ─── 경로 ────────────────────────────────────
BASE_DIR = Path("Q:/Claudework/bridge base")
DB_PATH = BASE_DIR / "master.db"
SA_KEY_PATH = Path("Q:/Claudework/.vault/google_service_account.json")
BACKUP_RECORD = BASE_DIR / "tools" / ".gdrive_backup_state.json"

RESUME_DIRS = [
    BASE_DIR / "tools" / "processed_docs" / "processed",
    BASE_DIR / "tools" / "resume_converter" / "output",
]

ORIGINAL_DIRS = [
    BASE_DIR / "tools" / "processed_docs" / "originals",
    BASE_DIR / "tools" / "processed_docs" / "incoming",
    BASE_DIR / "tools" / "resume_converter" / "input",
    BASE_DIR / "uploads",
]

VIDEO_DIRS = [
    BASE_DIR / "tools" / "processed_docs" / "originals",
    BASE_DIR / "tools" / "processed_docs" / "incoming",
    BASE_DIR / "uploads",
]
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".webm", ".mkv"}

EMPLOYER_DIRS = [
    BASE_DIR / "tools" / "employer_docs",
    BASE_DIR / "employer_data",
]

CONFIG_FILES = [
    "render.yaml",
    "CLAUDE.md",
    "requirements.txt",
    "package.json",
]

DRIVE_FOLDER_NAME = "BRIDGE_Backups"


# ─── Google Drive 서비스 ─────────────────────
def _get_drive_service():
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        # SA 키 로드 (파일 우선, 환경변수 폴백)
        if SA_KEY_PATH.exists():
            creds = Credentials.from_service_account_file(
                str(SA_KEY_PATH),
                scopes=["https://www.googleapis.com/auth/drive.file"]
            )
        elif os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"):
            sa_info = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))
            creds = Credentials.from_service_account_info(
                sa_info,
                scopes=["https://www.googleapis.com/auth/drive.file"]
            )
        else:
            logger.error("Google SA 키 없음 — 백업 불가")
            return None

        return build("drive", "v3", credentials=creds, cache_discovery=False)
    except ImportError:
        logger.error("google-api-python-client 미설치: pip install google-api-python-client google-auth")
        return None
    except Exception as e:
        logger.error(f"Drive 서비스 생성 실패: {e}")
        return None


# ─── 폴더 관리 ───────────────────────────────
def _find_or_create_folder(service, name, parent_id=None):
    """Drive에서 폴더 찾기, 없으면 생성"""
    q = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        q += f" and '{parent_id}' in parents"

    results = service.files().list(q=q, spaces="drive", fields="files(id,name)").execute()
    files = results.get("files", [])

    if files:
        return files[0]["id"]

    # 생성
    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        meta["parents"] = [parent_id]

    folder = service.files().create(body=meta, fields="id").execute()
    logger.info(f"폴더 생성: {name} → {folder['id']}")
    return folder["id"]


def _get_backup_folders(service):
    """BRIDGE_Backups/ 하위 폴더 ID 반환"""
    root_id = _find_or_create_folder(service, DRIVE_FOLDER_NAME)
    db_id = _find_or_create_folder(service, "db", root_id)
    originals_id = _find_or_create_folder(service, "originals", root_id)
    resume_id = _find_or_create_folder(service, "resumes", root_id)
    video_id = _find_or_create_folder(service, "videos", root_id)
    employer_id = _find_or_create_folder(service, "employers", root_id)
    config_id = _find_or_create_folder(service, "config", root_id)
    return {
        "root": root_id, "db": db_id, "originals": originals_id,
        "resumes": resume_id, "videos": video_id,
        "employers": employer_id, "config": config_id,
    }


# ─── 파일 업로드 ─────────────────────────────
def _upload_file(service, local_path, folder_id, drive_filename=None):
    """파일을 Drive에 업로드. 동일 이름 있으면 스킵."""
    from googleapiclient.http import MediaFileUpload

    fname = drive_filename or os.path.basename(local_path)

    # 중복 체크
    q = f"name='{fname}' and '{folder_id}' in parents and trashed=false"
    existing = service.files().list(q=q, fields="files(id)").execute().get("files", [])
    if existing:
        logger.info(f"  스킵 (이미 존재): {fname}")
        return existing[0]["id"]

    meta = {"name": fname, "parents": [folder_id]}
    media = MediaFileUpload(str(local_path), resumable=True)
    file = service.files().create(body=meta, media_body=media, fields="id").execute()
    logger.info(f"  업로드: {fname} → {file['id']}")
    return file["id"]


# ─── 백업 상태 관리 ──────────────────────────
def _load_state():
    if BACKUP_RECORD.exists():
        return json.loads(BACKUP_RECORD.read_text(encoding="utf-8"))
    return {"uploaded_resumes": [], "last_db_backup": "", "last_config_backup": ""}


def _save_state(state):
    BACKUP_RECORD.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


# ─── 백업 함수들 ─────────────────────────────
def backup_db(service, folders):
    """master.db → Drive db/ 폴더에 날짜별 업로드"""
    if not DB_PATH.exists():
        logger.warning("master.db 없음")
        return

    today = datetime.now().strftime("%Y%m%d")
    dump_name = f"master_{today}.db"

    # 로컬에 임시 복사 (WAL 모드 안전)
    import shutil
    tmp = BASE_DIR / "tools" / f".tmp_backup_{today}.db"
    shutil.copy2(str(DB_PATH), str(tmp))

    try:
        _upload_file(service, tmp, folders["db"], dump_name)
    finally:
        tmp.unlink(missing_ok=True)

    # 30일 이전 Drive 백업 삭제
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    q = f"'{folders['db']}' in parents and trashed=false"
    old_files = service.files().list(q=q, fields="files(id,name)").execute().get("files", [])
    for f in old_files:
        try:
            date_part = f["name"].replace("master_", "").replace(".db", "")
            if date_part < cutoff:
                service.files().delete(fileId=f["id"]).execute()
                logger.info(f"  삭제 (30일 경과): {f['name']}")
        except:
            pass

    logger.info(f"DB 백업 완료: {dump_name}")


def backup_resumes(service, folders):
    """변환 이력서 PDF → Drive resumes/ 폴더에 신규분만 업로드"""
    state = _load_state()
    uploaded = set(state.get("uploaded_resumes", []))
    new_count = 0

    for d in RESUME_DIRS:
        if not d.exists():
            continue
        for pdf in d.glob("*.pdf"):
            fname = pdf.name
            if fname in uploaded:
                continue
            try:
                _upload_file(service, pdf, folders["resumes"], fname)
                uploaded.add(fname)
                new_count += 1
            except Exception as e:
                logger.warning(f"  실패: {fname} — {e}")

    state["uploaded_resumes"] = list(uploaded)
    _save_state(state)
    logger.info(f"변환 이력서 백업 완료: 신규 {new_count}건, 총 {len(uploaded)}건")


def backup_originals(service, folders):
    """원본 이력서/커버레터 → Drive originals/ (신규분만, 영상 제외)"""
    state = _load_state()
    uploaded = set(state.get("uploaded_originals", []))
    new_count = 0

    for d in ORIGINAL_DIRS:
        if not d.exists():
            continue
        for f in d.iterdir():
            if not f.is_file():
                continue
            if f.suffix.lower() in VIDEO_EXTS:
                continue  # 영상은 별도 함수
            if f.name.startswith("."):
                continue
            if f.name in uploaded:
                continue
            try:
                _upload_file(service, f, folders["originals"], f.name)
                uploaded.add(f.name)
                new_count += 1
            except Exception as e:
                logger.warning(f"  실패: {f.name} — {e}")

    state["uploaded_originals"] = list(uploaded)
    _save_state(state)
    logger.info(f"원본 이력서 백업 완료: 신규 {new_count}건, 총 {len(uploaded)}건")


def backup_videos(service, folders):
    """영상 파일 → Drive videos/ (신규분만)"""
    state = _load_state()
    uploaded = set(state.get("uploaded_videos", []))
    new_count = 0

    for d in VIDEO_DIRS:
        if not d.exists():
            continue
        for f in d.iterdir():
            if not f.is_file():
                continue
            if f.suffix.lower() not in VIDEO_EXTS:
                continue
            if f.name in uploaded:
                continue
            try:
                _upload_file(service, f, folders["videos"], f.name)
                uploaded.add(f.name)
                new_count += 1
            except Exception as e:
                logger.warning(f"  실패: {f.name} — {e}")

    state["uploaded_videos"] = list(uploaded)
    _save_state(state)
    logger.info(f"영상 백업 완료: 신규 {new_count}건, 총 {len(uploaded)}건")


def backup_employers(service, folders):
    """구인자 관련 문서 → Drive employers/ (신규분만)"""
    state = _load_state()
    uploaded = set(state.get("uploaded_employers", []))
    new_count = 0

    for d in EMPLOYER_DIRS:
        if not d.exists():
            continue
        for f in d.rglob("*"):
            if not f.is_file() or f.name.startswith("."):
                continue
            # 상대경로를 키로 사용 (하위폴더 구분)
            rel = str(f.relative_to(d)).replace("\\", "/")
            if rel in uploaded:
                continue
            try:
                _upload_file(service, f, folders["employers"], f.name)
                uploaded.add(rel)
                new_count += 1
            except Exception as e:
                logger.warning(f"  실패: {rel} — {e}")

    state["uploaded_employers"] = list(uploaded)
    _save_state(state)
    logger.info(f"구인자 문서 백업 완료: 신규 {new_count}건, 총 {len(uploaded)}건")


def backup_config(service, folders):
    """설정 파일 → Drive config/ 폴더에 날짜 접두어로 업로드"""
    today = datetime.now().strftime("%Y%m%d")

    for fname in CONFIG_FILES:
        fpath = BASE_DIR / fname
        if not fpath.exists():
            continue
        drive_name = f"{today}_{fname}"
        try:
            _upload_file(service, fpath, folders["config"], drive_name)
        except Exception as e:
            logger.warning(f"  실패: {fname} — {e}")

    logger.info("설정 백업 완료")


# ─── 오래된 Drive 파일 정리 ──────────────────
def cleanup_old_backups(service, folders, keep_days=30):
    """30일 이전 DB 백업만 삭제 (이력서/설정은 영구 보관)"""
    cutoff = (datetime.now() - timedelta(days=keep_days)).strftime("%Y%m%d")

    q = f"'{folders['db']}' in parents and trashed=false"
    files = service.files().list(q=q, fields="files(id,name)").execute().get("files", [])
    deleted = 0
    for f in files:
        try:
            date_part = f["name"].replace("master_", "").replace(".db", "")[:8]
            if date_part < cutoff:
                service.files().delete(fileId=f["id"]).execute()
                deleted += 1
        except:
            pass

    if deleted:
        logger.info(f"정리: {deleted}건 삭제 (DB {keep_days}일 초과)")


# ─── 메인 ────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="BRIDGE Google Drive 백업")
    parser.add_argument("--all", action="store_true", help="전체 백업")
    parser.add_argument("--db", action="store_true", help="DB만")
    parser.add_argument("--originals", action="store_true", help="원본 이력서만")
    parser.add_argument("--resumes", action="store_true", help="변환 이력서만")
    parser.add_argument("--videos", action="store_true", help="영상만")
    parser.add_argument("--employers", action="store_true", help="구인자 문서만")
    parser.add_argument("--config", action="store_true", help="설정만")
    args = parser.parse_args()

    if not any([args.all, args.db, args.originals, args.resumes,
                args.videos, args.employers, args.config]):
        args.all = True

    service = _get_drive_service()
    if not service:
        logger.error("Drive 서비스 연결 실패 — 종료")
        sys.exit(1)

    folders = _get_backup_folders(service)
    logger.info(f"Drive 폴더: {DRIVE_FOLDER_NAME}/ (root={folders['root'][:8]}...)")

    if args.all or args.db:
        backup_db(service, folders)

    if args.all or args.originals:
        backup_originals(service, folders)

    if args.all or args.resumes:
        backup_resumes(service, folders)

    if args.all or args.videos:
        backup_videos(service, folders)

    if args.all or args.employers:
        backup_employers(service, folders)

    if args.all or args.config:
        backup_config(service, folders)

    cleanup_old_backups(service, folders)
    logger.info("═══ 백업 완료 ═══")


if __name__ == "__main__":
    main()
```

---

## ██ 3. 자동 실행 (Task Scheduler) ██

파일: `tools/run_gdrive_backup.bat`

```bat
@echo off
REM BRIDGE Google Drive 자동 백업 — 매일 02:00 실행
cd /d "Q:\Claudework\bridge base"
"Q:\Phtyon 3\python.exe" -X utf8 tools/gdrive_backup.py --all >> "Q:\Claudework\backups\gdrive_backup.log" 2>&1
```

Task Scheduler 등록:

```bash
# Windows Task Scheduler에 등록
schtasks /create /tn "BRIDGE_GDrive_Backup" /tr "Q:\Claudework\bridge base\tools\run_gdrive_backup.bat" /sc daily /st 02:00 /f

# 등록 확인
schtasks /query /tn "BRIDGE_GDrive_Backup"
```

---

## ██ 4. Render DB 백업도 Drive로 통합 ██

기존 `tools/render_db_backup.py`를 수정하여 Drive 업로드 추가:

```
기존 render_db_backup.py를 찾아서,
로컬 저장 후 Drive에도 업로드하는 로직 추가:

# 기존 코드 유지 (로컬 저장)
# 아래 추가:
try:
    from gdrive_backup import _get_drive_service, _get_backup_folders, _upload_file
    service = _get_drive_service()
    if service:
        folders = _get_backup_folders(service)
        _upload_file(service, str(out), folders["db"], f"render_{out.name}")
        print(f"  Drive 업로드 완료")
except Exception as e:
    print(f"  Drive 업로드 스킵: {e}")
```

---

## ██ 5. .gitignore 추가 ██

```bash
# 백업 상태 파일 + 임시 파일
grep -q "gdrive_backup_state" .gitignore || echo -e "\n# Backup state\ntools/.gdrive_backup_state.json\n.tmp_backup_*" >> .gitignore
```

---

## ██ 6. 검증 + 커밋 ██

```bash
# 문법
python -m py_compile tools/gdrive_backup.py && echo "gdrive OK"

# 테스트 실행 (DB만)
python tools/gdrive_backup.py --db

# 결과 확인: Drive에 BRIDGE_Backups/db/ 폴더 생성됐는지
# → 성공 시 "DB 백업 완료: master_YYYYMMDD.db" 출력

# Task Scheduler 확인
schtasks /query /tn "BRIDGE_GDrive_Backup" 2>/dev/null

# 커밋
git add tools/gdrive_backup.py tools/run_gdrive_backup.bat .gitignore
git commit -m "feat: Google Drive 자동 백업 — DB/이력서/설정 + Task Scheduler 매일 02:00"
```

---

## ██ 보안 체크 ██

| 항목 | 상태 |
|------|------|
| SA 키 | ✅ .vault/ 저장, .gitignore 차단 |
| Drive 권한 | ✅ drive.file 스코프만 (Drive 전체 접근 아님) |
| DB 덤프 내용 | ✅ PII 필드 암호화 상태 그대로 백업 |
| 이력서 PDF | ✅ PII 제거된 변환본만 (원본 아님) |
| 백업 보존 | ✅ DB 30일 자동 정리, 이력서/설정 영구 |
| .env 제외 | ✅ CONFIG_FILES에 .env 미포함 |
| 로그 | ✅ 로컬 로그만, Drive에 로그 업로드 안 함 |

---

## ██ 사전 준비 (SA 키 없는 경우) ██

SA 키가 이미 있으면 이 단계 스킵.
없으면:

```
1. Google Cloud Console → 프로젝트 선택 (기존 bridge-sheet-sync 프로젝트)
2. APIs & Services → Google Drive API 활성화
3. Service Accounts → 기존 SA 선택 → Keys → Add Key → JSON
4. 다운로드된 JSON → Q:\Claudework\.vault\google_service_account.json
5. Google Drive (브라우저) → BRIDGE_Backups 폴더 수동 생성
   → 폴더 우클릭 → 공유 → SA 이메일 추가 (편집자 권한)
```

SA 이메일 확인:
```bash
python -c "
import json
sa = json.load(open('Q:/Claudework/.vault/google_service_account.json'))
print(f'SA 이메일: {sa[\"client_email\"]}')
print('→ 이 이메일을 Drive 폴더에 편집자로 초대')
"
```

---

## ██ 용량 관리 ██

```
Google 무료 15GB 기준:
  master.db (~50MB) × 30일 = ~1.5GB
  원본 이력서 (~500KB) × 3,000건 = ~1.5GB
  변환 이력서 (~200KB) × 3,000건 = ~600MB
  영상 (~5MB) × 200건 = ~1GB
  구인자 문서 = ~200MB
  설정 파일 = 무시 수준

  총 예상: ~4.8GB / 15GB = 32% 사용

  계정 2개면 30GB — 수년간 충분
  영상이 많으면 별도 계정 분리 권장:
    계정1: DB + 이력서 + 설정
    계정2: 영상 + 대용량 파일
```
