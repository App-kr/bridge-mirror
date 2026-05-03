# BRIDGE Email Autoresponder Daemon - Hidden Background
# - CMD 창 안 뜸 (pythonw.exe + Hidden)
# - 로그온/부팅 시 자동 시작
# - 죽으면 1분 내 자동 재시작
# - 단일 인스턴스 보장 (MultipleInstances=IgnoreNew)
# - 600초(10분)마다 inbox 폴링 — 코드 내장 루프

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { Write-Host "[FAIL] Admin required (관리자 권한으로 실행)" -ForegroundColor Red; exit 1 }

$taskName  = "BRIDGE_EmailAutoresponder_Daemon"
$pythonExe = "Q:\Phtyon 3\pythonw.exe"
$script    = "Q:\Claudework\bridge base\tools\email_autoresponder.py"
$workDir   = "Q:\Claudework\bridge base"

if (-not (Test-Path $script)) {
    Write-Host "[FAIL] $script missing" -ForegroundColor Red
    exit 1
}

# 기존 daemon 태스크 정리
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# 기존 1회성 태스크 비활성화 (daemon이 24시간 돌므로 중복 불필요)
foreach ($legacy in "BRIDGE_EmailAutoresponder", "BRIDGE_EmailAutoresponder_Dawn", "BRIDGE_EmailAutoresponder_Night") {
    $t = Get-ScheduledTask -TaskName $legacy -ErrorAction SilentlyContinue
    if ($t -and $t.State -ne "Disabled") {
        Disable-ScheduledTask -TaskName $legacy -ErrorAction SilentlyContinue | Out-Null
        Write-Host "[INFO] disabled legacy task: $legacy"
    }
}

# Action: pythonw.exe (CMD창 미발생) + --force (업무시간 무관 무한 루프)
$action = New-ScheduledTaskAction `
    -Execute "`"$pythonExe`"" `
    -Argument "-X utf8 `"$script`" --force" `
    -WorkingDirectory $workDir

# Trigger: 로그온 + 부팅 (둘 다 — 어느 쪽이든 가장 빠른 시점에 시작)
$triggers = @(
    (New-ScheduledTaskTrigger -AtLogOn),
    (New-ScheduledTaskTrigger -AtStartup)
)

# Settings: 영구 가동 + 자동 재시작 + Hidden + 단일 인스턴스
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -RestartCount 9999 `
    -ExecutionTimeLimit (New-TimeSpan -Days 3650) `
    -MultipleInstances IgnoreNew `
    -Hidden

# Principal: Interactive 사용자 권한 (네트워크 + Gmail IMAP/SMTP 접근 위해)
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $triggers `
    -Settings $settings `
    -Principal $principal `
    -Description "BRIDGE Email Auto Responder - Hidden daemon (10min poll, restart on crash, no CMD)" | Out-Null

# 즉시 시작
Start-ScheduledTask -TaskName $taskName
Start-Sleep -Seconds 5
$info = Get-ScheduledTaskInfo -TaskName $taskName
Write-Host ""
Write-Host "[OK] $taskName 등록 완료" -ForegroundColor Green
Write-Host "  State        : $((Get-ScheduledTask -TaskName $taskName).State)"
Write-Host "  LastRun      : $($info.LastRunTime)"
Write-Host "  LastResult   : $($info.LastTaskResult)"

# 프로세스 확인
$proc = Get-WmiObject Win32_Process -Filter "Name='pythonw.exe'" |
    Where-Object { $_.CommandLine -like "*email_autoresponder*" } |
    Select-Object -First 1
if ($proc) {
    Write-Host "  Running PID  : $($proc.ProcessId)" -ForegroundColor Green
} else {
    Write-Host "  Running PID  : (still starting — log file에서 확인)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "검증 방법:"
Write-Host "  Get-Content 'Q:\Claudework\logs\email_autoresponder.log' -Tail 10 -Wait"
Write-Host "  텔레그램에서 봇이 메일 처리 알림 정상 도착 확인"
