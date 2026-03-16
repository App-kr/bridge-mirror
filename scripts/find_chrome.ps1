$paths = @(
    'C:\Program Files\Google\Chrome\Application\chrome.exe',
    'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    'C:\Users\Scarlett\AppData\Local\Google\Chrome\Application\chrome.exe',
    'C:\Program Files\Google\Chrome Beta\Application\chrome.exe',
    'C:\Program Files\Chromium\Application\chrome.exe',
    'C:\Program Files (x86)\Chromium\Application\chrome.exe'
)
foreach ($p in $paths) {
    if (Test-Path $p) { Write-Host ("FOUND: " + $p) }
    else              { Write-Host ("NOT:   " + $p) }
}

# 레지스트리에서 Chrome 경로 확인
$reg1 = Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" -ErrorAction SilentlyContinue
$reg2 = Get-ItemProperty -Path "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" -ErrorAction SilentlyContinue
if ($reg1) { Write-Host ("REG HKLM: " + $reg1.'(default)') }
if ($reg2) { Write-Host ("REG HKCU: " + $reg2.'(default)') }

# where 명령
$w = where.exe chrome 2>&1
Write-Host ("WHERE: " + $w)
