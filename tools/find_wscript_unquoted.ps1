# Search for all calls to wscript in scripts - looking for unquoted paths
$searchPaths = @(
    "Q:\Claudework",
    "Q:\Headset"
)

$patterns = @("wscript", "WScript")

foreach ($root in $searchPaths) {
    if (-not (Test-Path $root)) { continue }

    Write-Host "=== Searching in: $root ==="

    # Search .ps1, .bat, .py, .vbs, .cmd files
    Get-ChildItem $root -Recurse -ErrorAction SilentlyContinue -Include "*.ps1","*.bat","*.py","*.vbs","*.cmd","*.ahk" |
        Where-Object { $_.FullName -notmatch "\\.git\\" -and $_.FullName -notmatch "__pycache__" } |
        ForEach-Object {
            $file = $_
            $content = Get-Content $file.FullName -ErrorAction SilentlyContinue -Raw
            if ($content -match "wscript" -or $content -match "WScript\.Shell") {
                # Find the specific lines
                $lines = Get-Content $file.FullName -ErrorAction SilentlyContinue
                for ($i = 0; $i -lt $lines.Count; $i++) {
                    $line = $lines[$i]
                    if ($line -match "wscript" -and $line -notmatch "^#" -and $line -notmatch "^//") {
                        Write-Host ""
                        Write-Host "FILE: $($file.FullName)"
                        Write-Host "LINE $($i+1): $line"
                        # Check if it looks unquoted
                        if ($line -match "wscript" -and $line -match "bridge base" -and $line -notmatch '"Q:\\Claudework\\bridge base') {
                            Write-Host "  *** POSSIBLE UNQUOTED PATH DETECTED ***"
                        }
                    }
                }
            }
        }
}

Write-Host ""
Write-Host "=== Search C:\ for scripts referencing Q:\Claudework\bridge (without quotes) ==="
Get-ChildItem "C:\Users\Scarlett\AppData" -Recurse -Depth 4 -ErrorAction SilentlyContinue -Include "*.ps1","*.bat","*.vbs","*.cmd" |
    Where-Object { $_.FullName -notmatch "\\.git\\" } |
    ForEach-Object {
        $content = Get-Content $_.FullName -ErrorAction SilentlyContinue -Raw
        if ($content -match "Claudework.bridge") {
            Write-Host "Found reference in: $($_.FullName)"
            Get-Content $_.FullName -ErrorAction SilentlyContinue | Where-Object { $_ -match "Claudework.bridge" } | ForEach-Object {
                Write-Host "  >> $_"
            }
        }
    }
