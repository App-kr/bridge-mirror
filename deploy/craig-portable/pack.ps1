# ============================================================
# BRIDGE Craig RPA — 포터블 패키지 빌드
# ============================================================
# 이 PC에서 실행: USB에 복사할 패키지 생성
# DB에서 PII 테이블을 제거한 안전 버전 생성
# 사용법: powershell -ExecutionPolicy Bypass -File pack.ps1
# ============================================================

$ProjectRoot = "Q:\Claudework\bridge base"
$PackDir = "$ProjectRoot\deploy\craig-portable"
$OutDir = "$PackDir\package"

Write-Host "Building portable Craig RPA package..." -ForegroundColor Cyan

# 출력 폴더 생성
if (Test-Path $OutDir) { Remove-Item $OutDir -Recurse -Force }
New-Item -Path $OutDir -ItemType Directory -Force | Out-Null

# setup.ps1 복사
Copy-Item "$PackDir\setup.ps1" "$OutDir\setup.ps1" -Force
Write-Host "  [OK] setup.ps1" -ForegroundColor Green

# RPA 스크립트 + 오버레이 복사
Copy-Item "$ProjectRoot\tools\craigslist_auto_rpa.py" "$OutDir\craigslist_auto_rpa.py" -Force
Write-Host "  [OK] craigslist_auto_rpa.py" -ForegroundColor Green
Copy-Item "$ProjectRoot\tools\rpa_overlay.py" "$OutDir\rpa_overlay.py" -Force
Write-Host "  [OK] rpa_overlay.py" -ForegroundColor Green

# 설치 가이드 복사
$guideFile = Join-Path $PackDir ([char[]]@(49352,80,67,95,49444,52824,44032,51060,46300,46041,53944,53944) -join '')
if (-not (Test-Path $guideFile)) { $guideFile = Get-ChildItem $PackDir -Filter "*설치가이드*" | Select-Object -First 1 -ExpandProperty FullName }
if ($guideFile -and (Test-Path $guideFile)) {
    Copy-Item $guideFile (Join-Path $OutDir (Split-Path $guideFile -Leaf)) -Force
    Write-Host "  [OK] $(Split-Path $guideFile -Leaf)" -ForegroundColor Green
}

# DB: PII 테이블 제거한 안전 버전 생성
if (Test-Path "$ProjectRoot\master.db") {
    Copy-Item "$ProjectRoot\master.db" "$OutDir\master_safe.db" -Force

    python -c @"
import sqlite3
conn = sqlite3.connect('$($OutDir -replace '\\','\\\\')\\master_safe.db')
pii_tables = ['candidates','client_inquiries','interviews',
              'email_log','email_queue','contact_messages',
              'email_templates','admin_sessions']
dropped = []
for t in pii_tables:
    try:
        conn.execute(f'DROP TABLE IF EXISTS {t}')
        dropped.append(t)
    except: pass
conn.execute('VACUUM')
conn.commit()
tables = [r[0] for r in conn.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall()]
conn.close()
print(f'  Dropped PII tables: {dropped}')
print(f'  Remaining tables: {tables}')
"@ 2>&1

    Write-Host "  [OK] master_safe.db (PII removed)" -ForegroundColor Green
} else {
    Write-Host "  [WARN] master.db not found" -ForegroundColor Yellow
}

# README
@"
BRIDGE Craigslist RPA - Portable Setup
=======================================

1. Python 3.10+ 설치 (python.org, "Add to PATH" 체크)
2. Chrome 브라우저 설치
3. setup.ps1 우클릭 -> "PowerShell로 실행"
4. 설치 경로 선택 (기본: D:\BridgeCraig)
5. Craigslist 계정 정보 입력
6. 끝! 6시간마다 자동 실행

보안:
- DB에 개인정보(PII) 없음: jobs + ad_posts 테이블만 포함
- 크리덴셜은 .env 파일에만 저장 (현재 사용자만 접근 가능)
- 광고 텍스트에 업체명/연락처/이메일 자동 제거 (redact_pii)
- 로그에 개인정보 미기록

DB 업데이트:
- 새 채용공고 추가 시, 메인 PC에서 pack.ps1 재실행 -> USB 복사
"@ | Set-Content "$OutDir\README.txt" -Encoding UTF8

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Package ready:" -ForegroundColor Green
Write-Host "  $OutDir" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

$files = Get-ChildItem $OutDir | ForEach-Object {
    $size = if ($_.Length -gt 1MB) { "{0:N1} MB" -f ($_.Length / 1MB) } else { "{0:N0} KB" -f ($_.Length / 1KB) }
    "  $($_.Name) ($size)"
}
$files | ForEach-Object { Write-Host $_ -ForegroundColor Gray }
Write-Host ""
Write-Host "Copy this folder to USB." -ForegroundColor Cyan
