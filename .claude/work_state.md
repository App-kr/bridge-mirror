# BRIDGE 작업 상태 (세션 간 유지)
최근 업데이트: 2026-03-20 (21:35)

## 세션 재시작 방법
1. `/clear`
2. `@.claude/work_state.md`
3. `'Phase N Step M부터 계속'` 또는 `'미완료 작업부터 계속'`

---

## 현재 진행 중인 작업
없음 (세션 종료)

## 2026-03-20 세션 완료 (홈페이지 불안정요소 수정)
- fix(CSP): connect-src *.onrender.com 와일드카드 (CRITICAL-2)
- fix(MegaMenu): DOM createElement 링크 → router.push() SPA 네비게이션 복구 (CRITICAL-3)
- fix(manifest): "BRIDGE Admin" → "BRIDGE", start_url /admin → / (BUG-18)
- feat(api/track): /api/track POST 엔드포인트 신규 (BUG-12)
- fix(api/jobs): 로컬 JSON 없으면 Render API 프록시 (BUG-1/2)
- fix(layout): og:image 추가 (UX)

## 2026-03-20 세션 완료 (EmployerManagement 기능 머지)
- feat(DocBlock): Job번호·업체명 더블클릭 인라인 편집 (onEditJobCode / onEditName 콜백)
- feat(DocBlock): 이메일 클릭 → 메일 팝업 자동 오픈 (onOpenMail 콜백)
- feat(MailComposer): 헤더 드래그로 팝업 위치 이동 (dragPos state + mousemove)
- feat(ExcelView): 열 문자 헤더(A/B/C) + 행 번호(1/2/3) 추가
- EmployerManagement: 위 3개 콜백 DocBlock에 연결, 빌드 에러 0개

## 2026-03-19 저녁 세션 완료 (ClaudeBlog API 오류 수정)
- fix(content_generator): Gemini 키 고갈 오류 근본 수정
  - _SESSION_EXHAUSTED: 세션 내 일일 고갈 키 추적 (재시도 낭비 방지)
  - 60초 재시도 → 20초 단축 (RPM 회복용)
  - 2회 연속 429 → 일일 고갈로 간주, 세션 제외
  - Claude 400 잔액부족 감지 → 명확한 메시지 + 행동 안내
- fix(main): --count N 인수 지원 / daily_posts 루프 적용
  - --dry --count 2 → 2건 더미 생성 확인 완료
  - --now --count 5 → 5건 발행 지원
  - --draft --count 10 → 10건 초안 생성 지원
- feat(settings.py): 신규 설정 관리자
  - 메뉴 1: Gemini API 키 추가/삭제/이름변경/모델변경
  - 메뉴 2: 계정/스케줄 편집 (daily_posts, post_time, days_ahead)
  - 메뉴 3: 키워드 풀 편집 (추가/삭제/재사용기간)
  - 메뉴 4: 사용자 정의 명령어 등록·즉시실행
  - 메뉴 5: 명령어 실행 (직접 인수 입력 포함)
  - 메뉴 6: API 키 상태 실시간 확인
- config.json: user_commands 기본 5개 preset 추가

## 작업하던 파일 목록
- `web_frontend/src/app/admin/sheet/` — Canvas Sheet Phase 3 진행 중
- `api_server.py` — 프로필 메일 빌더 API (배포 실패 상태)
- `web_frontend/src/app/admin/mail-send/page.tsx` — 프로필 빌더 탭

## 2026-03-19 세션 완료 사항 (추가)
- fix(sheet): 행 체크박스 선택 후 색상 → 전체 컬럼에 적용 (applyStyleToSelection)
- fix(sheet): MailModal Gmail/Naver 토글 + handleSend API 호출 + 결과 피드백
- fix(api): _decrypt_row 공백/개행 제거 후 is_encrypted 체크 (edge case 대응)
- fix(db): candidates.sheet_number 컬럼 추가 + 3059건 rowid 마이그레이션 완료
  → 번호 컬럼에 1~3059 고유 번호 표시 (사용자 직접 수정 가능)

## 절대 건드리면 안 되는 것
- master.db (hard-delete 금지)
- .backups/ 내용 (임의 삭제 금지)
- HERO-ANIMATION (CSS/JSX 수정 금지)
- CLAUDE.md IMMUTABLE CORE 섹션
- .env 파일
- `_build_profile_card()` 함수 — 호환성 유지, 삭제 금지

## 세션 종료 때 기록한 내용
시간: 2026-03-19
완료한 작업:
1. Adobe Genuine Software 완전 차단 (ags_nuke.ps1)
2. Adobe TOS 팝업 차단 (tos_fix.ps1)
3. ClaudeBlog 기술 메모리 완전 저장 (.memory/blog-automation.md)
4. Q 드라이브 전체 정리 완료 (24개 폴더 영문명)
5. Stop hook bash 오류 수정 (python3→bat wrapper)
6. CLAUDE.md v5.0 SLIM + sheet_context.md + sheet-worker 에이전트 구축

미완료 (다음 세션):
- Render/Vercel 배포 실패 수정 (프로필 메일 빌더 관련)
- Canvas Sheet Phase 3 — 발송상태 태그 DB 반영
- Canvas Sheet Phase 3 — 진행단계 드롭다운 저장
- Supabase 보안 경고 2건 수정 (개발 완료 후)
- DB ALTER TABLE: sheet_number, korea_experience 컬럼 추가
- Apps Script 구글 시트 실제 설치

특이 사항:
- Render autoDeploy: false (수동 배포만)
- python3 = D:\Phtyon 3 경로 (broken) → 항상 절대경로 사용
- 사진공유 폴더 원본 잠금 → 탐색기에서 수동 삭제 필요
