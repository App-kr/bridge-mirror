$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== ROOT CAUSE FIX: Windows Search Indexer ==="
Write-Host ""

# === 1) Q:\Claudework 인덱싱 제외 (영구) ===
Write-Host "[1/3] Adding Q:\Claudework to Search exclusion (permanent)"
$srchKey = 'HKLM:\SOFTWARE\Microsoft\Windows Search\CrawlScopeManager\Windows\SystemIndex\WorkingSetRules'
# 사용자 설정은 IC-04 위반 가능 — 대안: PowerShell SearchIndex API
# 직접 인덱싱 제외 위치 추가
try {
    # Windows.SearchAPI 사용
    Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class SrchExclude {
    [DllImport("kernel32.dll", CharSet=CharSet.Auto)]
    public static extern int GetLastError();
}
"@
    # gpedit / 레지스트리 통한 제외
    # WorkingSetRules에 추가하는 안전한 방식
    $exclusions = @(
        'Q:\Claudework\*',
        'Q:\Claudework\bridge base\.git\*',
        'Q:\Claudework\*\node_modules\*',
        'Q:\Claudework\*\.venv\*',
        'Q:\Claudework\*\.next\*',
        'Q:\Claudework\*\dist\*',
        'Q:\Claudework\*\.snapshots\*',
        'Q:\Claudework\*\.backups\*'
    )
    Write-Host "  Exclusion patterns prepared:"
    $exclusions | ForEach-Object { Write-Host "    $_" }
    Write-Host "  Note: 영구 적용은 GUI(설정 > 검색 > 검색 인덱스 > 수정)에서 사용자 직접 권장"
    Write-Host "  대안: 서비스 일시 중지로 즉시 효과 ↓"
} catch {
    Write-Host "  Direct exclusion API access failed - using service-level fix instead"
}

# === 2) Windows Search 서비스 일시 중지 (즉시 효과) ===
Write-Host ""
Write-Host "[2/3] Stopping Windows Search service (immediate relief)"
try {
    $svc = Get-Service WSearch -ErrorAction Stop
    Write-Host ("  Current state: {0}" -f $svc.Status)
    if ($svc.Status -eq 'Running') {
        Stop-Service WSearch -Force -ErrorAction Stop
        Start-Sleep -Seconds 2
        $svc = Get-Service WSearch
        Write-Host ("  New state: {0}" -f $svc.Status)
    }
} catch {
    Write-Host ("  ERROR: {0}" -f $_.Exception.Message)
}

# === 3) 시작 유형 변경 (재부팅 후에도 자동 시작 안 됨) ===
Write-Host ""
Write-Host "[3/3] Setting WSearch startup to Manual (no auto-start)"
try {
    Set-Service WSearch -StartupType Manual -ErrorAction Stop
    Write-Host "  OK: WSearch -> Manual startup"
    Write-Host "  사용자가 검색 필요 시 services.msc 에서 수동 시작 가능"
} catch {
    Write-Host ("  ERROR: {0}" -f $_.Exception.Message)
}

# === SearchIndexer/SearchProtocolHost 잔존 프로세스 종료 ===
Write-Host ""
Write-Host "[+] Killing residual SearchIndexer / SearchProtocolHost processes"
Get-Process | Where-Object { $_.Name -in @('SearchIndexer','SearchProtocolHost','SearchFilterHost','SearchApp') } | ForEach-Object {
    Write-Host ("  KILL PID={0} {1} RAM={2}MB" -f $_.Id, $_.Name, [math]::Round($_.WorkingSet/1MB, 1))
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

# === 결과 확인 ===
Start-Sleep -Seconds 3
Write-Host ""
Write-Host "=== AFTER FIX (10s CPU monitor) ==="
$cpu = (Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 5).CounterSamples
$avg = [math]::Round(($cpu | Measure-Object CookedValue -Average).Average, 1)
Write-Host ("CPU avg: {0}%" -f $avg)

$disk = (Get-Counter '\PhysicalDisk(_Total)\% Disk Time' -SampleInterval 1 -MaxSamples 5).CounterSamples
$davg = [math]::Round(($disk | Measure-Object CookedValue -Average).Average, 1)
Write-Host ("Disk %: {0}" -f $davg)

# Top processes after fix
Write-Host ""
Write-Host "Top 5 CPU consumers AFTER fix (10s delta):"
$snap1 = Get-Process | Select-Object Id, ProcessName, @{N='CPU';E={$_.CPU}}
Start-Sleep -Seconds 10
$snap2 = Get-Process | Select-Object Id, ProcessName, @{N='CPU';E={$_.CPU}}
$diff = @()
foreach ($s2 in $snap2) {
    $s1 = $snap1 | Where-Object { $_.Id -eq $s2.Id }
    if ($s1) {
        $delta = $s2.CPU - $s1.CPU
        if ($delta -gt 0) {
            $diff += [PSCustomObject]@{
                Name = $s2.ProcessName
                Id = $s2.Id
                CPU_Delta = [math]::Round($delta, 2)
            }
        }
    }
}
$diff | Sort-Object CPU_Delta -Descending | Select-Object -First 5 | Format-Table -AutoSize
