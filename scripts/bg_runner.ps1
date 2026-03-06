# ═══════════════════════════════════════════════════════════
# BRIDGE Background Runner
# 
# 이 파일을 bridge base 루트에 두고,
# 모든 자동화 스크립트에서 import하여 사용
#
# 사용법:
#   . "Q:\Claudework\bridge base\scripts\bg_runner.ps1"
#   Invoke-BridgeBG -Python "scripts/parsers/parse_jobs.py --input raw.txt --db master.db"
#   Invoke-BridgeBG -Node "scripts/generators/generate_job_docx.js --input job.json"
#   Invoke-BridgeBG -Command "any command here"
# ═══════════════════════════════════════════════════════════

$BRIDGE_ROOT = "Q:\Claudework\bridge base"
$LOG_DIR = Join-Path $BRIDGE_ROOT "logs"

# 로그 디렉토리 생성
if (-not (Test-Path $LOG_DIR)) {
    New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null
}

function Invoke-BridgeBG {
    param(
        [string]$Python,
        [string]$Node,
        [string]$Command,
        [string]$LogName = "bg_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    )

    $logFile = Join-Path $LOG_DIR "$LogName.log"
    $errorLog = Join-Path $LOG_DIR "$LogName.error.log"

    if ($Python) {
        $fullCmd = "cd '$BRIDGE_ROOT'; python $Python *> '$logFile' 2> '$errorLog'"
    }
    elseif ($Node) {
        $fullCmd = "cd '$BRIDGE_ROOT'; node $Node *> '$logFile' 2> '$errorLog'"
    }
    elseif ($Command) {
        $fullCmd = "cd '$BRIDGE_ROOT'; $Command *> '$logFile' 2> '$errorLog'"
    }
    else {
        Write-Error "Python, Node, 또는 Command 중 하나 지정 필요"
        return
    }

    # 핵심: -WindowStyle Hidden으로 백그라운드 실행
    Start-Process -FilePath "powershell" `
        -ArgumentList "-WindowStyle Hidden -ExecutionPolicy Bypass -Command `"$fullCmd`"" `
        -WindowStyle Hidden `
        -WorkingDirectory $BRIDGE_ROOT

    Write-Host "[BG] 실행됨 → 로그: $logFile" -ForegroundColor DarkGray
}

# ─── 타스크 스케줄러 등록 헬퍼 ───────────────────────────
function Register-BridgeTask {
    param(
        [string]$Name,
        [string]$VbsPath = (Join-Path $BRIDGE_ROOT "scripts\silent_run.vbs"),
        [int]$IntervalHours = 6,
        [string]$Description = "BRIDGE auto task (background)"
    )

    $action = New-ScheduledTaskAction `
        -Execute "wscript.exe" `
        -Argument """$VbsPath""" `
        -WorkingDirectory $BRIDGE_ROOT

    $trigger = New-ScheduledTaskTrigger `
        -Once -At (Get-Date) `
        -RepetitionInterval (New-TimeSpan -Hours $IntervalHours)

    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
        -MultipleInstances IgnoreNew

    Register-ScheduledTask `
        -TaskName $Name `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Description $Description `
        -Force

    Write-Host "[TASK] '$Name' 등록 완료 (${IntervalHours}시간 간격)" -ForegroundColor Green
}

# ─── 사용 예시 ───────────────────────────────────────────
# . "Q:\Claudework\bridge base\scripts\bg_runner.ps1"
#
# 1) 파서 백그라운드 실행:
# Invoke-BridgeBG -Python "scripts/parsers/parse_jobs.py --input raw.txt --db master.db" -LogName "parser"
#
# 2) docx 생성 백그라운드:
# Invoke-BridgeBG -Node "scripts/generators/generate_job_docx.js --input job.json" -LogName "docx_gen"
#
# 3) Craigslist 자동포스팅 타스크 등록 (6시간):
# Register-BridgeTask -Name "BRIDGE_CL_AutoPost" -IntervalHours 6
#
# 4) 타스크 확인/삭제:
# Get-ScheduledTask -TaskName "BRIDGE_*"
# Unregister-ScheduledTask -TaskName "BRIDGE_CL_AutoPost" -Confirm:$false
