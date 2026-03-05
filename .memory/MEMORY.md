# BRIDGE Project — Memory Index
> 인덱스 전용. 상세 내용은 각 토픽 파일 참조.
> 절대 규칙 → `CLAUDE.md` | 학습 내용 → 아래 파일들
> 환경 무관 적용: Desktop, Mobile, Admin System 모두 동일

## Quick Reference
- **서비스**: bridgejob.co.kr (ESL 교사 채용)
- **스택**: FastAPI + Next.js 15 + Supabase + SQLite
- **빌드**: 14 routes, 0 errors (2026-02-28)

---

## Topic Files

| 파일 | 내용 | 최종 업데이트 |
|------|------|-------------|
| [architecture.md](architecture.md) | 시스템 구조, 데이터 흐름, 파일 맵 | 2026-02-28 |
| [api-endpoints.md](api-endpoints.md) | API 엔드포인트, Rate limit, 인증 레벨 | 2026-02-28 |
| [debugging-patterns.md](debugging-patterns.md) | 디버깅 패턴, 흔한 오류, 해결법 | 2026-02-28 |
| [admin-system.md](admin-system.md) | 관리자 페이지, Desktop 앱, 인터뷰 | 2026-02-28 |
| [design-system.md](design-system.md) | UI 디자인 규칙, CSS 클래스, 레이아웃 | 2026-02-28 |
| [deployment.md](deployment.md) | 배포 설정, nginx, systemd, 환경변수 | 2026-02-28 |

---

## User Preferences
- 파일 수정 전 반드시 백업
- 하위 폴더 정리 원칙
- 묻지 말고 자율 실행 선호
- `.next` 캐시 충돌 → `rm -rf .next` 후 재시작
- `.env.local`: `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`
- 모든 메모리/설정 파일은 프로젝트 내부(`Q:\Claudework\bridge base`)에만 보관
- **서버 규칙**: dev 서버는 별도 터미널에서 --reload로 상시 실행 중. 코드 수정 시 Hot Reload 자동 반영. 서버 시작/종료/재시작 명령 실행 금지. package.json이나 .env 변경 시에만 "재시작 필요" 안내.
- **화면 확인 규칙**: 브라우저를 열어 보여주기 전 반드시 curl로 서버 응답/렌더링 검증. 검증 통과 후에만 브라우저 열기.
- **포커스 스틸 금지**: 게임 중 바탕화면 튕김 방지. GUI 앱(브라우저/탐색기/메모장) 실행 금지, `start` 명령 금지, 모든 작업은 현재 bash 셸 내에서만. 서버는 `run_in_background`로만 시작.

## Team Names (영국식 영문 이름)
- **Scarlett** — 대표 (User)
- **Violet** — 운영부장
- 이름 규칙: 영국식 영어 이름으로 통일
- **MARK 사용 금지**
