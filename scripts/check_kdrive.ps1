if (Test-Path 'K:\') {
    Write-Host "K드라이브 있음"
    Get-ChildItem 'K:\' -Recurse -Include '*.ico','*.png' -ErrorAction SilentlyContinue |
        Select-Object -First 20 |
        ForEach-Object { Write-Host $_.FullName }
} else {
    Write-Host "K드라이브 없음"
}
