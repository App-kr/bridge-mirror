# BRIDGE Craig RPA - Main PC Setup
# USB에서 이 스크립트를 실행하세요
# PowerShell 관리자 권한으로: powershell -ExecutionPolicy Bypass -File setup_main_pc.ps1

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 > $null

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "  BRIDGE Craig RPA - PC Setup" -ForegroundColor Cyan
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""

# 1. 설치 경로 설정
$installDir = "K:\BridgeCraig"
Write-Host "  Install to: $installDir" -ForegroundColor Gray

# 폴더 생성
if (!(Test-Path $installDir)) {
    New-Item -ItemType Directory -Path $installDir -Force | Out-Null
    Write-Host "  [OK] Directory created" -ForegroundColor Green
}

# 2. 파일 복사
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "  Copying from: $scriptDir" -ForegroundColor Gray

# 모든 파일 복사 (setup 스크립트 제외)
Get-ChildItem -Path $scriptDir -Recurse -Exclude "setup_main_pc.ps1","System Volume Information" | ForEach-Object {
    $dest = $_.FullName.Replace($scriptDir, $installDir)
    if ($_.PSIsContainer) {
        New-Item -ItemType Directory -Path $dest -Force -ErrorAction SilentlyContinue | Out-Null
    } else {
        $destDir = Split-Path -Parent $dest
        if (!(Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
        Copy-Item -Path $_.FullName -Destination $dest -Force
    }
}
Write-Host "  [OK] Files copied" -ForegroundColor Green

# 3. Python 패키지 설치
Write-Host ""
Write-Host "  Installing Python packages..." -ForegroundColor Yellow
pip install screeninfo Pillow pywin32 cryptography python-dotenv selenium webdriver-manager 2>&1 | Out-Null
Write-Host "  [OK] Packages installed" -ForegroundColor Green

# 4. launch_now.ps1 경로 업데이트
$launchFile = Join-Path $installDir "launch_now.ps1"
if (Test-Path $launchFile) {
    $content = Get-Content $launchFile -Raw -Encoding UTF8
    # 경로가 다를 경우 업데이트
    $content = $content -replace 'S:\\Claudework\\BridgeCraig', $installDir.Replace('\','\\')
    [System.IO.File]::WriteAllBytes($launchFile, [System.Text.Encoding]::UTF8.GetPreamble() + [System.Text.Encoding]::UTF8.GetBytes($content))
    Write-Host "  [OK] launch_now.ps1 paths updated" -ForegroundColor Green
}

# 5. 바탕화면 바로가기 생성
Write-Host ""
Write-Host "  Creating desktop shortcut..." -ForegroundColor Yellow
$python = & python -c "import sys; print(sys.executable)" 2>$null
& $python -c @"
import win32com.client, os
shell = win32com.client.Dispatch('WScript.Shell')
desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
lnk_path = os.path.join(desktop, 'BRIDGE 작업.lnk')
lnk = shell.CreateShortCut(lnk_path)
lnk.TargetPath = r'C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe'
lnk.Arguments = r'-NoProfile -ExecutionPolicy Bypass -File "$installDir\launch_now.ps1"'.replace('$installDir', r'$installDir')
lnk.IconLocation = r'$installDir\craig_icon.ico,0'
lnk.WorkingDirectory = r'$installDir'
lnk.Save()
print('  [OK] Desktop shortcut created')
"@ 2>&1

# 6. 무결성 해시 초기화
Write-Host ""
Write-Host "  Initializing integrity hashes..." -ForegroundColor Yellow
Set-Location $installDir
& python craigslist_auto_rpa.py --integrity-reset 1234
Write-Host "  [OK] Integrity hashes initialized" -ForegroundColor Green

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Desktop: 'BRIDGE 작업' shortcut" -ForegroundColor Gray
Write-Host "  Location: $installDir" -ForegroundColor Gray
Write-Host ""
Write-Host "  Press any key to close..." -ForegroundColor DarkGray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
