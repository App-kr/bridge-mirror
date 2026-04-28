$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== C-drive hooks audit (CREATE_NO_WINDOW missing) ==="
$hookDir = "C:\Users\Scarlett\.claude\hooks"
Get-ChildItem $hookDir -Filter '*.py' -ErrorAction SilentlyContinue | ForEach-Object {
    $content = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue
    if (-not $content) { return }

    $hasSubprocess = $content -match 'subprocess\.(run|Popen|call|check_call|check_output)'
    $hasCreateNoWindow = $content -match 'CREATE_NO_WINDOW|creationflags'

    if ($hasSubprocess) {
        if ($hasCreateNoWindow) {
            Write-Host ("  OK    {0}  (subprocess + creationflags)" -f $_.Name)
        } else {
            Write-Host ("  VULN  {0}  (subprocess WITHOUT creationflags)" -f $_.Name)
        }
    } else {
        Write-Host ("  N/A   {0}  (no subprocess)" -f $_.Name)
    }
}
