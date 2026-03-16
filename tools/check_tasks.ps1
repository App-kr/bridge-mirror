Get-ScheduledTask | Where-Object {
    $_.TaskName -like '*bridge*' -or
    $_.TaskName -like '*blog*' -or
    $_.TaskName -like '*claude*' -or
    $_.TaskName -like '*naver*' -or
    $_.TaskName -like '*python*'
} | Select-Object TaskName, State, TaskPath | Format-Table -AutoSize
