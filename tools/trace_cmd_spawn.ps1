# 2026-04-28 - Trace cmd/powershell window spawning
$ErrorActionPreference = 'SilentlyContinue'

Write-Host "=== A) Other BRIDGE Python scripts using subprocess WITHOUT CREATE_NO_WINDOW ==="
$bridgeDir = "Q:\Claudework\bridge base"
$results = @()
Get-ChildItem $bridgeDir -Recurse -Filter "*.py" -File -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch '\.venv\\|\\node_modules\\|\\.git\\|\\worktrees\\' } |
    ForEach-Object {
        $content = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue
        if (-not $content) { return }
        # subprocess + .cmd or .bat 호출하면서 CREATE_NO_WINDOW 없는 경우
        if ($content -match 'subprocess\.(run|Popen|call|check_call|check_output)' -and
            $content -match '\.cmd|\.bat|npx|npm\.cmd' -and
            $content -notmatch 'CREATE_NO_WINDOW') {
            $results += [PSCustomObject]@{
                File = $_.FullName.Substring($bridgeDir.Length + 1)
                Lines = ([regex]::Matches($content, 'subprocess\.(run|Popen|call)')).Count
            }
        }
    }
$results | Sort-Object Lines -Descending | Format-Table -AutoSize -Wrap

Write-Host "`n=== B) Currently running cmd.exe / powershell.exe (admin or system) ==="
Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(cmd|powershell|conhost|pwsh)\.exe$' } |
    ForEach-Object {
        $p = $_
        $owner = ""
        try {
            $oi = $p | Invoke-CimMethod -MethodName GetOwner -ErrorAction SilentlyContinue
            if ($oi.User) { $owner = "$($oi.Domain)\$($oi.User)" }
        } catch {}
        [PSCustomObject]@{
            PID = $p.ProcessId
            Parent = $p.ParentProcessId
            Name = $p.Name
            Owner = $owner
            CmdLine = if ($p.CommandLine) { $p.CommandLine.Substring(0,[Math]::Min(140,$p.CommandLine.Length)) } else { '' }
        }
    } | Format-Table -AutoSize -Wrap

Write-Host "`n=== C) Recent task-scheduler events (last 30 min) ==="
$cutoff = (Get-Date).AddMinutes(-30)
Get-ScheduledTask | Where-Object { $_.TaskPath -notlike '\Microsoft\*' } | ForEach-Object {
    $info = $_ | Get-ScheduledTaskInfo
    if ($info.LastRunTime -gt $cutoff) {
        [PSCustomObject]@{
            LastRun = $info.LastRunTime
            Name = ($_.TaskPath + $_.TaskName)
            Result = $info.LastTaskResult
            Exec = ($_.Actions | Select-Object -First 1).Execute
        }
    }
} | Sort-Object LastRun -Descending | Format-Table -AutoSize -Wrap

Write-Host "`n=== D) Conhost (cmd window host) processes ==="
Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'conhost.exe' } |
    Select-Object ProcessId, ParentProcessId,
        @{N='ParentName';E={(Get-CimInstance Win32_Process -Filter "ProcessId=$($_.ParentProcessId)").Name}} |
    Format-Table -AutoSize
