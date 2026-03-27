# Python 마이그레이션 스크립트 (C/D → Q)
# 관리자 권한 필수

param(
    [switch]$SkipBackup = $false,
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

function Log($msg) {
    $ts = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    Write-Host "[$ts] $msg"
}

function Check-Admin {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# 관리자 체크
if (-not (Check-Admin)) {
    Log "ERROR: 관리자 권한 필요"
    Log "PowerShell을 '관리자 권한으로 실행'해주세요"
    exit 1
}

$Q_ROOT = "Q:\Claudework"
$PYTHON_Q = "$Q_ROOT\Python"
$BACKUP_DIR = "$Q_ROOT\backup\python-migration"

Log "================================"
Log "Python 마이그레이션 시작"
Log "================================"

# 1. C/D 드라이브 Python 검색
Log "`n[1/4] C, D 드라이브에서 Python 검색 중..."

$pythonPaths = @()

# C 드라이브
$cPython = Get-ChildItem "C:\Users\Scarlett\AppData\Local\Programs\Python" -ErrorAction SilentlyContinue -Directory
if ($cPython) {
    $cPython | ForEach-Object {
        $pythonPaths += @{
            Path   = $_.FullName
            Source = "C"
            Version = $_.Name
        }
        Log "  ✓ Found: $($_.FullName)"
    }
}

# D 드라이브
if (Test-Path "D:\") {
    $dPython = Get-ChildItem "D:\" -ErrorAction SilentlyContinue -Filter "*Python*" -Directory
    if ($dPython) {
        $dPython | ForEach-Object {
            $pythonPaths += @{
                Path   = $_.FullName
                Source = "D"
                Version = $_.Name
            }
            Log "  ✓ Found: $($_.FullName)"
        }
    }
}

if ($pythonPaths.Count -eq 0) {
    Log "  ⚠️  C/D 드라이브에서 Python을 찾을 수 없습니다"
    Log "  새로 설치가 필요합니다"
} else {
    Log "  총 $($pythonPaths.Count)개 Python 설치 발견"
}

# 2. 백업 생성
Log "`n[2/4] 백업 생성 중..."

if (-not (Test-Path $BACKUP_DIR)) {
    New-Item -ItemType Directory -Path $BACKUP_DIR -Force | Out-Null
}

foreach ($py in $pythonPaths) {
    $backupName = "$($py.Source)_$($py.Version)_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    $backupPath = "$BACKUP_DIR\$backupName"

    Log "  복사 중: $($py.Version) → $backupPath"
    Copy-Item -Path $py.Path -Destination $backupPath -Recurse -Force -ErrorAction SilentlyContinue
    Log "  ✓ 백업 완료"
}

# 3. Q로 복사
Log "`n[3/4] Q 드라이브로 이동 중..."

if (-not (Test-Path $PYTHON_Q)) {
    New-Item -ItemType Directory -Path $PYTHON_Q -Force | Out-Null
    Log "  폴더 생성: $PYTHON_Q"
}

foreach ($py in $pythonPaths) {
    $destPath = "$PYTHON_Q\$($py.Version)"
    if (Test-Path $destPath) {
        Log "  ⚠️  이미 존재: $destPath (스킵)"
        continue
    }

    Log "  복사 중: $($py.Version) → Q 드라이브"
    Copy-Item -Path $py.Path -Destination $destPath -Recurse -Force
    Log "  ✓ 완료: $destPath"
}

# 4. Python 최신 버전 설치 (필요시)
Log "`n[4/4] Python 3.14 설치 확인..."

$py314Path = "$PYTHON_Q\Python314"
if (-not (Test-Path "$py314Path\python.exe")) {
    Log "  Python 3.14 다운로드 중 (scoop 사용)..."

    # scoop 설치 확인
    if (-not (Get-Command scoop -ErrorAction SilentlyContinue)) {
        Log "  scoop 설치 중..."
        iex (New-Object Net.WebClient).DownloadString('https://get.scoop.sh')
    }

    Log "  scoop install python@3.14 실행..."
    scoop install python@3.14 2>&1 | ForEach-Object { Log "    $_" }

    # scoop 설치 위치에서 Q로 복사
    $scoopPython = "$env:USERPROFILE\scoop\apps\python\current"
    if (Test-Path $scoopPython) {
        Copy-Item -Path $scoopPython -Destination $py314Path -Recurse -Force
        Log "  ✓ Python 3.14 복사 완료"
    }
} else {
    Log "  ✓ Python 3.14이 이미 Q에 있습니다: $py314Path"
}

# 5. PATH 환경변수 업데이트
Log "`n[5/5] 환경변수 설정 중..."

$pythonExePaths = Get-ChildItem "$PYTHON_Q" -Filter "python.exe" -Recurse | ForEach-Object { $_.Directory.FullName } | Select-Object -Unique

foreach ($pyPath in $pythonExePaths) {
    $currentPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
    if ($currentPath -notlike "*$pyPath*") {
        $newPath = "$pyPath;$currentPath"
        [Environment]::SetEnvironmentVariable("PATH", $newPath, "Machine")
        Log "  ✓ PATH 추가: $pyPath"
    } else {
        Log "  ⚠️  이미 설정됨: $pyPath"
    }
}

# 6. pip 업그레이드
Log "`n[6/5] pip 업그레이드 중..."

foreach ($pyPath in $pythonExePaths) {
    $pythonExe = "$pyPath\python.exe"
    if (Test-Path $pythonExe) {
        Log "  $pythonExe -m pip install --upgrade pip"
        & $pythonExe -m pip install --upgrade pip 2>&1 | ForEach-Object { Log "    $_" }
    }
}

Log "`n================================"
Log "✅ 마이그레이션 완료!"
Log "================================"
Log "`n다음 경로들이 이제 Q에 있습니다:"
Get-ChildItem $PYTHON_Q -Filter "python.exe" -Recurse | ForEach-Object {
    Log "  - $($_.FullName)"
}

Log "`n다음 명령으로 테스트:"
Log "  python --version"
Log "  py --version"

Log "`n[선택] 기존 C/D의 Python 삭제 (백업 후):"
Log "  Remove-Item -Path 'C:\Users\Scarlett\AppData\Local\Programs\Python' -Recurse -Force"

Log "`nPowerShell을 다시 시작해야 변경사항이 적용됩니다."
