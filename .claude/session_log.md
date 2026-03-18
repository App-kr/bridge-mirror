# BRIDGE 세션 로그 (최근 5세션 자동 유지)
새 세션 시작 시 이 파일을 반드시 읽어라.

---
날짜: 2026-03-18 (오후 세션, 현재)
완료:
- BridgeAudioStartup Task Scheduler 등록 (재부팅 헤드셋 자동 선택 버그 해결)
- Apps Script 설계 오류 7개 발견·보고 (파일 수정은 안 함)
- 프로필 빌더 설계서 DB 컬럼 대조 점검

미완료:
- apps_script_skeleton.js 오류 수정 반영 (파일 미수정)
- Apps Script 구글 시트 실제 설치 (수동 작업 필요)
- 프로필 메일 빌더 API/UI 구현 (api_server.py + mail-send/page.tsx)

주의:
- DB에 sheet_number, korea_experience 컬럼 없음 → 구현 전 ALTER TABLE 선행
- marital → married / personal → personal_consideration (컬럼명 불일치)
- apps_script_skeleton.js 버그 4개는 e7d0977에서 이미 수정됨, 나머지 3개 미수정

---
날짜: 2026-03-18 (오전 세션, 09:00~14:40)
완료:
- OPUS 프로필 빌더 설계서 작성 (4a984bc) — 02.JPG 역공학, DB컬럼 대조
- Apps Script 버그 4개 수정 + OPUS_명령서.md 작성 (e7d0977)
  수정항목: LockService, e.range.getRow(), EXPERIENCE 중복, setBackground 순서
- RULE-PYTHON (ClaudeBlog venv 경로 고정) CLAUDE.md 추가 (41e426b, d71fe37)
- 블로그 프롬프트 v6.6 업데이트 (4f131ac) — 내부백링크·글자수·저작권
- MEMORY.md 200줄 재구조화 (57dbb28)

---
날짜: 2026-03-17 (21:00~24:00)
완료:
- bridge_prompt_ui 완성 (584ba63) — 한글UI, 한국인학생, 귀여운아이콘
- Teast 광고 포스팅 포맷 개선 + 30일 스케줄러 (4b1a4af)
  파일: tools/_teast_build_post.py, scripts/teast_post.bat, teast_post_silent.vbs

---
날짜: 2026-03-17 (16:30~17:00)
완료:
- 네이버 버튼 파비콘→N 텍스트, 템플릿 버튼 스타일 (e27882e)
  파일: web_frontend/src/app/admin/mail-send/page.tsx
- How It Works + Life in Korea 카드 삭제 (ad36350)

---
