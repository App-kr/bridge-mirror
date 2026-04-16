# BRIDGE Admin Sheet 완전 복원 + 보안 강화
# Claude Code Opus 4.7 전용 프롬프트
# 2026.04.17 생성 — 전체 복사 후 Claude Code에 붙여넣기

---

## 역할

너는 BRIDGE 에이전시(bridgejob.co.kr)의 시니어 풀스택 엔지니어 겸 보안 담당자다.
ESL 원어민 교사 채용 플랫폼의 Admin Sheet를 완전 복원하고 보안을 강화한다.

## 환경

```
PC: Taco (Q: 드라이브), Python: "Q:\Phtyon 3\python.exe" (오타 그대로)
소스: Q:\Claudework\bridge base\
GitHub: koreadobby/bridge (main)
백엔드: FastAPI → Render (bridge-n7hk.onrender.com), autoDeploy:true
프론트: Next.js → Vercel (bridge-chi-lime.vercel.app)
DB: SQLite master.db (candidates 3,059건, 98+ 컬럼)
암호화: AES-256-GCM (BRIDGE_FIELD_KEY), PII 14필드 암호화 저장
```

## 현재 문제 6건 (스크린샷 기반)

1. **코드값 표시**: 국적 등에 "VDN2McU8dZB/mn..." 암호문이 평문 대신 표시됨
   → 원인: Render BRIDGE_FIELD_KEY 불일치 또는 _decrypt_row() 호출 누락
   → nationality_plain 컬럼이 있으면 그것 사용, 없으면 복호화 수정

2. **데이터 부분 로드**: 전체 3,059건 중 150건만 표시, "전체" 탭은 750건 표시 후 빈 화면
   → 원인: API limit/offset 페이징 + 프론트 가상 스크롤 미연동
   → 스크롤 시 추가 로드(무한 스크롤) 또는 배치 로드 수정

3. **엑셀 수정 시 오류**: 셀 편집 후 "페이지 오류" 발생
   → 원인: PATCH /api/admin/candidates/{id} 에러 (재암호화 또는 필드 불일치)

4. **Google Sheet 형식 불일치**: 구글시트 New탭(한글번역+사진+메모)과 Admin Sheet 컬럼 순서/내용 다름
   → 원인: defaultCols 매핑이 DB 스키마와 미동기화

5. **행 안의 수평선 + 한국어 세로 렌더링**: Canvas 셀 내부에 구분선 그려지고 한국어 글자별 줄바꿈
   → 원인: renderContent()에서 ctx.stroke()가 clip 내부에서 실행 + split(' ') 공백 기반 줄바꿈

6. **페이지 오류 (빨간 원)**: /admin/sheet 진입 시 간헐적 "페이지 오류" 표시
   → 원인: API 연결 실패 또는 JS 런타임 에러

## 절대 규칙 (위반 시 즉시 중단)

```
IC-01: master.db 이동/삭제/hard-delete 금지 (is_deleted=1 논리삭제만)
IC-02: 히어로 애니메이션 (검정배경+현수교) 수정 금지
IC-03: 비밀번호/API키 코드 하드코딩 금지 (환경변수만)
IC-04: Q: 드라이브 외부 파일 생성 금지
IC-05: 기존 작동 중인 API 엔드포인트 삭제 금지 (추가만)
IC-06: 개인정보(이름/이메일/전화/카카오/주소) 외부 노출 절대 금지
```

## 보안 요구사항 (필수 구현)

```
SEC-01: 파일 업로드 시 MIME 타입 + magic bytes 이중 검증 (PDF 위장 악성코드 차단)
SEC-02: 업로드 파일명 sanitize (path traversal, null byte, unicode 정규화)
SEC-03: 월 1회 자동 보안 검토 스크립트 (tools/security_monthly.py)
        - npm audit / pip-audit 취약점 스캔
        - gitleaks 시크릿 스캔
        - OWASP Top 10 체크리스트 자동 검증
        - 결과 로그 저장 + 관리자 이메일 알림
SEC-04: CSP 헤더 강화 (script-src, style-src, font-src 명시적 화이트리스트)
SEC-05: API Rate Limit 전 엔드포인트 확인 (public은 IP당 제한, admin은 세션당 제한)
SEC-06: SQL Injection 방지 — 모든 쿼리 파라미터화 검증 (raw string 포맷 금지)
SEC-07: AI 기반 서버 탈취 시도 방지:
        - prompt injection 방어 (사용자 입력을 시스템 프롬프트로 해석 불가)
        - SSRF 방어 (서버가 내부 IP 호출 불가)
        - 관리자 세션 토큰 httpOnly + Secure + SameSite=Strict
SEC-08: 파일 변조 감지 — 업로드된 파일의 SHA-256 해시를 DB에 저장, 다운로드 시 무결성 검증
```

## 작업 순서 (순차 실행, 각 완료 후 커밋)

### Phase 0: 감사 (READ-ONLY, 수정 금지) [직렬]

```bash
cd "Q:\Claudework\bridge base"
git add -A && git commit -m "PRE: opus47-admin-sheet-restore" 2>/dev/null

echo "=== 0-1. 현재 커밋 ==="
git log --oneline -10

echo ""
echo "=== 0-2. Render 환경변수 확인 ==="
grep -n "BRIDGE_FIELD_KEY\|FIELD_KEY\|ENCRYPT\|DECRYPT" api_server.py | head -20

echo ""
echo "=== 0-3. _decrypt_row 함수 ==="
sed -n '/_decrypt_row/,/^def /p' api_server.py | head -40

echo ""
echo "=== 0-4. nationality_plain 컬럼 ==="
sqlite3 master.db "PRAGMA table_info(candidates)" | grep -i "plain\|nation"

echo ""
echo "=== 0-5. GET candidates API 페이징 ==="
grep -n "def.*candidates\|limit\|offset\|page" api_server.py | head -20

echo ""
echo "=== 0-6. PATCH candidates 재암호화 ==="
grep -n "_encrypt_if_needed\|encrypt.*patch\|EDITABLE" api_server.py | head -15

echo ""
echo "=== 0-7. 프론트 데이터 로드 ==="
grep -n "fetch\|limit\|offset\|page\|scroll\|loadMore\|infinite" web_frontend/src/app/admin/sheet/BridgeCanvasSheet.tsx | head -20

echo ""
echo "=== 0-8. defaultCols 매핑 ==="
grep -n "defaultCols\|mapRow" web_frontend/src/app/admin/sheet/engine/types.ts | head -20

echo ""
echo "=== 0-9. Canvas renderContent ==="
grep -n "renderContent\|drawWrappedText\|ctx.stroke\|ctx.clip" web_frontend/src/app/admin/sheet/engine/GridEngine.ts | head -20

echo ""
echo "=== 0-10. 보안 현황 ==="
grep -n "rate_limit\|_rate_ok\|Content-Security-Policy\|CSP\|X-Frame\|CORS" api_server.py | head -15

echo ""
echo "=== 0-11. 파일 업로드 보안 ==="
grep -n "upload\|MIME\|magic\|file_type\|allowed_ext\|sanitize" api_server.py | head -15

echo ""
echo "=== 0-12. DB 스키마 전체 (candidates 컬럼) ==="
sqlite3 master.db "PRAGMA table_info(candidates)" | cat

echo ""
echo "=== 0-13. Google Sheet New탭 컬럼 순서 (참고) ==="
echo "A:이메일 B:이름 C:사진 D:번호 E:국적 F:국적상세 G:성별 H:현위치 I:학위 J:전공 K:자격증 L:시작일 M:지역선호 N:레퍼런스 O:선호/인터뷰 P:지원한곳/인터뷰요청 Q:포지션제안/진행 R:메모"
```

감사 결과 전부 보고. 수정하지 마. 보고 후 아래 순서대로 실행.

### Phase 1: 코드값 → 평문 복원 [직렬]

```
감사 0-4에서 nationality_plain 등 _plain 컬럼이 있으면:
  → GET /api/admin/candidates 응답에서 _plain 컬럼 우선 반환
  → 암호화 컬럼은 폴백으로만 사용

_plain 컬럼이 없으면:
  → _decrypt_row()가 올바르게 호출되는지 확인
  → Render BRIDGE_FIELD_KEY와 로컬 키 일치 여부 확인
  → 불일치 시: 로컬 DB에서 평문 값으로 nationality_plain 컬럼 생성 + API에서 반환

★ 프론트에서 표시할 때 암호화된 값이 보이면 안 됨 — 복호화 실패 시 빈 값("") 표시
```

커밋: `git commit -m "fix: decrypt nationality — plaintext fallback"`

### Phase 2: 전체 데이터 로드 [직렬]

```
현재: 구직활동중 150건만, 전체 750건만 표시

수정 방향 (감사 0-5, 0-7 기반):
A) API에서 limit을 충분히 높게 (3000+) 또는 전체 반환
B) 프론트에서 무한 스크롤 — 스크롤 끝 도달 시 다음 배치 자동 로드
C) 가상 렌더링 — Canvas에서 보이는 행만 그리기 (overscan 15)

★ "전체 3,059건"이 하단에 표시되고 스크롤로 전부 접근 가능해야 함
★ 기존 탭(구직활동중/체결완료/블랙리스트/전체)별 필터 유지
```

커밋: `git commit -m "fix: load all candidates — infinite scroll + virtual render"`

### Phase 3: 셀 편집 오류 수정 [직렬]

```
PATCH /api/admin/candidates/{id} 호출 시 에러 수정:
1. 재암호화 로직 확인 — PII 필드 수정 시 _encrypt_if_needed() 호출 되는지
2. EDITABLE 필드 목록에 누락된 컬럼 추가
3. 프론트에서 에러 시 사용자에게 토스트 알림 (빨간 "저장 실패")
4. 에러 발생해도 페이지 크래시 안 되게 try-catch 보강
```

커밋: `git commit -m "fix: PATCH candidates — re-encrypt + error handling"`

### Phase 4: Google Sheet 형식 일치 [직렬]

```
New탭(gid=408531674) 컬럼 순서를 참고하여 defaultCols 매핑 업데이트:
  메일, 이름, 사진, 번호, 국적, 성별, 현위치, 시작일, 학위, 전공, 자격증,
  지역선호, 타겟, 경력, 급여, 주거, 레퍼런스, 선호사항, 기피사항, 진행단계, 메모

★ 기존에 있는 컬럼은 순서만 변경
★ DB에 없는 컬럼은 추가하지 않음
★ mapRow()와 defaultCols 동기화
```

커밋: `git commit -m "fix: column order match Google Sheet New tab"`

### Phase 5: Canvas 렌더링 버그 수정 [직렬]

```
P0-A: 셀 내 수평선 제거
  → renderContent()를 2-패스로 분리:
    PASS 1: ctx.save/clip → fillRect(배경) + fillText(텍스트) → ctx.restore
    PASS 2: 구분선만 별도 루프 (clip 밖에서 stroke)

P0-A: 한국어 줄바꿈
  → drawWrappedText():
    공백 있으면 단어 단위, 공백 없으면 글자 단위
    셀 너비 초과 시 … 말줄임표
    행 높이 초과 줄은 그리지 않음

P0-C: ABCD 열 클릭 → 개별 열 선택만 (전체선택 금지)
P0-D: 행번호 칸에 r+1 순서 숫자만 (강사번호는 '번호' 컬럼에만)
P0-E: 정렬은 더블클릭만 (단일 클릭 정렬 제거)
```

커밋: `git commit -m "fix: Canvas rendering — lines, wrapping, selection, sort"`

### Phase 6: 보안 강화 [병렬] — 팬아웃 시 동시 실행

```
[서브에이전트 A] 파일 업로드 보안:
  - MIME + magic bytes 이중 검증
  - 파일명 sanitize (path traversal, null byte)
  - SHA-256 해시 DB 저장

[서브에이전트 B] 월간 보안 검토 스크립트:
  - tools/security_monthly.py 생성
  - npm audit + pip-audit + gitleaks + OWASP 체크
  - 로그 저장: tools/security_reports/YYYY-MM.json
  - Windows 작업 스케줄러: 매월 1일 03:00

[서브에이전트 C] CSP + 세션 보안:
  - next.config.js CSP 헤더 강화
  - admin 세션: httpOnly + Secure + SameSite=Strict
  - SSRF 방어: 내부 IP 호출 차단 미들웨어
  - Rate Limit 누락 엔드포인트 보강
```

커밋: `git commit -m "security: upload hardening + monthly audit + CSP + session"`

### Phase 7: 검증 + 배포 [직렬]

```bash
# 컴파일 검증
python -c "import py_compile; py_compile.compile('api_server.py', doraise=True); print('API OK')"
cd web_frontend && npx tsc --noEmit && npm run build && echo "FRONT OK"

# DB 무결성
sqlite3 master.db "PRAGMA integrity_check"

# 보안 스캔
cd .. && python tools/security_monthly.py --quick 2>/dev/null || echo "보안 스크립트 없으면 스킵"

# Git push (Render autoDeploy:true → 자동 배포)
git add -A && git commit -m "BRIDGE Admin Sheet 완전 복원 + 보안 강화" && git push origin main
```

## 보고 형식

```
| Phase | 항목 | 결과 | 비고 |
|-------|------|------|------|
| 0 | 감사 | | |
| 1 | 코드값→평문 | | |
| 2 | 전체 로드 | | |
| 3 | 편집 오류 | | |
| 4 | 컬럼 순서 | | |
| 5 | Canvas 버그 | | |
| 6 | 보안 강화 | | |
| 7 | 빌드+배포 | | |
```

## 향후 안정성 보장

```
★ 이 프롬프트에서 수정한 모든 설정값은 코드에 하드코딩이 아닌
  환경변수 또는 DB 설정 테이블에 저장되어야 함.
★ 향후 URL 변경, 웹 구조 개편, 패키지 업데이트 시에도
  세팅한 값이 깨지지 않도록:
  - 모든 API URL은 환경변수 또는 config 파일에서 읽기
  - 컬럼 매핑은 types.ts에 중앙 관리
  - 암호화 키는 환경변수만 (코드 하드코딩 금지)
  - 보안 설정은 미들웨어 레벨 (개별 라우트에 흩어지지 않게)
```
