' ═══════════════════════════════════════════════════════════
' BRIDGE Silent Runner
' 
' 용도: 어떤 명령이든 창 없이 완전 백그라운드 실행
' 사용자가 게임/포토샵/영화 중이어도 절대 방해 안 함
'
' 사용법:
'   wscript "Q:\Claudework\bridge base\scripts\silent_run.vbs"
'
' 수정: 아래 CMD 변수만 바꾸면 어떤 작업이든 적용 가능
' ═══════════════════════════════════════════════════════════

Set WshShell = CreateObject("WScript.Shell")

' ─── 실행할 명령어 (여기만 수정) ─────────────────────────
' 예시 1: Craigslist 자동 포스팅
CMD = "powershell -WindowStyle Hidden -ExecutionPolicy Bypass -Command ""cd 'Q:\Claudework\bridge base'; python scripts/auto_craigslist.py"""

' 예시 2: 파싱 스크립트
' CMD = "powershell -WindowStyle Hidden -Command ""cd 'Q:\Claudework\bridge base'; python scripts/parsers/parse_jobs.py --input raw.txt --db master.db"""

' 예시 3: docx 생성
' CMD = "powershell -WindowStyle Hidden -Command ""cd 'Q:\Claudework\bridge base'; node scripts/generators/generate_job_docx.js --input job.json"""

' ─── 실행 (0=창숨김, False=비동기) ───────────────────────
WshShell.Run CMD, 0, False

Set WshShell = Nothing
