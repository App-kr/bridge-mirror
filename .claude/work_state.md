# BRIDGE 작업 상태 (세션 간 공유)
마지막 업데이트: 2026.03.18

## 현재 진행 중인 작업
없음 (세션 종료)

## 작업하던 파일 목록
- `scripts/audio/audio-startup.ps1` — 신규 생성 완료
- `scripts/audio/register_audio_task.py` — 신규 생성 완료
- `웹빌드_자료/apps_script_skeleton.js` — 설계 오류 발견만 (파일 미수정)
- `웹빌드_자료/OPUS_설계서_프로필빌더.md` — DB 컬럼 대조 점검 완료

## 절대 건드리면 안 되는 것
- master.db (hard-delete 금지)
- .backups/ 폴더 (삭제 금지)
- HERO-ANIMATION (수정 금지)
- CLAUDE.md IMMUTABLE CORE 섹션
- .env 파일
- `_build_profile_card()` 함수 — 호환성 유지, 수정 금지

## 세션 종료 전 마지막 상태
시각: 2026-03-18
완료된 작업:
1. 재부팅 시 헤드셋 자동 선택 버그 → BridgeAudioStartup Task Scheduler 등록으로 해결
2. Apps Script 설계 점검 → 오류 7개 발견 및 보고 (파일 수정은 안 함)
3. 프로필 빌더 설계서 DB 컬럼 대조 점검 완료

미완료 (중단 지점):
- apps_script_skeleton.js 오류 수정 반영 → 아직 안 함
- Apps Script 구글 시트 실제 설치 → 아직 안 함
- 프로필 메일 빌더 API/UI 구현 → 아직 안 함

다음 세션 주의사항:
- apps_script_skeleton.js에 발견된 오류 7개 먼저 수정 후 구글 시트에 설치
- DB에 sheet_number, korea_experience 컬럼 없음 → ALTER TABLE 선행 필요
- marital → DB 실제 컬럼명은 married / personal → personal_consideration
