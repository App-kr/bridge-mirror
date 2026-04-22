' BRIDGE Resume Converter — 콘솔 없음 실행 런처
' pythonw.exe 사용 → CMD 창 없이 GUI만 뜸
' 닫아도 프로그램 유지 (VBS는 독립 실행 후 즉시 종료)
Dim WshShell
Set WshShell = CreateObject("WScript.Shell")

Dim PY  : PY  = "Q:\Phtyon 3\pythonw.exe"
Dim SRC : SRC = "Q:\Claudework\bridge base\tools\resume_converter\launcher.py"

' window style 0 = 완전 숨김, bWaitOnReturn = False (비동기)
WshShell.Run """" & PY & """ -X utf8 """ & SRC & """", 0, False
Set WshShell = Nothing
