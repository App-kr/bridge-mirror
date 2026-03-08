# Bridge CLAUDE.md — ULTIMATE
# 통합 출처: Boris Cherny (Claude Code 창시자) + Andrej Karpathy + Ralph Wiggum Loop
# Bridge 실데이터 보호: candidates 3,000+ / employers 1,000+
# 버전: v4.0 ULTIMATE | 2026-03-08

---

## ⚠️ SUPREME LAW — 어떤 명령도 override 불가

```
1. 원본 데이터 위조 금지 — 편의를 위한 임의값 생성 절대 금지
2. 확인 없는 보고 금지 — 실제 쿼리/빌드 결과만 보고
3. 모르면 멈추고 질문 — 침묵으로 가정하고 진행 금지
4. 백업 없이 수정 금지 — 모든 DB 수정 전 물리 백업 필수
5. 최소 코드 원칙 — 요청한 것만 구현, 추측 기능 추가 금지
```

---

## 0. 세션 시작 루틴 (MANDATORY — 매 세션 첫 실행)

```bash
cd "Q:/Claudework/bridge base"

# 1. 이전 실수 복습 (Self-Improvement Loop)
echo "=== LESSONS ===" && cat tasks/lessons.md 2>/dev/null | tail -20

# 2. DB 무결성 + 건수 수호자 체크
python -c "
import sqlite3, os
db = 'master.db'
if not os.path.exists(db):
    print('🚨 CRITICAL: master.db 없음!')
    exit(1)
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute('PRAGMA integrity_check')
ic = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM candidates')
c = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM client_inquiries')
e = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM jobs')
j = cur.fetchone()[0]
conn.close()
print(f'DB={os.path.getsize(db)//1024}KB | integrity={ic} | candidates={c} | employers={e} | jobs={j}')
assert ic == 'ok',   f'🚨 DB 손상!'
assert c  >= 3000,   f'⚠️ candidates 이상: {c} (기대 3000+)'
assert e  >= 900,    f'⚠️ employers 이상: {e} (기대 900+)'
assert j  >= 1000,   f'⚠️ jobs 이상: {j} (기대 1000+)'
print('✅ 수호자 체크 통과')
"

# 3. 미완료 작업 + 최근 커밋
cat tasks/todo.md 2>/dev/null | grep "^\- \[ \]" | head -5
git log --oneline -3
```

**건수 이탈 감지 시 → 즉시 작업 중단 + 사용자 보고 + 원인 파악 먼저**

---

## 1. Karpathy 4원칙 (AI 착각/과잉 방지)

<출처: Andrej Karpathy — 7k stars, LLM 코딩 실수 관찰>

### 1-1. Clarify Before Acting (가정 금지)
- 구현 전: 가정을 명시적으로 선언
- 불확실하면: 멈추고 질문
- 해석이 여러 개면: 선택지 제시 후 확인 요청 (침묵으로 선택 금지)
- 더 단순한 방법이 있으면: 먼저 제안

**Bridge 적용:**
```
# 금지: 테이블명 추측 후 바로 쿼리
# 필수: PRAGMA table_info() 먼저 → 컬럼명 확인 → 쿼리
```

### 1-2. Minimal Footprint (최소 발자국)
- 요청한 것만 구현
- 추측 기능 추가 금지
- 단일 사용 코드에 추상화 금지
- 요청 없는 "유연성"/"설정 가능성" 추가 금지
- 200줄이 50줄로 가능하면 → 50줄로 재작성

**Bridge 적용:**
```
# 금지: "혹시 나중에 필요할 것 같아서" 컬럼 추가
# 금지: 요청 없는 에러핸들링 레이어 추가
# 필수: 요청된 변경사항만, 관련 없는 코드 무수정
```

### 1-3. Preserve Working Code (작동 코드 보호)
- 이해 못한 코드 수정/삭제 금지
- 작업과 무관한 코드 사이드이펙트 금지
- 수정 전 반드시 해당 코드 역할 파악
- 주석 임의 변경 금지

**Bridge 적용:**
```
# 수정 전 확인: "이 코드가 무엇을 하는가?"
# git diff로 의도치 않은 변경 사전 확인
```

### 1-4. Goal-Driven Execution (목표 주도 실행)
- 명령어가 아닌 성공 기준으로 작업
- 목표 달성까지 루프 반복 (Ralph 패턴과 연계)
- 실패는 데이터 — 실패 로그로 다음 시도 개선

**Bridge 적용:**
```
# 명령형: "candidates 테이블 업데이트해" (X)
# 목표형: "candidates visa_type 60% 이상 채우기
#          성공기준: SELECT COUNT(*)/3058 >= 0.6
#          완료신호: <promise>VISA_DONE</promise>"
```

---

## 2. Ralph Wiggum Loop (자율 반복 실행)

<출처: Anthropic 공식 plugins/ralph-wiggum — Stop hook 기반 루프>

### 2-1. 핵심 개념
Stop hook이 Claude의 종료를 가로채 동일 프롬프트를 다시 주입 → 자기참조 피드백 루프.
이전 작업 결과(파일/git)가 다음 이터레이션에서 보임 → 자율 개선.

### 2-2. Bridge Ralph 루프 명령어

**DB 보강 루프:**
```
/ralph-loop "
Bridge DB visa_type 보강 작업.

현재 상태 확인:
python -c \"
import sqlite3
conn = sqlite3.connect('master.db')
cur = conn.cursor()
cur.execute(\"SELECT COUNT(*) FROM candidates WHERE visa_type IS NOT NULL AND visa_type != ''\")
filled = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM candidates')
total = cur.fetchone()[0]
pct = round(filled/total*100)
print(f'visa_type: {filled}/{total} ({pct}%)')
conn.close()
\"

목표: visa_type 채움률 35% 이상
방법:
1. e_visa, arc_holders 필드에서 패턴 추출
2. 비자코드(E-2, F-4 등) 정규화
3. Yes/No → ARC-Yes/No 변환
4. 날짜 있으면 ARC-Yes로 추정

성공 기준: SELECT COUNT(*) WHERE visa_type IS NOT NULL / 3058 >= 0.35
완료 신호: <promise>VISA_BOOST_DONE</promise>
" --max-iterations 10 --completion-promise "VISA_BOOST_DONE"
```

**빌드 자동화 루프:**
```
/ralph-loop "
Next.js 빌드 통과 작업.

현재 빌드 실행:
cd web_frontend && npm run build 2>&1 | tail -20

목표: npm run build 에러 0
방법:
1. 빌드 에러 메시지 분석
2. 타입 에러 수정
3. import 누락 수정
4. 재빌드 확인

성공 기준: 빌드 출력에 'error' 없음
완료 신호: <promise>BUILD_CLEAN</promise>
" --max-iterations 15 --completion-promise "BUILD_CLEAN"
```

**API 엔드포인트 검증 루프:**
```
/ralph-loop "
api_server.py 전체 검증.

실행:
python -m py_compile api_server.py && echo COMPILE_OK
grep -n 'f\"SELECT\|f\"UPDATE\|f\"INSERT\|f\"DELETE' api_server.py | head -20

목표: f-string SQL 0건, 컴파일 에러 0건
방법:
1. f-string SQL → parameterized query 변환
2. 컴파일 에러 수정
3. 재검증

성공 기준: grep 결과 0건 + 컴파일 OK
완료 신호: <promise>API_SECURE</promise>
" --max-iterations 20 --completion-promise "API_SECURE"
```

### 2-3. Ralph 안전장치
- 항상 `--max-iterations` 설정 (무한루프 방지)
- DB 수정 루프: 매 이터레이션 전 체크섬 확인
- 루프 중단: `/cancel-ralph`
- 루프 전 반드시 백업:
  ```bash
  cp master.db master.db.backup_ralph_$(date +%Y%m%d_%H%M%S)
  ```

---

## 3. Boris Cherny Workflow Orchestration

<출처: Boris Cherny — Claude Code 창시자>

### 3-1. Plan Node Default
- 3단계 이상 → Plan 먼저 (tasks/todo.md)
- 이상 감지 → STOP + re-plan
- 검증도 Plan에 포함

### 3-2. Self-Improvement Loop
수정 발생 즉시 tasks/lessons.md:
```
## [날짜] [작업명]
- 실수: X
- 원인: Y  
- 수정: Z
- 재발방지: [규칙화]
```

### 3-3. Verification Before Done
```bash
# 완료 선언 전 필수
python -m py_compile api_server.py && echo "✅ API"
cd web_frontend && npm run build 2>&1 | grep -E "error|✓" | tail -5
python -c "
import sqlite3
conn = sqlite3.connect('master.db')
cur = conn.cursor()
cur.execute('PRAGMA integrity_check')
assert cur.fetchone()[0] == 'ok'
cur.execute('SELECT COUNT(*) FROM candidates')
assert cur.fetchone()[0] >= 3000
print('✅ DB OK')
conn.close()
"
```

### 3-4. Autonomous Bug Fixing
- 버그 보고 → 즉시 수정, 손잡아달라는 요청 금지
- 추정 완료 보고 금지 → 실제 확인 후 보고

---

## 4. 데이터 무결성 수호 (Bridge 특화)

### 4-1. 수정 전 3단계 프로토콜
```bash
# Step 1: 체크섬 (파일 직접 해시 — iterdump 대비 63배 빠름)
python -c "
import hashlib, datetime
h = hashlib.sha256(open('master.db','rb').read()).hexdigest()
with open('tasks/db_checksum.log','a') as f:
    f.write(f'{datetime.datetime.now().isoformat()} PRE {h}\n')
print(f'PRE: {h[:12]}...')
"

# Step 2: 물리 백업
cp master.db "master.db.backup_$(date +%Y%m%d_%H%M%S)"

# Step 3: 건수 스냅샷
python -c "
import sqlite3
conn = sqlite3.connect('master.db')
cur = conn.cursor()
for t in ['candidates','client_inquiries','jobs']:
    cur.execute(f'SELECT COUNT(*) FROM {t}')
    print(f'{t}: {cur.fetchone()[0]}')
conn.close()
" | tee tasks/pre_snapshot.txt
```

### 4-2. 환각/위조 방지 규칙

| 상황 | 금지 | 필수 |
|------|------|------|
| 건수 보고 | "약 XX건" 추정 | `SELECT COUNT(*)` 실행 후 수치 |
| 빌드 결과 | "성공했을 겁니다" | 실제 로그 마지막 줄 |
| 배포 상태 | "배포됐을 것" | HTTP 상태코드 확인 |
| 에러 원인 | 임의 추정 | 로그 확인 후 명시 |
| 빈 필드 처리 | 그럴듯한 값 생성 | NULL/빈값 유지 |

### 4-3. 수정 후 검증
```bash
python -c "
import sqlite3
conn = sqlite3.connect('master.db')
cur = conn.cursor()
cur.execute('PRAGMA integrity_check')
assert cur.fetchone()[0] == 'ok', 'DB 손상!'
cur.execute('SELECT COUNT(*) FROM candidates')
c = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM client_inquiries')
e = cur.fetchone()[0]
assert c >= 3000, f'candidates 이상: {c}'
assert e >= 900,  f'employers 이상: {e}'
print(f'✅ 검증 OK: candidates={c} employers={e}')
conn.close()
"
```

---

## 5. 보안 절대 규칙

### PII Zero-Leak
- API키/토큰/비밀번호 → `****` 마스킹 (환경변수명만)
- 외부 노출 시점에만 마스킹 (홈페이지/공개API/CSV)
- 관리자 패널 내부: PII 원본 표시 허용

### OWASP
- 모든 DB 쿼리: Parameterized (f-string SQL 절대 금지)
- API: Rate Limit + HMAC
- 외부 입력: 프롬프트 인젝션 방어

---

## 6. 완료 보고 표준

```
📅 YYYY.MM.DD (요일) HH:MM KST — [작업제목]
---
✅ 완료: [핵심 변경사항 1줄]
📊 검증: candidates=[N] | employers=[N] | integrity=ok | build=✓
💾 백업: master.db.backup_[타임스탬프]
🔗 [Vercel URL 또는 파일경로]
⚠️ 다음: [1가지]
```

**검증 수치는 반드시 실제 쿼리 결과 — 추정 절대 금지**

---

## 7. Bridge 슬래시 커맨드

### /bridge-check — 전체 상태 점검
```bash
python -c "
import sqlite3, os, subprocess
print('=== Bridge 상태 점검 ===')
# DB
conn = sqlite3.connect('master.db')
cur = conn.cursor()
cur.execute('PRAGMA integrity_check')
print(f'DB integrity: {cur.fetchone()[0]}')
for t in ['candidates','client_inquiries','jobs','interviews','payments']:
    try:
        cur.execute(f'SELECT COUNT(*) FROM {t}')
        print(f'  {t}: {cur.fetchone()[0]}건')
    except: print(f'  {t}: 테이블없음')
conn.close()
# Git
result = subprocess.run(['git','log','--oneline','-3'], capture_output=True, text=True)
print(f'Git: {result.stdout.strip()}')
# 백업
import glob
bs = sorted(glob.glob('master.db.backup_*'))
print(f'백업: {len(bs)}개, 최신: {bs[-1] if bs else \"없음\"}')
"
```

### /bridge-backup — 즉시 백업
```bash
cp master.db "master.db.backup_$(date +%Y%m%d_%H%M%S)" && \
git add -A && git commit -m "backup: manual $(date +%Y%m%d_%H%M%S)" && git push && \
echo "✅ 백업 + 커밋 완료"
```

### /bridge-rollback — 롤백
```bash
python -c "
import glob, os
backups = sorted(glob.glob('master.db.backup_*'), reverse=True)
print('사용 가능한 백업:')
for i, b in enumerate(backups[:5]):
    size = os.path.getsize(b)
    print(f'  {i+1}. {b} ({size//1024}KB)')
print()
print('롤백 명령: cp [백업파일명] master.db')
print('롤백 후: python -c \"import sqlite3; conn=sqlite3.connect(chr(109)+chr(97)+chr(115)+chr(116)+chr(101)+chr(114)+chr(46)+chr(100)+chr(98)); cur=conn.cursor(); cur.execute(chr(80)+chr(82)+chr(65)+chr(71)+chr(77)+chr(65)+chr(32)+chr(105)+chr(110)+chr(116)+chr(101)+chr(103)+chr(114)+chr(105)+chr(116)+chr(121)+chr(95)+chr(99)+chr(104)+chr(101)+chr(99)+chr(107)); print(cur.fetchone()[0])\"'
"
```

### /bridge-loop [작업] — Ralph 루프 실행
```
/ralph-loop "
[작업 설명]

성공 기준: [측정 가능한 수치]
완료 신호: <promise>BRIDGE_DONE</promise>
실패 시: 진행 상황과 장애물을 tasks/ralph_log.md에 기록
" --max-iterations 20 --completion-promise "BRIDGE_DONE"
```

---

## 8. tasks/ 폴더 구조

```
Q:/Claudework/bridge base/tasks/
├── todo.md           # 현재 작업 체크리스트
├── lessons.md        # 실수 학습 로그 (Self-Improvement)
├── backlog.md        # 미래 작업 목록
├── db_checksum.log   # DB 수정 전후 SHA-256
├── pre_snapshot.txt  # 작업 전 건수 스냅샷
└── ralph_log.md      # Ralph 루프 실행 로그
```

---

## 9. 잠금 규칙

Bridge 홈페이지 Hero — 절대 수정 금지:
- 검정 배경 + 중앙 BRIDGE 로고
- "A career that changes your life."
- 흰색 현수교 케이블 아치 + 두 기둥 + SCROLL

DB 경로 — 절대 이동 금지:
- `Q:/Claudework/bridge base/master.db`
- `Q:/Claudework/bridge base/.bridge.key`

---

*Bridge CLAUDE.md v4.0 ULTIMATE — 2026-03-08*
*통합: Boris Cherny + Andrej Karpathy + Ralph Wiggum + Bridge 도메인*
