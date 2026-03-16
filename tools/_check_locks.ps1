$logdir = "Q:\Claudework\bridge base\logs"
Write-Host "=== logs 폴더 파일 목록 ==="
$files = [System.IO.Directory]::GetFiles($logdir)
if ($files.Count -eq 0) {
    Write-Host "(비어있음)"
} else {
    foreach ($f in $files) {
        $name = [System.IO.Path]::GetFileName($f)
        $content = [System.IO.File]::ReadAllText($f, [System.Text.Encoding]::UTF8).Trim()
        Write-Host ("  " + $name + " = [" + $content + "]")
        if ($name -like ".rpa_*.lock") {
            $pidVal = [int]$content
            $h = [System.Diagnostics.Process]::GetProcessById($pidVal)
            if ($h -ne $null) {
                Write-Host ("    → 프로세스 살아있음: " + $h.ProcessName)
            }
        }
    }
}
