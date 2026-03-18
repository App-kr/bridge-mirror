# audio-startup.ps1
# 로그인 시 스피커를 기본 오디오 장치로 강제 설정 (헤드셋 자동 선택 방지)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$logDir = "Q:\Claudework\bridge base\logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$logFile = "$logDir\audio-startup.log"

function Log($msg) {
    $ts = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    Add-Content -Path $logFile -Value "[$ts] $msg" -Encoding UTF8
}

# AudioDeviceCmdlets 모듈 확인
if (-not (Get-Module -ListAvailable -Name AudioDeviceCmdlets)) {
    Log "ERROR: AudioDeviceCmdlets 모듈 없음 — 설치 필요"
    exit 1
}

Import-Module AudioDeviceCmdlets

# 헤드셋이 연결되어 있어도 스피커를 기본 재생 장치로 강제 설정
$devices = Get-AudioDevice -List

$speaker = $devices | Where-Object {
    $_.Type -eq "Playback" -and
    $_.Name -like "*High Definition Audio Device*" -and
    $_.Name -notlike "*NVIDIA*" -and
    $_.Name -notlike "*Digital*"
}

$standMic = $devices | Where-Object {
    $_.Type -eq "Recording" -and
    $_.Name -like "*stand*"
}

if ($speaker) {
    Set-AudioDevice -Index $speaker.Index | Out-Null
    Log "재생 장치 → $($speaker.Name)"
} else {
    Log "WARNING: 스피커 장치를 찾을 수 없음"
}

if ($standMic) {
    Set-AudioDevice -Index $standMic.Index | Out-Null
    Log "녹음 장치 → $($standMic.Name)"
} else {
    Log "WARNING: 스탠드 마이크를 찾을 수 없음 — 기본 마이크 유지"
}

Log "완료"
