# BRIDGE 자동화 연동 가이드
> 마지막 업데이트: 2026-03-23 세션 9
> 위치: `Q:\Claudework\bridge base\docs\AUTOMATION_GUIDE.md`

---

## 안정성 현황

| 항목 | 상태 | 비고 |
|------|------|------|
| Git | CLEAN | `main` remote 동기화 완료 |
| DB | OK | candidates=3059, jobs=1072, file_uploads=0 (대기) |
| file_uploads 테이블 | READY | CREATE 완료, 기록 대기 |
| processed_docs 폴더 | READY | incoming/processed/originals/logs 4개 생성됨 |
| doc_run.bat | OK | 원클릭 런처 확인 |
| Cookie Secure | DEPLOYED | SameSite=Strict + Secure (localhost 예외) |
| SEO metadata | DEPLOYED | about/apply/inquiry/jobs 4페이지 |
| securityGuard | FIXED | API_URL → Render 서버 연결 |
| og-image.png | MISSING | 1200x630 PNG 필요 (SNS 공유용) |
| sql.js | UNUSED | 제거 가능 (1.4MB 절약) |

---

## 자동화 도구 한눈에 보기

```
doc_run.bat        ← 이력서 PII 제거 (원클릭)
auto_finalize.py   ← Canvas+백업+doc처리+커밋 (원클릭)
bridge_backup.py   ← 작업 전 백업 (Claude 자동)
secure_backup.py   ← AES-256 암호화 백업
bx.py              ← API키/비밀번호 관리 (DPAPI)
```

---

## STEP 1: 이력서 PII 제거 (doc_processor)

### 사용법 A — 파일 드롭 (가장 쉬움)

```
1. 이력서 파일(.docx/.pdf)을 여기에 복사:
   Q:\Claudework\bridge base\tools\processed_docs\incoming\

2. doc_run.bat 더블클릭 후 "batch" 입력
   또는 cmd에서:
   doc_run batch

3. 결과 확인:
   processed/  ← PII 제거된 파일
   originals/  ← 원본 백업
   logs/       ← 처리 로그
```

### 사용법 B — 단일 파일 직접 처리

```cmd
doc_run process "이력서.docx" -n 3057
```
- `-n 3057` = 강사번호 (자동 넘버링)

### 사용법 C — S3에서 다운로드 + 자동 처리

```cmd
doc_run download 3057
```
- S3에서 해당 번호 파일 자동 검색 → 다운로드 → PII 제거

### 사용법 D — 후보자 번호 조회

```cmd
doc_run lookup "Kim"
```

### 명령어 요약

| 명령 | 설명 |
|------|------|
| `doc_run setup` | 폴더 상태 확인 |
| `doc_run batch` | incoming/ 전체 처리 |
| `doc_run batch --dry` | 미리보기만 (처리 안함) |
| `doc_run process FILE -n NUM` | 단일 파일 |
| `doc_run download NUM` | S3 다운로드+처리 |
| `doc_run lookup NAME` | 후보자 검색 |
| `doc_run init-db` | file_uploads 테이블 재생성 |

---

## STEP 2: 작업 마무리 자동화 (auto_finalize)

```cmd
"D:\Phtyon 3\python.exe" -X utf8 "Q:\Claudework\bridge base\tools\auto_finalize.py" "작업명"
```

### 자동 실행 순서:
```
1. Canvas 새로고침 (refresh_canvas)
2. 백업 (bridge_backup.py)
3. incoming/ 이력서 자동 처리 (doc_processor batch) ← 신규
4. git add + commit + push
5. 작업일지 기록 (Obsidian)
```

- incoming/ 에 파일이 없으면 3단계는 자동 스킵

---

## STEP 3: 보안 키 관리 (bx.py)

```cmd
"D:\Phtyon 3\python.exe" -X utf8 "Q:\Claudework\bridge base\tools\bx.py"
```

### 등록된 키 목록:
| 키 | 용도 |
|----|------|
| AWS_ACCESS_KEY_ID | S3 파일 접근 |
| AWS_SECRET_ACCESS_KEY | S3 인증 |
| AWS_S3_BUCKET | 버킷 이름 |
| ADMIN_API_KEY | 관리자 API 인증 |
| BRIDGE_KEY | 암호화 마스터키 |

### 키 추가/수정:
```cmd
bx set KEY_NAME "value"
bx get KEY_NAME
bx list
```

---

## STEP 4: 암호화 백업 (secure_backup)

```cmd
"D:\Phtyon 3\python.exe" -X utf8 "Q:\Claudework\bridge base\tools\secure_backup.py" backup
"D:\Phtyon 3\python.exe" -X utf8 "Q:\Claudework\bridge base\tools\secure_backup.py" restore
```
- AES-256-GCM 암호화
- master.db + .env + .bridge.key 자동 포함

---

## STEP 5: 블로그 자동화 (ClaudeBlog)

```cmd
:: 테스트 (Gemini 0회 호출)
"Q:/Claudework/ClaudeBlog/.venv/Scripts/python.exe" -X utf8 "Q:/Claudework/ClaudeBlog/main.py" --dry

:: 실행 (하루 1회만!)
"Q:/Claudework/ClaudeBlog/.venv/Scripts/python.exe" -X utf8 "Q:/Claudework/ClaudeBlog/main.py" --now

:: 승인된 초안 발행 (Gemini 0회)
"Q:/Claudework/ClaudeBlog/.venv/Scripts/python.exe" -X utf8 "Q:/Claudework/ClaudeBlog/main.py" --publish-approved
```

---

## 즉시 해야 할 것 (우선순위순)

### 1순위 — 지금 바로
- [ ] **og-image.png 만들기**: 1200x630 PNG → `web_frontend/public/og-image.png`
  - 내용: BRIDGE 로고 + "ESL Teaching Jobs in Korea" + 현수교 이미지
  - 없으면 SNS 공유 시 썸네일 깨짐

### 2순위 — 번들 최적화
- [ ] **sql.js 제거** (1.4MB 절약):
  ```cmd
  cd Q:\Claudework\bridge base\web_frontend
  npm uninstall sql.js @types/sql.js
  ```

### 3순위 — 필요시
- [ ] `.github/workflows` push (PAT workflow scope 필요)
- [ ] CSV/Excel 내보내기 기능

---

## 폴더 맵

```
Q:\Claudework\bridge base\
├── tools\
│   ├── doc_processor.py    ← 이력서 PII 제거 v2.2
│   ├── doc_run.bat          ← 원클릭 런처
│   ├── auto_finalize.py     ← 작업 마무리 자동화
│   ├── bridge_backup.py     ← 작업 전 백업
│   ├── secure_backup.py     ← AES-256 암호화 백업
│   ├── bx.py                ← 보안 키 관리 (DPAPI)
│   └── processed_docs\
│       ├── incoming\        ← 여기에 파일 넣기
│       ├── processed\       ← PII 제거된 결과
│       ├── originals\       ← 원본 백업
│       └── logs\            ← 처리 로그
├── master.db                ← 메인 DB (절대 이동 금지)
├── .bridge.key              ← 암호화 키
├── backups\                 ← 자동 백업 저장소
└── docs\
    ├── AUTOMATION_GUIDE.md  ← 이 파일
    ├── AI_CONTEXT.md        ← AI 온보딩 문서
    └── AI_SECURITY_DESIGN.md
```
