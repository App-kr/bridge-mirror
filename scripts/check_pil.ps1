$py = "C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe"
$r = & $py -c "from PIL import Image, ImageDraw; print('PIL OK')" 2>&1
Write-Host $r
