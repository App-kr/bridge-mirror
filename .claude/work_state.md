# BRIDGE 작업 상태 (세션 간 유지)
최근 업데이트: 2026-03-20 (22:00)

## 세션 재시작 방법
1. `/clear`
2. `@.claude/work_state.md`
3. `'미완료 작업부터 계속'` 또는 원하는 작업 명시

---

## 현재 진행 중인 작업
없음 (세션 종료)

---

## 2026-03-20 세션 완료 전체 목록

### Canvas Sheet (핵심)
- fix(db): 272건 암호화 필드 평문 복원 (`0c31de5`)
- fix: 암호화 코드 복원 + Render 복원 API (`8d5125f`)
- fix(sheet): 열이동 + 메모배경색 + paste충돌 (`3c28b0a`)
- fix(sheet): 사진 우클릭 업로드 + 완료 토스트 (`5149109`)
- fix(sheet): photo paste + stage row color + dup col (`714974f`)
- fix(sheet): 사진cover채우기 + 행삭제 + 스타일토글 + stage배경색 (`b654f0a`)
- fix(sheet): 열선택스타일버그 + MailModal 구인자스타일 재작성 (`60447ee`)

### Employer 관리
- fix(employers): MEMO 암호화값 노출 방지 (`7204d56`)
- fix(employers): INIT_DATA 제거 + API 직접 로드 (`94c7d2b`)
- fix(employers): scroll + filter robustness (`1850a7c`)
- fix(employers): MEMO 복호화 필터 제거 (`bd9941c`)
- fix(employers): API → jobs 테이블 전환 (`7aeaef1`)
- fix(api): jNumber Job. 접두사 제거 (`be14905`)

### ImageFX 자동화
- feat(imagefx): abort 버튼 + status bar (`9af8b73`)
- fix(imagefx): photorealistic 프롬프트 + 로고 (`7f41284`)
- fix(imagefx): 6개 품질 이슈 (`6980876`)
- fix(imagefx): eye/race/age 제거 (`a5114b3`)
- feat(imagefx): AI사진 실사화 + JPG 저장 (`a12a64d`)
- feat(imagefx): diversity overhaul (`9f5c124`)

### ESLCafe 광고 관리
- feat: ESLCafe ad manager v5 HTML 앱 (`30fab25`)
- feat: ESLCafe ad manager v6 + anti-copy (`243122e`, `547ff2d`)

### 문서/보안 설계
- docs: AI_CONTEXT.md + AI_SECURITY_DESIGN.md + handoff v2 (`cbcc2d9`)
- docs: .memory/work-history.md 전체 이력 압축 저장 (현재)

---

## 미완료 (다음 세션 우선순위)

| 우선순위 | 항목 |
|---------|------|
| High | Canvas Sheet: 진행단계 변경 → DB PATCH 연결 |
| Medium | Canvas Sheet: 발송상태 태그 → DB 반영 |
| Medium | Canvas Sheet: 가상 렌더링 (Phase 4) |
| Low | CSV/Excel 내보내기 |

---

## 절대 건드리면 안 되는 것
- master.db (이동/삭제/hard-delete 금지)
- .bridge.key (암호화 키)
- HERO-ANIMATION (EarthGlobe.tsx 잠금)
- CLAUDE.md IMMUTABLE CORE 섹션
- .env 파일
- `_build_profile_card()` 함수

---

## 특이 사항 (현재 유효)
- Render autoDeploy: main push 시 자동 배포
- deploy_skip.json: expire=9999999999 → 모든 push 자동 승인
- python3 경로 broken → 항상 절대경로 사용
- 서버 Hot Reload 중 → 시작/종료 금지
- PAT workflow scope 없음 → .github/ push 불가
