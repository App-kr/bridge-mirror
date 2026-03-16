# Export AudioAutoSwitcher XML to see triggers
$taskNames = @("AudioAutoSwitcher", "AudioSwitcher", "BridgeBlogAuto", "Afternoon-Monitor", "AutoBackup5min", "Final-Backup")

foreach ($name in $taskNames) {
    $t = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($t) {
        Write-Host "=== Task: $name ==="
        Write-Host "State: $($t.State)"

        # Get triggers via CIM
        $taskPath = if ($t.TaskPath -ne "\") { $t.TaskPath + $name } else { "\" + $name }
        $xml = Export-ScheduledTask -TaskName $name -TaskPath $t.TaskPath -ErrorAction SilentlyContinue

        # Parse trigger info from XML
        if ($xml) {
            $xmlDoc = [xml]$xml
            $triggers = $xmlDoc.Task.Triggers
            Write-Host "Triggers:"
            if ($triggers) {
                $triggers.ChildNodes | ForEach-Object {
                    Write-Host "  Type: $($_.LocalName)"
                    if ($_.UserId) { Write-Host "  UserId: $($_.UserId)" }
                    if ($_.StartBoundary) { Write-Host "  StartBoundary: $($_.StartBoundary)" }
                    if ($_.Repetition) {
                        Write-Host "  RepetitionInterval: $($_.Repetition.Interval)"
                    }
                }
            } else {
                Write-Host "  (no triggers)"
            }

            # Print actions
            $actions = $xmlDoc.Task.Actions
            Write-Host "Actions:"
            if ($actions) {
                $actions.ChildNodes | ForEach-Object {
                    if ($_.Exec) {
                        Write-Host "  Execute: $($_.Exec.Command)"
                        Write-Host "  Arguments: $($_.Exec.Arguments)"
                    }
                }
            }
        }
        Write-Host ""
    }
}
