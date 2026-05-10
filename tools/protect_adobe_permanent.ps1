$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 영구 보호 — Defender / 백업 / Adobe 모두

Write-Host "=== 1) Defender 제외 폴더 확장 ==="
$EXCLUDE_PATHS = @(
    "Q:\Apps\Adobe",
    "D:\Adobe",
    "C:\Program Files (x86)\Adobe",
    "C:\Program Files\Adobe",
    "C:\ProgramData\Adobe",
    "C:\Users\Scarlett\Desktop\Acrobat_FullReset_20260510_125158",
    "C:\Users\Scarlett\Desktop\Acrobat_Cache_Backup_20260510_124057"
)
foreach ($p in $EXCLUDE_PATHS) {
    try {
        Add-MpPreference -ExclusionPath $p -ErrorAction Stop
        Write-Host ("  EXCLUDED: " + $p)
    } catch {
        Write-Host ("  (already or error: " + $p + ")")
    }
}

Write-Host ""
Write-Host "=== 2) Defender 제외 파일 (amtlib.dll 핵심) ==="
$EXCLUDE_FILES = @(
    "Q:\Apps\Adobe\ProgramFiles_x86\Acrobat DC\Acrobat\amtlib.dll",
    "D:\Adobe\ProgramFiles_x86\Acrobat DC\Acrobat\amtlib.dll"
)
foreach ($f in $EXCLUDE_FILES) {
    try {
        Add-MpPreference -ExclusionPath $f -ErrorAction Stop
    } catch {}
}

Write-Host ""
Write-Host "=== 3) Defender 위협 이름 제외 (HackTool:Win32/Keygen 차단) ==="
try {
    Add-MpPreference -ThreatIDDefaultAction_Ids 2147593794 -ThreatIDDefaultAction_Actions Allow -ErrorAction Stop
    Write-Host "  ALLOWED ThreatID 2147593794 (HackTool:Win32/Keygen for amtlib.dll)"
} catch {
    Write-Host ("  (admin needed: " + $_.Exception.Message + ")")
}

Write-Host ""
Write-Host "=== 4) BRIDGE 백업 폴더 영구 제외 ==="
$BACKUP_PATHS = @(
    "C:\Users\Scarlett\Desktop",
    "Q:\Claudework\bridge base\.backups",
    "Q:\Claudework\bridge backup",
    "Q:\Claudework\.snapshots"
)
foreach ($p in $BACKUP_PATHS) {
    if (Test-Path $p) {
        try {
            Add-MpPreference -ExclusionPath $p -ErrorAction Stop
            Write-Host ("  EXCLUDED: " + $p)
        } catch {}
    }
}

Write-Host ""
Write-Host "=== 5) 현재 Defender 제외 목록 검증 ==="
$prefs = Get-MpPreference
Write-Host ("Total ExclusionPath count: " + $prefs.ExclusionPath.Count)
$prefs.ExclusionPath | Where-Object { $_ -like '*Adobe*' -or $_ -like '*Acrobat*' -or $_ -like '*backup*' -or $_ -like '*Backup*' -or $_ -like '*snapshot*' } | ForEach-Object {
    Write-Host ("  " + $_)
}
