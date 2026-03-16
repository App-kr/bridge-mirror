$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut("C:\Users\Scarlett\Desktop\BRIDGE RPA.lnk")
$sc.TargetPath = "wscript.exe"
$sc.Arguments = '"Q:\Claudework\bridge base\start_craig.vbs"'
$sc.WorkingDirectory = "Q:\Claudework\bridge base"
$sc.Description = "BRIDGE Craigslist RPA"
$sc.Save()
Write-Host "바탕화면 바로가기 생성: C:\Users\Scarlett\Desktop\BRIDGE RPA.lnk"
