# set_secret.ps1 — .env 보안 입력 도구
# 사용법: .\tools\set_secret.ps1 SUPABASE_URL
# 사용법: .\tools\set_secret.ps1 SUPABASE_SERVICE_KEY

param([string]$KeyName = "")

$EnvPath = Join-Path $PSScriptRoot ".." ".env"
$EnvPath = [System.IO.Path]::GetFullPath($EnvPath)

if (-not $KeyName) {
    $KeyName = Read-Host "키 이름 입력 (예: SUPABASE_SERVICE_KEY)"
}
if (-not $KeyName) { Write-Host "취소됨."; exit 1 }

# 입력값 마스킹 (화면에 *** 표시)
$SecureValue = Read-Host "$KeyName 값 입력" -AsSecureString
$Value = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
)

if (-not $Value.Trim()) { Write-Host "값이 비어있습니다. 취소됨."; exit 1 }

# .env 파일 업데이트
$content = Get-Content $EnvPath -Raw -Encoding UTF8
$pattern = "(?m)^$([regex]::Escape($KeyName))=.*$"

if ($content -match $pattern) {
    $content = $content -replace $pattern, "$KeyName=$Value"
    Write-Host "✅ $KeyName 업데이트 완료"
} else {
    if (-not $content.EndsWith("`n")) { $content += "`n" }
    $content += "$KeyName=$Value`n"
    Write-Host "✅ $KeyName 추가 완료"
}

[System.IO.File]::WriteAllText($EnvPath, $content, [System.Text.Encoding]::UTF8)
