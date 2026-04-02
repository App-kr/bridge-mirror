' 최소 창 테스트 VBS — 이 파일을 더블클릭해서 빨간 창이 뜨는지 확인
Option Explicit

Dim sh, py, cmd
Set sh = CreateObject("WScript.Shell")

py = "Q:\Phtyon 3\python.exe"

cmd = Chr(34) & py & Chr(34) & _
      " -X utf8 " & _
      Chr(34) & "Q:\Claudework\bridge base\tools\resume_converter\test_window.pyw" & Chr(34)

' 창 스타일 1 = 일반 표시 (콘솔창 잠깐 뜰 수 있음), False = 비동기
sh.Run cmd, 1, False

Set sh = Nothing
