# ============================================================
# BRIDGE Craig RPA — 포터블 패키지 빌드
# ============================================================
# 이 PC에서 실행: USB에 복사할 패키지 생성
# 사용법: powershell -ExecutionPolicy Bypass -File pack.ps1
# ============================================================

$ProjectRoot = "Q:\Claudework\bridge base"
$PackDir = "$ProjectRoot\deploy\craig-portable"
$OutDir = "$ProjectRoot\deploy\craig-portable\package"

Write-Host "Building portable Craig RPA package..." -ForegroundColor Cyan

# 출력 폴더 생성
if (Test-Path $OutDir) { Remove-Item $OutDir -Recurse -Force }
New-Item -Path $OutDir -ItemType Directory -Force | Out-Null

# 필요 파일 복사
Copy-Item "$PackDir\setup.ps1" "$OutDir\setup.ps1" -Force
Copy-Item "$ProjectRoot\tools\craigslist_auto_rpa.py" "$OutDir\craigslist_auto_rpa.py" -Force
Copy-Item "$ProjectRoot\master.db" "$OutDir\master.db" -Force -ErrorAction SilentlyContinue

# README
@"
BRIDGE Craigslist RPA - Portable Setup
=======================================

1. 이 폴더를 USB에 복사
2. 다른 PC에서 setup.ps1 우클릭 → "PowerShell로 실행"
   (또는: powershell -ExecutionPolicy Bypass -File setup.ps1)
3. Craigslist 계정 정보 입력
4. 자동으로 6시간마다 실행됨

필요 사항:
- Windows 10/11
- Python 3.10+ (PATH에 등록)
- Chrome 브라우저
- 인터넷 연결

파일:
- setup.ps1              : 원클릭 설치 스크립트
- craigslist_auto_rpa.py : RPA 메인 스크립트
- master.db              : 채용공고 DB (복사본)
"@ | Set-Content "$OutDir\README.txt" -Encoding UTF8

Write-Host ""
Write-Host "[OK] Package ready at:" -ForegroundColor Green
Write-Host "  $OutDir" -ForegroundColor White
Write-Host ""
Write-Host "Copy this folder to USB drive." -ForegroundColor Cyan

$fileCount = (Get-ChildItem $OutDir).Count
Write-Host "Files: $fileCount" -ForegroundColor Gray
