# Search all scripts for unquoted wscript calls with bridge path
$results = @()

Get-ChildItem "Q:\" -Recurse -Include "*.bat","*.cmd","*.ps1","*.vbs","*.ahk" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch "_BACKUP|backups|__pycache__|tools\\check|tools\\find|tools\\grep|tools\\check" } |
    ForEach-Object {
        $f = $_
        $lines = Get-Content $f.FullName -ErrorAction SilentlyContinue
        $lnum = 0
        foreach ($line in $lines) {
            $lnum++
            # Look for wscript calls without quotes around bridge path
            if ($line -match "wscript" -and $line -match "bridge" -and $line -notmatch '"Q:\\Claudework\\bridge') {
                $results += [PSCustomObject]@{
                    File = $f.FullName
                    Line = $lnum
                    Content = $line.Trim()
                }
            }
        }
    }

if ($results) {
    Write-Host "FOUND unquoted bridge+wscript calls:"
    $results | Format-Table -Wrap
} else {
    Write-Host "No unquoted wscript+bridge calls found"
}

Write-Host ""
Write-Host "--- All wscript calls in Q drive ---"
Get-ChildItem "Q:\" -Recurse -Include "*.bat","*.cmd","*.ps1","*.vbs","*.ahk" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch "_BACKUP|backups|__pycache__|tools\\check|tools\\find|tools\\grep" } |
    ForEach-Object {
        $f = $_
        $content = Get-Content $f.FullName -ErrorAction SilentlyContinue
        if ($content -match "wscript") {
            Write-Host "FILE: $($f.FullName)"
            ($content | Select-String -Pattern "wscript" -CaseSensitive:$false) | ForEach-Object {
                Write-Host "  L$($_.LineNumber): $($_.Line.Trim())"
            }
        }
    }
