# 확장자 없는 파일 실행 시도 찾기

Write-Host "=== Startup 폴더 내 확장자 없는 파일 ==="
@(
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup",
    "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"
) | ForEach-Object {
    Get-ChildItem $_ -ErrorAction SilentlyContinue | Where-Object { $_.Extension -eq '' } | Select-Object FullName
}

Write-Host "`n=== 스케줄러 태스크 중 확장자 없는 실행 파일 ==="
Get-ScheduledTask -ErrorAction SilentlyContinue | ForEach-Object {
    $task = $_
    $task.Actions | ForEach-Object {
        $exe = $_.Execute
        if ($exe -and $exe -notmatch '\.\w{1,5}["$]?' -and $exe -notmatch 'cmd|powershell|python|wscript|mshta') {
            Write-Host "Task: $($task.TaskName) | Execute: $exe"
        }
    }
}

Write-Host "`n=== HKCU Run 중 확장자 없는 항목 ==="
$runKey = Get-Item "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -ErrorAction SilentlyContinue
if ($runKey) {
    $runKey.GetValueNames() | ForEach-Object {
        $val = $runKey.GetValue($_)
        if ($val -notmatch '\.\w{2,5}') {
            Write-Host "$_ = $val"
        }
    }
}

Write-Host "`n=== Q드라이브 루트 확장자 없는 파일 ==="
Get-ChildItem "Q:\" -File -ErrorAction SilentlyContinue | Where-Object { $_.Extension -eq '' } | Select-Object Name, FullName, LastWriteTime

Write-Host "`n=== 최근 이벤트 로그 (확장자 관련 오류) ==="
Get-WinEvent -LogName Application -MaxEvents 100 -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -match '확장자|extension|no.*ext|unknown.*file' } |
    Select-Object TimeCreated, Message -First 5 | Format-List

Write-Host "`n=== FindAgent 실행 파일 확인 ==="
Get-ChildItem "C:\KED\FindAgent" -ErrorAction SilentlyContinue | Select-Object Name, Extension, LastWriteTime
