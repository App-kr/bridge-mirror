Set objShell = CreateObject("WScript.Shell")
Set objFSO   = CreateObject("Scripting.FileSystemObject")

strPY = "Q:\Phtyon 3\pythonw.exe"
strSC = objFSO.BuildPath(objFSO.GetParentFolderName(WScript.ScriptFullName), "craigslist_auto_rpa.py")

Dim accounts(3)
accounts(0) = "account1"
accounts(1) = "account2"
accounts(2) = "account3"
accounts(3) = "account4"

Dim i
For i = 0 To 3
    strCmd = """" & strPY & """ -X utf8 """ & strSC & """ --account " & accounts(i) & " --limit 10"
    ' 0 = 창 완전 숨김, False = 대기 없이 다음 계정 즉시 시작
    objShell.Run strCmd, 0, False
    WScript.Sleep 5000
Next
