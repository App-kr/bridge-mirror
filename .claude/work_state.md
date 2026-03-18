# BRIDGE 작업 상태 (세션 간 유지)
최근 업데이트: 2026-03-19

## 세션 재시작 방법
1. `/clear`
2. `@.claude/work_state.md`
3. `'Phase N Step M부터 계속'` 또는 `'미완료 작업부터 계속'`

---

## 현재 진행 중인 작업
없음 (세션 종료)

## 작업하던 파일 목록
- `web_frontend/src/app/admin/sheet/` — Canvas Sheet Phase 3 진행 중
- `api_server.py` — 프로필 메일 빌더 API (배포 실패 상태)
- `web_frontend/src/app/admin/mail-send/page.tsx` — 프로필 빌더 탭

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
