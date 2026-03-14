Write-Host "=== BridgeCraigslistRPA 태스크 상세 ==="
$t = Get-ScheduledTask -TaskName 'BridgeCraigslistRPA' -ErrorAction SilentlyContinue
if ($t) {
    Write-Host "State: $($t.State)"
    $t.Actions | ForEach-Object {
        Write-Host "Execute: $($_.Execute)"
        Write-Host "Arguments: $($_.Arguments)"
    }
    $t.Triggers | ForEach-Object {
        Write-Host "Trigger: $($_.CimClass.CimClassName)"
    }
}

Write-Host "`n=== Q:\Claudework\bridge 폴더 내용 ==="
Get-ChildItem "Q:\Claudework\bridge" -ErrorAction SilentlyContinue | Select-Object Name, Extension, LastWriteTime

Write-Host "`n=== Q:\Claudework\start_craig.vbs 내용 ==="
if (Test-Path "Q:\Claudework\start_craig.vbs") {
    Get-Content "Q:\Claudework\start_craig.vbs"
}

Write-Host "`n=== Q:\Claudework\bridge\start_craig.vbs 내용 ==="
if (Test-Path "Q:\Claudework\bridge\start_craig.vbs") {
    Get-Content "Q:\Claudework\bridge\start_craig.vbs"
}

Write-Host "`n=== 로그온 시 실행 태스크 중 bridge 경로 포함 ==="
Get-ScheduledTask -ErrorAction SilentlyContinue | ForEach-Object {
    $tn = $_.TaskName
    $_.Actions | ForEach-Object {
        if ($_.Arguments -match 'bridge' -and $_.Arguments -notmatch '"Q:\\Claudework\\bridge') {
            Write-Host "⚠️ 따옴표 없이 bridge 경로: Task=$tn"
            Write-Host "   Execute: $($_.Execute)"
            Write-Host "   Arguments: $($_.Arguments)"
        }
    }
}
