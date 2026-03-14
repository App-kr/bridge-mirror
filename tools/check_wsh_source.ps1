# WSH 오류 원인 추적 — wscript.exe 호출 항목 전수 점검

Write-Host "=== 스케줄러에서 wscript.exe 호출하는 태스크 ==="
Get-ScheduledTask -ErrorAction SilentlyContinue | ForEach-Object {
    $tn = $_.TaskName
    $_.Actions | ForEach-Object {
        if ($_.Execute -match 'wscript' -or $_.Arguments -match 'wscript') {
            Write-Host "Task: $tn"
            Write-Host "  Execute : $($_.Execute)"
            Write-Host "  Arguments: $($_.Arguments)"
        }
    }
}

Write-Host "`n=== HKCU Run 전체 (스크립트로 정확히 확인) ==="
$key = Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -ErrorAction SilentlyContinue
$key.PSObject.Properties | Where-Object { $_.Name -notmatch '^PS' } | ForEach-Object {
    Write-Host "$($_.Name) = $($_.Value)"
}

Write-Host "`n=== HKLM Run 전체 ==="
$key2 = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -ErrorAction SilentlyContinue
$key2.PSObject.Properties | Where-Object { $_.Name -notmatch '^PS' } | ForEach-Object {
    Write-Host "$($_.Name) = $($_.Value)"
}

Write-Host "`n=== Startup 폴더 바로가기 대상 전체 ==="
$startupPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
Get-ChildItem $startupPath -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_.Extension -eq '.lnk') {
        $shell = New-Object -ComObject WScript.Shell
        $sc = $shell.CreateShortcut($_.FullName)
        Write-Host "[$($_.Name)]"
        Write-Host "  Target: $($sc.TargetPath)"
        Write-Host "  Args  : $($sc.Arguments)"
    } else {
        Write-Host "[$($_.Name)] - 바로가기 아님"
    }
}

Write-Host "`n=== AudioAutoSwitcher 태스크 XML 원문 ==="
$xml = [xml](Export-ScheduledTask -TaskName 'AudioAutoSwitcher' -ErrorAction SilentlyContinue)
$xml.Task.Actions.Exec | ForEach-Object {
    Write-Host "Command: $($_.Command)"
    Write-Host "Arguments: $($_.Arguments)"
}
