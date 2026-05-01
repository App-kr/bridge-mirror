# Bridge Work Tracker - 5min interval auto work logging
# 2026-05-01: git child conhost flicker fix
#   Was: & git rev-parse / log / diff / ls-files (7x conhost spawn per run)
#   Now: System.Diagnostics.Process with CreateNoWindow=true (zero conhost)

$ProjectRoot = "Q:\Claudework\bridge base"
$LogFile = "$ProjectRoot\.claude\work-log.txt"
$MaxLogLines = 500

Set-Location $ProjectRoot

# Helper: Run git silently (no conhost spawn)
function Invoke-GitSilent {
    param([string]$Args)
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = "git"
        $psi.Arguments = $Args
        $psi.WorkingDirectory = $ProjectRoot
        $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.CreateNoWindow = $true
        $proc = [System.Diagnostics.Process]::Start($psi)
        if (-not $proc) { return "" }
        $out = $proc.StandardOutput.ReadToEnd()
        $proc.WaitForExit(5000) | Out-Null
        return $out.Trim()
    } catch {
        return ""
    }
}

# --- 1) git 상태 수집 ---
$branch = Invoke-GitSilent "rev-parse --abbrev-ref HEAD"
if (-not $branch) { $branch = "unknown" }
$lastCommit = Invoke-GitSilent 'log -1 --format=%s'
$lastCommitTime = Invoke-GitSilent 'log -1 --format=%ar'
$modifiedFilesRaw = Invoke-GitSilent "diff --name-only"
$modifiedFiles = if ($modifiedFilesRaw) { @($modifiedFilesRaw -split "`n" | Where-Object { $_ }) } else { @() }
$untrackedFilesRaw = Invoke-GitSilent "ls-files --others --exclude-standard"
$untrackedFiles = if ($untrackedFilesRaw) { @($untrackedFilesRaw -split "`n" | Where-Object { $_ }) } else { @() }
$stagedFilesRaw = Invoke-GitSilent "diff --cached --name-only"
$stagedFiles = if ($stagedFilesRaw) { @($stagedFilesRaw -split "`n" | Where-Object { $_ }) } else { @() }

$totalChanged = $modifiedFiles.Count + $untrackedFiles.Count + $stagedFiles.Count

# --- 2) 1시간 이내 활동 체크 ---
$lastCommitEpoch = Invoke-GitSilent 'log -1 --format=%ct'
$nowEpoch = [int][double]::Parse((Get-Date -UFormat %s))
if ($lastCommitEpoch) {
    $minutesAgo = [math]::Round(($nowEpoch - [int]$lastCommitEpoch) / 60)
} else {
    $minutesAgo = 9999
}

# 1시간 이내 커밋이 있거나 수정 파일이 있으면 기록
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
