# Bridge Work Tracker — 5분 간격 자동 작업 기록
# 경로: Q:\Claudework\bridge base\.claude\work-tracker.ps1
# 보안: 키/비밀번호 절대 기록하지 않음. git 상태만 추적.

$ProjectRoot = "Q:\Claudework\bridge base"
$LogFile = "$ProjectRoot\.claude\work-log.txt"
$MaxLogLines = 500

Set-Location $ProjectRoot

# --- 1) git 상태 수집 ---
try {
    $branch = git rev-parse --abbrev-ref HEAD 2>$null
    if (-not $branch) { $branch = "unknown" }
    $lastCommit = git log -1 --format="%s" 2>$null
    $lastCommitTime = git log -1 --format="%ar" 2>$null
    $modifiedFiles = @(git diff --name-only 2>$null)
    $untrackedFiles = @(git ls-files --others --exclude-standard 2>$null)
    $stagedFiles = @(git diff --cached --name-only 2>$null)
} catch {
    $branch = "error"
    $lastCommit = "git error"
    $lastCommitTime = ""
    $modifiedFiles = @()
    $untrackedFiles = @()
    $stagedFiles = @()
}

$totalChanged = $modifiedFiles.Count + $untrackedFiles.Count + $stagedFiles.Count

# --- 2) 1시간 이내 활동 체크 ---
$lastCommitEpoch = git log -1 --format="%ct" 2>$null
$nowEpoch = [int][double]::Parse((Get-Date -UFormat %s))
if ($lastCommitEpoch) {
    $minutesAgo = [math]::Round(($nowEpoch - [int]$lastCommitEpoch) / 60)
} else {
    $minutesAgo = 9999
}

# 1시간(60분) 이내 커밋이 있거나 수정 파일이 있으면 기록
if ($minutesAgo -gt 60 -and $totalChanged -eq 0) {
    exit 0
}

# --- 3) 작업명 추정 ---
if ($totalChanged -gt 0) {
    $allFiles = @()
    if ($modifiedFiles) { $allFiles += $modifiedFiles }
    if ($untrackedFiles) { $allFiles += $untrackedFiles }
    if ($stagedFiles) { $allFiles += $stagedFiles }
    $topFile = $allFiles | Select-Object -First 1
    $others = $totalChanged - 1
    $workName = "editing: $topFile (+$others files)"
} elseif ($lastCommit) {
    $workName = "last: $lastCommit"
} else {
    $workName = "idle"
}

# --- 4) 로그 기록 ---
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$entry = "[$timestamp] Branch:$branch | $workName | commit:$lastCommitTime | changed:$totalChanged"

if (-not (Test-Path $LogFile)) {
    New-Item -Path $LogFile -ItemType File -Force | Out-Null
}

Add-Content -Path $LogFile -Value $entry -Encoding UTF8

# --- 5) 로그 크기 제한 ---
$lines = Get-Content $LogFile -Encoding UTF8
if ($lines.Count -gt $MaxLogLines) {
    $lines | Select-Object -Last $MaxLogLines | Set-Content $LogFile -Encoding UTF8
}
