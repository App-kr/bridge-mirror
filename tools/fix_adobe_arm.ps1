# AdobeARMHelper.exe 더미 파일 미리 생성 + 전체 권한
$armFile = "C:\Program Files (x86)\Common Files\Adobe\ARM\1.0\AdobeARMHelper.exe"
$armDir  = "C:\Program Files (x86)\Common Files\Adobe\ARM\1.0"

# 폴더 확인/생성
New-Item -ItemType Directory -Path $armDir -Force -ErrorAction SilentlyContinue | Out-Null

# 더미 파일 생성
[System.IO.File]::WriteAllBytes($armFile, [byte[]]@(0x4D,0x5A))  # MZ header
Write-Host "Created dummy: $armFile"

# 파일 권한 전체 허용
& takeown /F $armFile 2>&1 | Out-Null
& icacls $armFile /grant "Everyone:F" /C /Q 2>&1 | Out-Null
& icacls $armDir  /grant "Everyone:(OI)(CI)F" /T /C /Q 2>&1 | Out-Null
Write-Host "Permissions set. Ready to install."
