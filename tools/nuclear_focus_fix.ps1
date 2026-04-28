$ErrorActionPreference = 'Continue'

Write-Host "=== 1) Anthropic Claude 데스크탑 앱 식별 ==="
$claudeDesktop = Get-CimInstance Win32_Process | Where-Object {
    $_.ExecutablePath -like '*WindowsApps\Claude_*\app\Claude.exe' -or
    $_.ExecutablePath -like '*\Claude.exe'
} | Where-Object {
    $_.ExecutablePath -notlike '*claude-code*'  # CLI는 보호
} | Select-Object ProcessId, ExecutablePath

if ($claudeDesktop) {
    Write-Host "발견된 데스크탑 앱:"
    $claudeDesktop | Format-Table -AutoSize
} else {
    Write-Host "  (Anthropic 데스크탑 앱 미실행)"
}

Write-Host "`n=== 2) ForegroundLockTimeout 정상화 ==="
$current = (Get-ItemProperty 'HKCU:\Control Panel\Desktop' -Name 'ForegroundLockTimeout' -ErrorAction SilentlyContinue).ForegroundLockTimeout
Write-Host "  현재값: $current"
# 4294967295 (0xFFFFFFFF = -1) 은 Windows 가 무효로 처리할 수 있음
# 200000 (200초) = MS 권장 max — 정상 동작 보장
$NORMAL_LOCK = 200000
Set-ItemProperty 'HKCU:\Control Panel\Desktop' -Name 'ForegroundLockTimeout' -Value $NORMAL_LOCK -Type DWord
Write-Host "  새값: $NORMAL_LOCK (200초 동안 사용자 창 보호)"

# SystemParametersInfo SPI_SETFOREGROUNDLOCKTIMEOUT 즉시 broadcast
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class FocusLock {
    [DllImport("user32.dll", SetLastError=true)]
    public static extern bool SystemParametersInfo(uint uiAction, uint uiParam, uint pvParam, uint fWinIni);
    public const uint SPI_SETFOREGROUNDLOCKTIMEOUT = 0x2001;
    public const uint SPIF_UPDATEINIFILE = 0x01;
    public const uint SPIF_SENDWININICHANGE = 0x02;
}
"@
[FocusLock]::SystemParametersInfo(
    [FocusLock]::SPI_SETFOREGROUNDLOCKTIMEOUT,
    0,
    $NORMAL_LOCK,
    [FocusLock]::SPIF_UPDATEINIFILE -bor [FocusLock]::SPIF_SENDWININICHANGE
) | Out-Null
Write-Host "  broadcast 완료 (재부팅 없이 즉시 적용)"

Write-Host "`n=== 3) 현재 git/conhost spawner 부모 통계 (10s) ==="
$counts = @{}
$end = (Get-Date).AddSeconds(10)
while ((Get-Date) -lt $end) {
    Get-CimInstance Win32_Process -Filter "Name='git.exe' OR Name='conhost.exe'" | ForEach-Object {
        $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($_.ParentProcessId)"
        if ($parent) {
            $key = "$($parent.Name) (PID $($parent.ProcessId))"
            if (-not $counts.ContainsKey($key)) { $counts[$key] = 0 }
            $counts[$key]++
        }
    }
    Start-Sleep -Milliseconds 500
}
$counts.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 8 | ForEach-Object {
    Write-Host ("  {0,4}x  {1}" -f $_.Value, $_.Key)
}
