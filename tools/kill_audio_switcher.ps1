$procs = Get-WmiObject Win32_Process | Where-Object {
    $_.Name -eq 'python.exe' -and $_.CommandLine -like '*audio_switcher*'
}
foreach ($p in $procs) {
    Write-Host "종료: PID $($p.ProcessId)"
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
if ($procs.Count -eq 0) { Write-Host "실행중인 audio_switcher 없음" }
else { Write-Host "$($procs.Count)개 종료 완료" }
