# ============================================================
# Craig RPA — 작업 기록 내보내기 (다른 PC에서 실행)
# ============================================================
# USB에 복사해서 메인 PC로 가져갈 수 있습니다.
# 사용법: 우클릭 → PowerShell로 실행
# ============================================================

$InstallDir = "D:\BridgeCraig"
$DB = "$InstallDir\data\master.db"
$OutFile = "$PSScriptRoot\craig_records.json"

if (-not (Test-Path $DB)) {
    Write-Host "  [ERROR] DB not found: $DB" -ForegroundColor Red
    $InstallDir = Read-Host "  설치 경로 입력"
    $DB = "$InstallDir\data\master.db"
    if (-not (Test-Path $DB)) {
        Write-Host "  [ERROR] DB not found" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Host ""
Write-Host "  Craig RPA 기록 내보내기" -ForegroundColor Cyan
Write-Host ""

$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python 3") { $pythonCmd = $cmd; break }
    } catch { }
}

& $pythonCmd -c @"
import sqlite3, json
conn = sqlite3.connect(r'$DB')
conn.row_factory = sqlite3.Row
rows = conn.execute('SELECT * FROM ad_posts ORDER BY id').fetchall()
data = [dict(r) for r in rows]
conn.close()

with open(r'$OutFile', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'  [OK] {len(data)}건 내보내기 완료')
print(f'  파일: $OutFile')
"@

Write-Host ""
Write-Host "  이 파일을 USB에 넣어서 메인 PC로 가져가세요" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to close"
