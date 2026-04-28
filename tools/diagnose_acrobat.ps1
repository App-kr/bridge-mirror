$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== A) Adobe Acrobat actual install locations ==="
$searchPaths = @(
    "C:\Program Files\Adobe",
    "C:\Program Files (x86)\Adobe",
    "Q:\Apps\Adobe",
    "Q:\Adobe",
    "Q:\Program Files\Adobe",
    "Q:\Program Files (x86)\Adobe"
)
foreach ($p in $searchPaths) {
    if (Test-Path $p) {
        Write-Host ""
        Write-Host ("  FOUND: {0}" -f $p)
        Get-ChildItem $p -Recurse -Filter "Acrobat*.exe" -ErrorAction SilentlyContinue |
            Select-Object -First 10 |
            ForEach-Object { Write-Host ("    {0}  ({1} KB)" -f $_.FullName, [math]::Round($_.Length/1KB,1)) }
    }
}

Write-Host ""
Write-Host "=== B) Acrobat.exe / Acrobat Elements.exe / AcroRd32.exe in PATH (any drive) ==="
@('Acrobat.exe','AcroRd32.exe','Acrobat Elements.exe') | ForEach-Object {
    $name = $_
    Write-Host ""
    Write-Host ("Looking for: {0}" -f $name)
    @('C:\','Q:\') | ForEach-Object {
        Get-ChildItem -Path $_ -Recurse -Filter $name -ErrorAction SilentlyContinue -Force |
            Select-Object -First 5 |
            ForEach-Object { Write-Host ("    {0}" -f $_.FullName) }
    }
}

Write-Host ""
Write-Host "=== C) .pdf file association (current default) ==="
& cmd /c "assoc .pdf" 2>&1
Write-Host ""
$ftypeOut = & cmd /c "ftype AcroExch.Document.DC" 2>&1
Write-Host ("AcroExch.Document.DC -> {0}" -f $ftypeOut)
$ftypeOut2 = & cmd /c "ftype AcroExch.Document" 2>&1
Write-Host ("AcroExch.Document -> {0}" -f $ftypeOut2)

Write-Host ""
Write-Host "=== D) HKCU UserChoice for .pdf ==="
$uc = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.pdf\UserChoice' -ErrorAction SilentlyContinue
if ($uc) {
    Write-Host ("  ProgId: {0}" -f $uc.ProgId)
    Write-Host ("  Hash:   {0}" -f $uc.Hash)
} else { Write-Host "  (no UserChoice)" }

Write-Host ""
Write-Host "=== E) AppPaths for Acrobat ==="
@('Acrobat.exe','AcroRd32.exe','Acrobat Elements.exe') | ForEach-Object {
    $name = $_
    foreach ($hive in @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\',
                         'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\')) {
        $key = $hive + $name
        $v = (Get-ItemProperty $key -ErrorAction SilentlyContinue).'(default)'
        if ($v) { Write-Host ("  {0} = {1}" -f $key, $v) }
    }
}

Write-Host ""
Write-Host "=== F) Acrobat Run/Startup entries ==="
@('HKCU:\Software\Microsoft\Windows\CurrentVersion\Run',
  'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
  'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run') | ForEach-Object {
    $items = Get-ItemProperty $_ -ErrorAction SilentlyContinue
    if ($items) {
        $items.PSObject.Properties | Where-Object {
            $_.Name -notmatch '^PS' -and $_.Value -match 'Acrobat|Adobe'
        } | ForEach-Object {
            Write-Host ("  {0} :: {1} = {2}" -f $_.Name, $_.Value)
        }
    }
}
