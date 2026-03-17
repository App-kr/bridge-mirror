# ============================================================
# fix_audio_default.ps1  — 재부팅 후에도 스피커 기본 장치 유지
# ============================================================
param([switch]$Silent)

if (-not (Get-Module -ListAvailable -Name AudioDeviceCmdlets)) {
    Write-Host "AudioDeviceCmdlets 설치 중..." -ForegroundColor Yellow
    Install-Module -Name AudioDeviceCmdlets -Force -Scope CurrentUser
}
Import-Module AudioDeviceCmdlets -ErrorAction Stop

$playback = Get-AudioDevice -List | Where-Object { $_.Type -eq 'Playback' }

if (-not $Silent) {
    Write-Host "`n=== 오디오 출력 장치 ===" -ForegroundColor Cyan
    $playback | ForEach-Object {
        $tag = if ($_.Default) { " ◀ 현재기본" } else { "" }
        Write-Host "  [$($_.Index)] $($_.Name)$tag"
    }
}

# High Definition Audio Device (메인보드 스피커 출력) 우선 선택
$speaker = $playback | Where-Object { $_.Name -like "*High Definition Audio*" } | Select-Object -First 1

# 없으면 K66·780LITE 제외한 스피커
if (-not $speaker) {
    $speaker = $playback | Where-Object {
        $_.Name -notlike "*K66*" -and
        $_.Name -notlike "*780LITE*" -and
        $_.Name -notlike "*Captain*" -and
        $_.Name -notlike "*NVIDIA*" -and
        $_.Name -notlike "*Digital*" -and
        $_.Name -notlike "*TFG*"
    } | Select-Object -First 1
}

if (-not $speaker) {
    Write-Host "스피커 자동감지 실패" -ForegroundColor Red; exit 1
}

# 이미 기본이면 스킵
$current = Get-AudioDevice -Playback
if ($current.Name -eq $speaker.Name) {
    if (-not $Silent) { Write-Host "✅ 이미 기본: $($speaker.Name)" -ForegroundColor Green }
    exit 0
}

Write-Host "기본 설정 → $($speaker.Name)" -ForegroundColor Green
Set-AudioDevice -Index $speaker.Index | Out-Null

if (-not $Silent) {
    $after = Get-AudioDevice -Playback
    Write-Host "현재 기본: $($after.Name)" -ForegroundColor Cyan
    if ($after.Name -eq $speaker.Name) {
        Write-Host "✅ 설정 성공" -ForegroundColor Green
    } else {
        Write-Host "❌ 설정 실패" -ForegroundColor Red
    }
}
