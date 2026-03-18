# BRIDGE 다음 작업 목록

## 🔴 1순위 — Apps Script 구글 시트 설치 (수동)
- 구글 시트 → 확장 프로그램 → Apps Script 열기
- `웹빌드_자료/apps_script_skeleton.js` 내용 붙여넣기
- `installTrigger()` 실행 → onFormSubmit 트리거 등록
- `testRun()` 실행 → 시트/번호 확인
- 폼 테스트 제출 → New 시트 3행 확인

## 🟡 2순위 — 프로필 메일 빌더 구현
사전 조건:
- `ALTER TABLE candidates ADD COLUMN sheet_number INTEGER DEFAULT NULL`
- `ALTER TABLE candidates ADD COLUMN korea_experience TEXT DEFAULT NULL`

구현:
- `api_server.py`: `_get_flag_emoji()`, `_build_profile_card_v2()`, 2개 엔드포인트 추가
- `web_frontend/src/app/admin/mail-send/page.tsx`: 프로필 빌더 탭 추가

## 🟢 3순위 — ClaudeBlog 개선
- `[IMG_TOP]` 위치: 서론 텍스트 입력 이후로 이동
- `_set_cover_image()` 구현 (네이버 SE4 커버 이미지)
- 작성 완료 후 Ctrl+A → Ctrl+E 자동 적용

## ⚪ 4순위
- Vercel 배포 화면 확인 (스크린샷)
- 모바일 반응형 점검
