# Read all task XML files and show LogonTrigger tasks
$taskDir = "C:\Windows\System32\Tasks"

function Get-TaskDetails($path) {
    $files = Get-ChildItem $path -File -ErrorAction SilentlyContinue
    foreach ($f in $files) {
        try {
            $content = [System.IO.File]::ReadAllText($f.FullName)
            if ($content -match "LogonTrigger") {
                # Strip BOM and fix encoding
                $content = $content -replace '[\x00]', ''  # Remove null bytes from UTF-16
                Write-Host "=== LOGON TASK: $($f.Name) ==="
                # Extract command and arguments
                if ($content -match '<Command>(.*?)</Command>') {
                    Write-Host "  Command: $($matches[1])"
                }
                if ($content -match '<Arguments>(.*?)</Arguments>') {
                    Write-Host "  Arguments: $($matches[1])"
                }
                Write-Host ""
            }
        } catch {}
    }
    # Recurse into subdirectories
    $dirs = Get-ChildItem $path -Directory -ErrorAction SilentlyContinue
    foreach ($d in $dirs) {
        Get-TaskDetails $d.FullName
    }
}

Get-TaskDetails $taskDir
