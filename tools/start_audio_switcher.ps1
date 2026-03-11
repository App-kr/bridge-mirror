# 기존 실행 중인 인스턴스 확인
$running = Get-WmiObject Win32_Process | Where-Object {
    $_.CommandLine -like '*audio_switcher*'
}
if ($running) {
    Write-Host "이미 실행 중 (PID: $($running.ProcessId))"
    exit 0
}

# 새로 실행
$proc = Start-Process -FilePath 'pythonw.exe' `
    -ArgumentList '-X utf8 "Q:\Claudework\bridge base\tools\audio_switcher.py"' `
    -WindowStyle Hidden -PassThru
Start-Sleep 2

$check = Get-WmiObject Win32_Process | Where-Object {
    $_.CommandLine -like '*audio_switcher*'
}
if ($check) {
    Write-Host "실행 확인: PID $($check.ProcessId)"
} else {
    Write-Host "실행 실패"
}
