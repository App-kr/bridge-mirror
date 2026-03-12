# 5분마다 실행되는 실제 백업 데몬
# 저장: Claude JSONL + PSReadLine history + 세션 스냅샷

$agPath    = [System.Environment]::GetFolderPath("ApplicationData") + "\AntiGravity"
$backupDir = $agPath + "\SessionBackups"
$claudeDir = [System.Environment]::GetFolderPath("UserProfile") + "\.claude\projects"
$psHistory = [System.Environment]::GetFolderPath("ApplicationData") + "\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt"
$logFile   = $backupDir + "\backup-daemon.log"

if (-not (Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir -Force | Out-Null }

function Write-Log($msg) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

Write-Log "백업 데몬 시작"

while ($true) {
    try {
        $ts = Get-Date -Format 'yyyyMMdd_HHmmss'
        $snapDir = $backupDir + "\snap_" + $ts
        New-Item -ItemType Directory -Path $snapDir -Force | Out-Null

        # 1. Claude JSONL 대화기록 복사
        if (Test-Path $claudeDir) {
            $jsonlFiles = Get-ChildItem $claudeDir -Recurse -Filter "*.jsonl" |
                          Sort-Object LastWriteTime -Descending | Select-Object -First 5
            foreach ($f in $jsonlFiles) {
                Copy-Item $f.FullName -Destination $snapDir -Force
            }
            Write-Log "JSONL $($jsonlFiles.Count)개 복사 -> $snapDir"
        }

        # 2. PSReadLine 터미널 히스토리 복사
        if (Test-Path $psHistory) {
            Copy-Item $psHistory -Destination ($snapDir + "\terminal_history.txt") -Force
            Write-Log "터미널 히스토리 복사"
        }

        # 3. latest-session.json 갱신 (메타 스냅샷)
        $meta = @{
            timestamp   = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
            snap_dir    = $snapDir
            jsonl_count = $jsonlFiles.Count
        } | ConvertTo-Json
        $meta | Out-File -FilePath ($backupDir + "\latest-session.json") -Encoding UTF8 -Force

        # 4. 오래된 스냅샷 정리 (최근 20개만 유지)
        $oldSnaps = Get-ChildItem $backupDir -Directory -Filter "snap_*" |
                    Sort-Object LastWriteTime -Descending | Select-Object -Skip 20
        foreach ($old in $oldSnaps) { Remove-Item $old.FullName -Recurse -Force }

        Write-Log "5분 백업 완료 [$ts]"
    }
    catch {
        Write-Log "백업 오류: $_"
    }

    Start-Sleep -Seconds 300
}
