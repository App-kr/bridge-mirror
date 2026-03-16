$py = "C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe"
$r = & $py "Q:\Claudework\bridge base\scripts\make_craig_icon.py" 2>&1
$r | Out-String | Write-Host
Write-Host "exit=$LASTEXITCODE"
