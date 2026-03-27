Set objShell = CreateObject("WScript.Shell")
objShell.Run "cmd /k cd Q:\Claudework\bridge base && python tools/rpa_credential_vault.py setup", 1, False
