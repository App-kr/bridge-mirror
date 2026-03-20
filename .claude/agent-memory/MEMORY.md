# Feature-Dev Agent Memory
최종 업데이트: 2026-03-20

## 환경
- Python 실행: `Q:/Claudework/ClaudeBlog/.venv/Scripts/python.exe` (backup 스크립트용)
- bridge_backup.py는 ClaudeBlog venv python으로 실행 불가 → git log로 이전 커밋 백업 확인 대체
- bash에서 Q: 드라이브 ls/dir 불가 → Read 도구로 파일 직접 읽기
- TSC 검증: `cd "Q:/Claudework/bridge base/web_frontend" && npx tsc --noEmit`

## 주요 파일 경로
- Sheet: `Q:/Claudework/bridge base/web_frontend/src/app/admin/sheet/`
- GridEngine: `engine/GridEngine.ts`
- SelectionManager: `engine/SelectionManager.ts`
- BridgeCanvasSheet.tsx: 메인 React 컴포넌트
- types.ts: TABS, STAGES, MTAGS, MAIL_TEMPLATES (수정 제한)
- api_server.py: `_decrypt_row`, `_safe_decrypt` 함수

## 확인된 패턴
- GridEngine은 ghost div 스크롤 + Canvas 렌더링 방식
- 열 선택: SelectionManager.selectedCols Set 사용, selectedRows와 분리
- 행번호(idx 타입 열): drawRowNum에서 rowIdx+1만 표시 (mgtNum 분리)
- _decrypt_row: 모든 str 필드 자동 감지 방식 (화이트리스트 아님)
- ColDef.v === false 이면 숨긴 열

## 수정 금지
- types.ts MAIL_TEMPLATES 내용
- types.ts DataRow 인터페이스
- HERO 애니메이션 관련 파일
