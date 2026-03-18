[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$dirs = Get-ChildItem "Q:\" -Force -Directory | Where-Object {
    ($_.Name -replace '[^\x20-\x7E]', '').Length -ne $_.Name.Length
}

foreach ($d in $dirs) {
    $bytes = [System.Text.Encoding]::Unicode.GetBytes($d.Name)
    Write-Host ("Folder hex: " + (($bytes | ForEach-Object { $_.ToString("X2") }) -join " "))
    Write-Host ("Folder name length: " + $d.Name.Length)

    $files = Get-ChildItem $d.FullName -Force -File -ErrorAction SilentlyContinue | Select-Object -First 3
    foreach ($f in $files) {
        $fb = [System.Text.Encoding]::Unicode.GetBytes($f.Name)
        Write-Host ("  File hex: " + (($fb | ForEach-Object { $_.ToString("X2") }) -join " "))
    }
}
