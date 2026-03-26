# 각 스케줄러 작업의 Hidden/창 설정 확인
$tasks = Get-ScheduledTask | ForEach-Object {
    $t = $_
    $actions = $t.Actions | ForEach-Object { "$($_.Execute) $($_.Arguments)" }
    $settings = $t.Settings
    $principal = $t.Principal
    [PSCustomObject]@{
        Name       = $t.TaskName
        Hidden     = $settings.Hidden
        RunLevel   = $principal.RunLevel
        LogonType  = $principal.LogonType
        Command    = ($actions -join "; ").Substring(0, [Math]::Min(80, ($actions -join "; ").Length))
    }
} | Where-Object { $_.Command -match "powershell|python|\.py|bridge|claude|bat" }

$tasks | Format-Table -AutoSize

Write-Host "`n=== Hidden=False (창이 뜨는 작업) ===" -ForegroundColor Red
$tasks | Where-Object { $_.Hidden -eq $false -or $_.Hidden -eq $null } | Format-Table -AutoSize
