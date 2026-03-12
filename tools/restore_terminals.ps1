# 오전 10시 이후 작업 세션 복구
# 수정된 파일 기반: rpa_overlay.py, ClaudeBlog (naver_uploader, content_generator)

Write-Host "터미널 세션 복구 시작..." -ForegroundColor Cyan

# Windows Terminal이 없으면 PowerShell 창들로 복구
$wt = Get-Command "wt.exe" -ErrorAction SilentlyContinue

if ($wt) {
    # Windows Terminal: 탭별로 세션 복구
    Start-Process "wt.exe" -ArgumentList @(
        "new-tab", "--title", "Bridge Base", "--tabColor", "#0078D4",
            "-d", "Q:\Claudework\bridge base", "powershell.exe", "-NoExit", "-Command", "Write-Host '[Bridge Base] 복구됨' -ForegroundColor Green",
        ";", "new-tab", "--title", "ClaudeBlog", "--tabColor", "#107C10",
            "-d", "Q:\Claudework\ClaudeBlog", "powershell.exe", "-NoExit", "-Command", "Write-Host '[ClaudeBlog] 복구됨' -ForegroundColor Green; git status",
        ";", "new-tab", "--title", "RPA Overlay", "--tabColor", "#FF8C00",
            "-d", "Q:\Claudework\bridge base", "powershell.exe", "-NoExit", "-Command", "Write-Host '[RPA Overlay] python rpa_overlay.py' -ForegroundColor Yellow; Get-Content overlay_state.json"
    )
    Write-Host "Windows Terminal 탭 3개 복구 완료" -ForegroundColor Green
} else {
    # wt 없음 - 개별 PowerShell 창으로 복구
    Write-Host "Windows Terminal 미설치 - 개별 창으로 복구" -ForegroundColor Yellow

    Start-Process "powershell.exe" -ArgumentList "-NoExit", "-Command",
        "cd 'Q:\Claudework\bridge base'; Write-Host '[Bridge Base] 복구됨' -ForegroundColor Green"

    Start-Process "powershell.exe" -ArgumentList "-NoExit", "-Command",
        "cd 'Q:\Claudework\ClaudeBlog'; Write-Host '[ClaudeBlog] 복구됨' -ForegroundColor Green; git status"

    Start-Process "powershell.exe" -ArgumentList "-NoExit", "-Command",
        "cd 'Q:\Claudework\bridge base'; Write-Host '[RPA Overlay]' -ForegroundColor Yellow; Get-Content overlay_state.json"

    Write-Host "창 3개 복구 완료" -ForegroundColor Green
}

Write-Host ""
Write-Host "복구된 세션:" -ForegroundColor Cyan
Write-Host "  1. Bridge Base    - Q:\Claudework\bridge base" -ForegroundColor White
Write-Host "  2. ClaudeBlog     - Q:\Claudework\ClaudeBlog (naver_uploader, content_generator 작업중)" -ForegroundColor White
Write-Host "  3. RPA Overlay    - rpa_overlay.py (overlay_state.json 활성)" -ForegroundColor White
