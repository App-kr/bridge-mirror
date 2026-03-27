' BRIDGE Resume Converter — 숨김 런처 (CMD 창 없음)
Option Explicit

Dim sh, fso, py, toolDir, cmd
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

toolDir = "Q:\Claudework\bridge base\tools"

' pythonw.exe 우선 (콘솔창 없는 GUI 전용)
Dim pyw, pyc
pyw = "D:\Phtyon 3\pythonw.exe"
pyc = "D:\Phtyon 3\python.exe"

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

' 창 스타일 1 = 일반 (정상 표시), False = 비동기 실행
sh.Run cmd, 1, False

Set fso = Nothing
Set sh  = Nothing
