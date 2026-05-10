$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# OS 레벨 — git.exe 의 콘솔 호스트 설정 변경
# HKCU\Console\<full-path-with-underscores> 에 WindowAlpha=0, 1x1 size

$gitPaths = @(
    "Q:_Code_Git_mingw64_bin_git.exe",
    "Q:_Code_Git_cmd_git.exe",
    "Q:_Code_Git_bin_bash.exe",
    "Q:_Code_Git_usr_bin_bash.exe",
    "Q:_Code_Git_bin__usr_bin_bash.exe"
)

foreach ($path in $gitPaths) {
    $key = "HKCU:\Console\$path"
    if (-not (Test-Path $key)) {
        New-Item -Path $key -Force | Out-Null
    }
    # WindowAlpha 0~255 (255=opaque, 0=transparent) - 일부 Windows 빌드만 지원
    Set-ItemProperty -Path $key -Name "WindowAlpha" -Value 0 -Type DWord
    # ScreenBufferSize / WindowSize - 1x1 픽셀
    Set-ItemProperty -Path $key -Name "WindowSize" -Value 0x00010001 -Type DWord
    # 위치 화면 밖
    Set-ItemProperty -Path $key -Name "WindowPosition" -Value 0xFFFFFFFF -Type DWord
    # ForceV2 0 = legacy console (일부 spawn 차단)
    Set-ItemProperty -Path $key -Name "ForceV2" -Value 0 -Type DWord
    # Default visible state - hide
    Set-ItemProperty -Path $key -Name "QuickEdit" -Value 0 -Type DWord
    Set-ItemProperty -Path $key -Name "InsertMode" -Value 0 -Type DWord
    Write-Host "  Configured: $key"
}

# 글로벌 Console - ForceV2=0 (모든 콘솔 legacy 모드)
$globalKey = "HKCU:\Console"
Set-ItemProperty -Path $globalKey -Name "ForceV2" -Value 0 -Type DWord -Force
Write-Host "  Global ForceV2=0 (Legacy console mode)"

Write-Host ""
Write-Host "=== Verify ==="
foreach ($path in $gitPaths) {
    $key = "HKCU:\Console\$path"
    if (Test-Path $key) {
        $alpha = (Get-ItemProperty $key -Name WindowAlpha -ErrorAction SilentlyContinue).WindowAlpha
        Write-Host ("  ${path}: Alpha=$alpha")
    }
}
