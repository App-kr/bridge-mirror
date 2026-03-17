$regPath = 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run'
$keysToRemove = @('RiotClient', 'Discord', 'electron.app.Notion', 'Steam')
foreach ($key in $keysToRemove) {
    if (Get-ItemProperty -Path $regPath -Name $key -ErrorAction SilentlyContinue) {
        Remove-ItemProperty -Path $regPath -Name $key
        Write-Host "제거됨: $key"
    } else {
        Write-Host "없음: $key"
    }
}
Write-Host "--- 남은 시작프로그램 ---"
Get-ItemProperty -Path $regPath | Select-Object -Property * -ExcludeProperty PSPath, PSParentPath, PSChildName, PSDrive, PSProvider
