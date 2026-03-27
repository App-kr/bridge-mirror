Set objShell = CreateObject("WScript.Shell")
strBatPath = objShell.CurrentDirectory & "\run.bat"
objShell.Run strBatPath, 0, False
