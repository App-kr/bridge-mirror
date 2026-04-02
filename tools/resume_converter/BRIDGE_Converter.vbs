' BRIDGE Resume Converter — 숨김 런처 (CMD 창 없음)
Option Explicit

Dim sh, fso, py, toolDir, cmd
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

toolDir = "Q:\Claudework\bridge base\tools"

' Q드라이브 Python 3.10 (bridge base 전용)
Dim pyw, pyc
pyw = "Q:\Phtyon 3\pythonw.exe"
pyc = "Q:\Phtyon 3\python.exe"

If Not fso.FileExists(pyw) Then pyw = "Q:\Phtyon 3\python.exe"
If Not fso.FileExists(pyc) Then pyc = "Q:\Phtyon 3\python.exe"

If fso.FileExists(pyw) Then
    py = pyw
ElseIf fso.FileExists(pyc) Then
    py = pyc
Else
    py = "pythonw"
End If

' 작업 디렉토리 설정 (resume_converter 패키지 부모)
sh.CurrentDirectory = toolDir

' sys.path 포함하여 실행 (모듈 검색 경로 보장)
cmd = Chr(34) & py & Chr(34) & _
      " -X utf8 -c " & _
      Chr(34) & _
      "import sys,os;" & _
      "sys.path.insert(0,r'" & toolDir & "');" & _
      "from resume_converter.main_gui import main;main()" & _
      Chr(34)

' 창 스타일 0 = 숨김 (CMD 창 없음), False = 비동기 실행
sh.Run cmd, 0, False

Set fso = Nothing
Set sh  = Nothing
