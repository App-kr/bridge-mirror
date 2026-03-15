# 아이콘 캐시 새로고침
Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 1800
Start-Process explorer
Write-Host "Explorer 재시작 완료 - 아이콘 캐시 갱신"
