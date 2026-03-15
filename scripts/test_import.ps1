$py = "C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe"
$base = "Q:\Claudework\bridge base"
Set-Location $base
$r1 = & $py -c "import rpa_overlay; print('overlay_OK')" 2>&1
$r2 = & $py -c "import tkinter; print('tkinter_OK')" 2>&1
$r3 = & $py -c "import selenium; print('selenium_OK')" 2>&1
Write-Host $r1
Write-Host $r2
Write-Host $r3
