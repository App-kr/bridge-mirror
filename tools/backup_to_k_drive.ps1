$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$kRoot = "K:\Backup\PC_Snapshot_$ts"
New-Item -ItemType Directory -Force -Path $kRoot | Out-Null

Write-Host "=== K드라이브 PC 핵심 백업 ==="
Write-Host ("Target: " + $kRoot)
Write-Host ""

# 1. Adobe Acrobat 본체 (Q드라이브 + D드라이브 두 위치)
@(
    @{src="Q:\Apps\Adobe"; name="Adobe_Q"},
    @{src="D:\Adobe"; name="Adobe_D"}
) | ForEach-Object {
    if (Test-Path $_.src) {
        $dst = Join-Path $kRoot $_.name
        Write-Host ("Backup: " + $_.src + " -> " + $dst)
        robocopy $_.src $dst /E /R:1 /W:1 /MT:8 /NFL /NDL /NJH /NJS /NC /NS | Out-Null
        $size = (Get-ChildItem $dst -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
        Write-Host ("  Size: " + [math]::Round($size/1MB, 1) + " MB")
    }
}

# 2. 핵심 amtlib.dll golden copy
$goldenSrc = "Q:\Claudework\bridge base\.backups\adobe_critical\amtlib.dll"
if (Test-Path $goldenSrc) {
    Copy-Item $goldenSrc (Join-Path $kRoot "amtlib_golden.dll") -Force
    Write-Host "Backup: amtlib.dll golden copy"
}

# 3. BRIDGE 핵심 daemon 파일들 (작은 사이즈, 자주 백업)
$bridgeKey = Join-Path $kRoot "BRIDGE_critical"
New-Item -ItemType Directory -Force -Path $bridgeKey | Out-Null
@(
    "Q:\Claudework\bridge base\tools\focus_guard.py",
    "Q:\Claudework\bridge base\tools\ram_watchdog.py",
    "Q:\Claudework\bridge base\tools\game_mode_guardian.py",
    "Q:\Claudework\bridge base\tools\io_watchdog.py",
    "Q:\Claudework\bridge base\tools\amtlib_guardian.py",
    "Q:\Claudework\bridge base\tools\protect_adobe_permanent.ps1",
    "Q:\Claudework\bridge base\tools\register_amtlib_guardian.ps1",
    "Q:\Claudework\bridge base\.claude\work-tracker.py",
    "Q:\Claudework\agentic_os\watchdog.py",
    "Q:\Claudework\PC_OPERATING_RULES.md"
) | ForEach-Object {
    if (Test-Path $_) {
        Copy-Item $_ $bridgeKey -Force
        Write-Host ("Backup: " + (Split-Path $_ -Leaf))
    }
}

# 4. .vscode/settings.json 묶음
$vscodeBak = Join-Path $kRoot "vscode_settings"
New-Item -ItemType Directory -Force -Path $vscodeBak | Out-Null
@(
    "Q:\.vscode\settings.json",
    "Q:\Claudework\.vscode\settings.json"
) | ForEach-Object {
    if (Test-Path $_) {
        $name = $_.Replace(":", "").Replace("\", "_")
        Copy-Item $_ (Join-Path $vscodeBak $name) -Force
    }
}

# 5. README - 복원 가이드
$readme = @"
PC Snapshot Backup - $ts
============================

Backup Contents:
  - Adobe_Q/  : Adobe Acrobat from Q:\Apps\Adobe (full)
  - Adobe_D/  : Adobe Acrobat from D:\Adobe (full)
  - amtlib_golden.dll : Golden copy of amtlib.dll (Defender false positive insurance)
  - BRIDGE_critical/  : Core daemons + scripts
  - vscode_settings/  : Workspace settings

Restore on Other PC:
  1. Copy Adobe_Q/ -> Q:\Apps\Adobe (or D:\Adobe)
  2. Run protect_adobe_permanent.ps1 to register Defender exclusions
  3. Run register_amtlib_guardian.ps1 to setup auto-recovery
  4. Optional: Copy BRIDGE_critical scripts to target PC

Restore amtlib.dll only:
  Copy amtlib_golden.dll to:
    Q:\Apps\Adobe\ProgramFiles_x86\Acrobat DC\Acrobat\amtlib.dll
"@
Set-Content (Join-Path $kRoot "README.txt") $readme -Encoding UTF8

Write-Host ""
Write-Host "=== Backup Complete ==="
$totalSize = (Get-ChildItem $kRoot -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
Write-Host ("Total: " + [math]::Round($totalSize/1GB, 2) + " GB at " + $kRoot)

# K드라이브 잔여공간
$k = Get-PSDrive K
Write-Host ("K-drive free: " + [math]::Round($k.Free/1GB, 1) + " GB")
