# ============================================================
# BRIDGE Craig RPA — 포터블 패키지 빌드  v2  (2026-04-01)
# ============================================================
# 이 PC에서 실행: USB / K드라이브에 복사할 패키지 생성
# DB에서 PII 테이블을 제거한 안전 버전 생성
# 사용법: powershell -ExecutionPolicy Bypass -File pack.ps1
# ============================================================

$ProjectRoot = "Q:\Claudework\bridge base"
$PackDir     = "$ProjectRoot\deploy\craig-portable"
$OutDir      = "$PackDir\package"
$Python313   = "C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  BRIDGE Craig RPA — Packing v2" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 출력 폴더 초기화
if (Test-Path $OutDir) { Remove-Item $OutDir -Recurse -Force }
New-Item -Path $OutDir -ItemType Directory -Force | Out-Null
New-Item -Path "$OutDir\tools" -ItemType Directory -Force | Out-Null
New-Item -Path "$OutDir\images" -ItemType Directory -Force | Out-Null
New-Item -Path "$OutDir\logs"   -ItemType Directory -Force | Out-Null

# ── 설치 스크립트 ─────────────────────────────────────────
Copy-Item "$PackDir\setup.ps1" "$OutDir\setup.ps1" -Force
Write-Host "  [OK] setup.ps1" -ForegroundColor Green

# ── 한글 설치가이드 ───────────────────────────────────────
$guide = Get-ChildItem $PackDir -Filter "*설치가이드*" | Select-Object -First 1 -ExpandProperty FullName
if ($guide -and (Test-Path $guide)) {
    Copy-Item $guide (Join-Path $OutDir (Split-Path $guide -Leaf)) -Force
    Write-Host "  [OK] $(Split-Path $guide -Leaf)" -ForegroundColor Green
}

# ── RPA 메인 파일들 (루트 기준 최신 버전) ─────────────────
foreach ($f in @("craigslist_auto_rpa.py", "rpa_overlay.py", "rpa_icon.ico")) {
    $src = "$ProjectRoot\$f"
    if (Test-Path $src) {
        Copy-Item $src "$OutDir\$f" -Force
        Write-Host "  [OK] $f" -ForegroundColor Green
    } else {
        Write-Host "  [SKIP] $f not found" -ForegroundColor DarkYellow
    }
}

# ── tools/ 서브모듈 ───────────────────────────────────────
foreach ($f in @("rpa_credential_vault.py")) {
    $src = "$ProjectRoot\tools\$f"
    if (Test-Path $src) {
        Copy-Item $src "$OutDir\tools\$f" -Force
        Write-Host "  [OK] tools/$f" -ForegroundColor Green
    }
}

# ── 이미지 ───────────────────────────────────────────────
$imgSrc = "$ProjectRoot\images"
if (Test-Path $imgSrc) {
    Copy-Item "$imgSrc\*" "$OutDir\images\" -Force
    $imgCount = (Get-ChildItem "$OutDir\images").Count
    Write-Host "  [OK] images/ ($imgCount files)" -ForegroundColor Green
}

# ── DB: PII 테이블 제거한 안전 버전 ───────────────────────
if (Test-Path "$ProjectRoot\master.db") {
    Copy-Item "$ProjectRoot\master.db" "$OutDir\master_safe.db" -Force
    $dbPath = ($OutDir -replace '\\','\\') + "\\master_safe.db"
    & $Python313 -c @"
import sqlite3
conn = sqlite3.connect(r'$OutDir\master_safe.db')
pii_tables = ['candidates','client_inquiries','interviews',
              'email_log','email_queue','contact_messages',
              'email_templates','admin_sessions','push_subscriptions']
dropped = []
for t in pii_tables:
    try:
        conn.execute(f'DROP TABLE IF EXISTS {t}')
        dropped.append(t)
    except: pass
conn.execute('VACUUM')
conn.commit()
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
conn.close()
print(f'  PII removed: {dropped}')
print(f'  Tables kept: {tables}')
"@ 2>&1
    Write-Host "  [OK] master_safe.db" -ForegroundColor Green
} else {
    Write-Host "  [WARN] master.db not found — DB skipped" -ForegroundColor Yellow
}

# ── README ────────────────────────────────────────────────
@"
BRIDGE Craigslist RPA — Portable Package v2 (2026-04-01)
=========================================================

[ 설치 ]
1. Python 3.10+ 설치 (python.org — "Add to PATH" 체크 필수)
2. Chrome 브라우저 설치 (google.com/chrome)
3. setup.ps1 우클릭 → "PowerShell로 실행"
4. 설치 경로 입력 (기본: D:\BridgeCraig)
5. Craigslist 계정 입력
6. 완료!

[ 포함 파일 ]
  craigslist_auto_rpa.py  — Selenium Craigslist 자동 게시 (메인)
  rpa_overlay.py          — 작업 진행 오버레이 (한국어 UI, 곰 애니)
  rpa_icon.ico            — BRIDGE RPA 아이콘
  tools/rpa_credential_vault.py — DPAPI 기반 자격증명 보관소
  images/                 — 광고 이미지 (B.jpg 등)
  master_safe.db          → jobs + ad_posts만 포함 (PII 제거됨)

[ 보안 ]
  - DB에 후보자 개인정보 없음 (jobs/ad_posts 테이블만)
  - 자격증명 DPAPI 암호화 저장 (Windows 현재 사용자만 복호화 가능)
  - 광고 텍스트 내 업체명/연락처/이메일 자동 제거 (redact_pii)
  - 로그에 개인정보 미기록

[ DB 업데이트 ]
  메인 PC에서 pack.ps1 재실행 → USB / K드라이브 복사 → setup.ps1 재실행

"@ | Set-Content "$OutDir\README.txt" -Encoding UTF8

# ── 패키지 크기 요약 ──────────────────────────────────────
Write-Host ""
$totalBytes = (Get-ChildItem $OutDir -Recurse -File | Measure-Object -Property Length -Sum).Sum
$totalMB = [math]::Round($totalBytes / 1MB, 1)
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Package ready: $OutDir" -ForegroundColor Green
Write-Host "  Total size: $totalMB MB" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

Get-ChildItem $OutDir | ForEach-Object {
    $size = if ($_.PSIsContainer) { "(dir)" } elseif ($_.Length -gt 1MB) { "{0:N1} MB" -f ($_.Length / 1MB) } else { "{0:N0} KB" -f ($_.Length / 1KB) }
    Write-Host "  $($_.Name) $size" -ForegroundColor Gray
}
Write-Host ""
Write-Host "  Next: Copy package\ folder to USB or K:\BRIDGE_RPA_Installer\" -ForegroundColor Cyan
Write-Host ""
