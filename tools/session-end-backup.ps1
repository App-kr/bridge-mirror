# session-end-backup.ps1
# 세션 종료 시 Claude Code가 실행하는 백업 스크립트
# 사용: pwsh -File tools/session-end-backup.ps1 -Note "오늘 한 작업 요약"

param(
    [string]$Note = ""
)

$BASE   = "Q:\Claudework\bridge base"
$DAYS   = @("일","월","화","수","목","금","토")
$today  = Get-Date
$dow    = $DAYS[$today.DayOfWeek.value__]
$label  = $today.ToString("yyyy-MM-dd") + "_$dow"
$dest   = "$BASE\.backups\$label"

Write-Host "📦 백업 시작: $label" -ForegroundColor Cyan

# 1. 백업 폴더 생성
New-Item -ItemType Directory -Path $dest -Force | Out-Null

# 2. .memory 폴더 복사
if (Test-Path "$BASE\.memory") {
    Copy-Item "$BASE\.memory" "$dest\memory" -Recurse -Force
    Write-Host "  ✓ .memory 복사 완료"
}

# 3. git log 저장
Set-Location $BASE
git log --oneline -20 2>$null | Out-File "$dest\git-log.txt" -Encoding utf8
Write-Host "  ✓ git-log.txt 저장"

# 4. 오늘 변경된 파일 목록
git diff --name-only HEAD~5 HEAD 2>$null | Out-File "$dest\changed-files.txt" -Encoding utf8
Write-Host "  ✓ changed-files.txt 저장"

# 5. 세션 노트 저장
$noteContent = @"
# 세션 노트 — $label

## 작업 요약
$Note

## 생성 시각
$($today.ToString("yyyy-MM-dd HH:mm:ss"))
"@
$noteContent | Out-File "$dest\session-note.md" -Encoding utf8
Write-Host "  ✓ session-note.md 저장"

# 6. 14일 이전 백업 폴더 자동 삭제
$cutoff = (Get-Date).AddDays(-14)
Get-ChildItem "$BASE\.backups" -Directory | Where-Object {
    $_.CreationTime -lt $cutoff
} | ForEach-Object {
    Remove-Item $_.FullName -Recurse -Force
    Write-Host "  🗑 오래된 백업 삭제: $($_.Name)" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "✅ 백업 완료: $dest" -ForegroundColor Green
Write-Host "   14일치 백업 유지 중"
