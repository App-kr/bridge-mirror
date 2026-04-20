$ErrorActionPreference = 'SilentlyContinue'

Write-Host "=== A) Windows 'Restart apps' 설정 ==="
Write-Host "  HKCU...\Winlogon\RestartApps = $((Get-ItemProperty 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Winlogon' -Name 'RestartApps' -ErrorAction SilentlyContinue).RestartApps)"
Write-Host "  HKCU\Control Panel\Desktop\AutoRestartShell = $((Get-ItemProperty 'HKCU:\Control Panel\Desktop' -Name 'AutoRestartShell' -ErrorAction SilentlyContinue).AutoRestartShell)"
Write-Host "  HKCU...\RestartSession\RestartLastSession = $((Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced' -Name 'RestartApps' -ErrorAction SilentlyContinue).RestartApps)"
Write-Host ""
Write-Host "  HKLM Policy ExplorerRunOnceOverride:"
Get-ItemProperty 'HKLM:\Software\Policies\Microsoft\Windows\System' -ErrorAction SilentlyContinue | Format-List DisableAutomaticRestartSignOn

Write-Host "`n=== B) Hancom 관련 자동실행 레지스트리 ==="
$runKeys = @(
  'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run',
  'HKLM:\Software\Microsoft\Windows\CurrentVersion\Run',
  'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run'
)
foreach ($k in $runKeys) {
    Get-ItemProperty $k -ErrorAction SilentlyContinue | ForEach-Object {
        $_.PSObject.Properties | Where-Object {
            $_.Name -notmatch '^PS' -and $_.Value -match 'HNC|Hancom|Hwp|Hnc'
        } | ForEach-Object {
            Write-Host "$k :: $($_.Name) = $($_.Value)"
        }
    }
}

Write-Host "`n=== C) 현재 실행 중인 HWP 관련 프로세스 ==="
Get-Process | Where-Object { $_.Name -match 'Hwp|Hnc|Hancom|HManager|HOfficeLite' } | Select-Object Name, Id, Path | Format-Table -AutoSize

Write-Host "`n=== D) HWP ProgID / LastOpenFiles ==="
Get-ItemProperty 'HKCU:\Software\HNC\Hwp\11.0\HwpFrame\AppState' -ErrorAction SilentlyContinue | Out-String | Write-Host
Get-ChildItem 'HKCU:\Software\HNC\Hwp\11.0' -ErrorAction SilentlyContinue | Select-Object PSChildName | Format-Table -AutoSize

Write-Host "`n=== E) Windows 11 StartupApps 기본앱 ==="
Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run' -ErrorAction SilentlyContinue | Format-List *

Write-Host "`n=== F) 전체 ~$*.hwp 잠금파일 검색 (Q/D 드라이브) ==="
@('Q:\Claudework','C:\Users\Scarlett\Desktop','C:\Users\Scarlett\Documents','C:\Users\Scarlett\Downloads') | ForEach-Object {
    if (Test-Path $_) {
        Get-ChildItem $_ -Recurse -Include '~$*.hwp','~$*.hwpx','*.asv' -File -Force -ErrorAction SilentlyContinue |
            Select-Object FullName, Length, LastWriteTime | Format-Table -AutoSize
    }
}
