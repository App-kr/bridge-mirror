# List ALL scheduled tasks with their full action details
$tasks = Get-ScheduledTask -ErrorAction SilentlyContinue

Write-Host "=== ALL Scheduled Tasks with Actions ==="
foreach ($t in $tasks) {
    foreach ($action in $t.Actions) {
        $exe = $action.Execute
        $args = $action.Arguments
        # Flag wscript or any bridge-related task
        if ($exe -like "*wscript*" -or $exe -like "*cscript*" -or
            $args -like "*bridge*" -or $args -like "*Claudework*" -or
            $t.TaskName -like "*Audio*" -or $t.TaskName -like "*Bridge*" -or
            $t.TaskName -like "*craig*" -or $t.TaskName -like "*RPA*") {
            Write-Host ""
            Write-Host "Task: $($t.TaskName)"
            Write-Host "  Path: $($t.TaskPath)"
            Write-Host "  State: $($t.State)"
            Write-Host "  Execute: $exe"
            Write-Host "  Arguments: $args"
            if ($args -like "*bridge base*" -and $args -notlike '*"Q:\Claudework\bridge base*') {
                Write-Host "  *** WARNING: Path may be unquoted! ***"
            }
        }
    }
}

Write-Host ""
Write-Host "=== Tasks with wscript in Execute path ==="
$tasks | ForEach-Object {
    $t = $_
    $t.Actions | Where-Object { $_.Execute -like "*wscript*" } | ForEach-Object {
        Write-Host "Task: $($t.TaskName)"
        Write-Host "  Execute: $($_.Execute)"
        Write-Host "  Arguments: $($_.Arguments)"
        Write-Host ""
    }
}
