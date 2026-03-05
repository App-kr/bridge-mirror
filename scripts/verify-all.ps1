[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Import-Module AudioDeviceCmdlets

Write-Host "========== 1. 장치 상태 ==========" -ForegroundColor Cyan
$playback = Get-AudioDevice -Playback
$recording = Get-AudioDevice -Recording
Write-Host "현재 출력: $($playback.Name)"
Write-Host "현재 입력: $($recording.Name)"

Write-Host ""
Write-Host "전체 장치:"
Get-AudioDevice -List | Select-Object Index, Default, Type, Name | Format-Table -AutoSize

$hasCaptain = Get-AudioDevice -List | Where-Object { $_.Name -like "*Captain*" }
if ($hasCaptain) {
    Write-Host ">> Captain 780LITE: 감지됨 (헤드셋 ON)" -ForegroundColor Green
} else {
    Write-Host ">> Captain 780LITE: 없음 (헤드셋 OFF)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========== 2. EqualizerAPO 상태 ==========" -ForegroundColor Cyan

# Check if EqualizerAPO is installed on any device
$eqApoClsid = "D9BD8B0A-1069-4AB2-A0EB-4B5B29CE0D88"
$renderPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render"
$eqConfigured = 0

Get-ChildItem $renderPath -ErrorAction SilentlyContinue | ForEach-Object {
    $fxPath = Join-Path $_.PSPath "FxProperties"
    if (Test-Path $fxPath) {
        $fx = Get-ItemProperty $fxPath -ErrorAction SilentlyContinue
        $allProps = $fx | Get-Member -MemberType NoteProperty | ForEach-Object { $_.Name }
        foreach ($prop in $allProps) {
            $val = $fx.$prop
            if ($val -is [string] -and $val -like "*$eqApoClsid*") {
                $propPath2 = Join-Path $_.PSPath "Properties"
                if (Test-Path $propPath2) {
                    $p = Get-ItemProperty $propPath2 -ErrorAction SilentlyContinue
                    $devName = $p.'{a45c254e-df1c-4efd-8020-67d146a850e0},2'
                    Write-Host ">> EqualizerAPO 적용됨: $devName" -ForegroundColor Green
                    $eqConfigured++
                }
                break
            }
        }
    }
}

if ($eqConfigured -eq 0) {
    Write-Host ">> EqualizerAPO: 어떤 장치에도 적용 안 됨! DeviceSelector 실행 필요" -ForegroundColor Red
}

Write-Host ""
Write-Host "========== 3. EQ 설정 파일 ==========" -ForegroundColor Cyan
$configFile = "C:\Program Files\EqualizerAPO\config\config.txt"
$boostFile = "C:\Program Files\EqualizerAPO\config\footstep-boost.txt"

Write-Host "config.txt:"
Get-Content $configFile -ErrorAction SilentlyContinue
Write-Host ""
Write-Host "footstep-boost.txt:"
Get-Content $boostFile -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "========== 4. F9 토글 테스트 ==========" -ForegroundColor Cyan
# Simulate toggle
$toggleResult = & "Q:\Claudework\bridge base\scripts\audio-toggle.ps1"
Write-Host "토글 결과: $toggleResult"
$afterPlayback = (Get-AudioDevice -Playback).Name
$afterRecording = (Get-AudioDevice -Recording).Name
Write-Host "전환 후 출력: $afterPlayback"
Write-Host "전환 후 입력: $afterRecording"

# Toggle back
$toggleBack = & "Q:\Claudework\bridge base\scripts\audio-toggle.ps1"
Write-Host "복원 결과: $toggleBack"
$finalPlayback = (Get-AudioDevice -Playback).Name
$finalRecording = (Get-AudioDevice -Recording).Name
Write-Host "복원 후 출력: $finalPlayback"
Write-Host "복원 후 입력: $finalRecording"
