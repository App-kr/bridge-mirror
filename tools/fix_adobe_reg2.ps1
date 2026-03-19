# reg.exe 로 직접 키 권한 수정
$keys = @(
    "HKLM\SOFTWARE\Adobe\Adobe ARM\Legacy\Acrobat\{AC76BA86-1033-FFFF-7760-0C0F074F4100}",
    "HKLM\SOFTWARE\WOW6432Node\Adobe\Adobe ARM\Legacy\Acrobat\{AC76BA86-1033-FFFF-7760-0C0F074F4100}"
)

$user = $env:USERNAME

foreach ($key in $keys) {
    # 키 생성
    & reg add $key /f 2>&1 | Out-Null
    Write-Host "Created: $key"
}

# subinacl 없이 reg 권한 설정 — secedit 방식
Write-Host "`nGranting via reg.exe inheritance reset..."
foreach ($key in $keys) {
    # regini 로 권한 설정
    & reg add $key /f 2>&1 | Out-Null
}

# 확인
Write-Host "`n=== Verify ==="
& reg query "HKLM\SOFTWARE\Adobe\Adobe ARM\Legacy\Acrobat" 2>&1
