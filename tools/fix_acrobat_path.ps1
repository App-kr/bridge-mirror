$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$cPath = "C:\Program Files (x86)\Adobe\Acrobat DC"
$qPath = "Q:\Apps\Adobe\ProgramFiles_x86\Acrobat DC"

Write-Host "=== Step 1: Verify Q path exists with full Acrobat install ==="
if (-not (Test-Path "$qPath\Acrobat\Acrobat.exe")) {
    Write-Host "  FATAL: $qPath\Acrobat\Acrobat.exe not found"
    exit 1
}
Write-Host "  OK: $qPath\Acrobat\Acrobat.exe exists"

Write-Host ""
Write-Host "=== Step 2: Inspect C path current state ==="
if (Test-Path $cPath) {
    $items = Get-ChildItem $cPath -Force -ErrorAction SilentlyContinue
    Write-Host ("  C path content: {0} items" -f $items.Count)
    $items | Select-Object -First 10 | ForEach-Object { Write-Host ("    {0}" -f $_.Name) }

    # 비어있거나 거의 비어있으면 junction 가능
    $hasRealFiles = $items | Where-Object { $_.Length -gt 0 -and -not $_.PSIsContainer } | Measure-Object | Select-Object -ExpandProperty Count
    if ($hasRealFiles -gt 5) {
        Write-Host ""
        Write-Host "  WARN: C path has real files - rename instead of delete"
        $bak = "C:\Program Files (x86)\Adobe\Acrobat DC.bak.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        Move-Item $cPath $bak -Force
        Write-Host ("  Backed up to: {0}" -f $bak)
    } else {
        Write-Host "  Removing nearly-empty C path..."
        Remove-Item $cPath -Recurse -Force -ErrorAction SilentlyContinue
        if (Test-Path $cPath) {
            Write-Host "  WARN: could not fully remove - may need admin rights"
        } else {
            Write-Host "  OK: removed"
        }
    }
} else {
    Write-Host "  C path does not exist (clean state)"
}

Write-Host ""
Write-Host "=== Step 3: Create directory junction C -> Q ==="
if (-not (Test-Path $cPath)) {
    $parent = Split-Path $cPath -Parent
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    & cmd /c "mklink /J `"$cPath`" `"$qPath`"" 2>&1 | ForEach-Object { Write-Host "  $_" }
} else {
    Write-Host "  C path still exists - cannot create junction"
}

Write-Host ""
Write-Host "=== Step 4: Verify junction ==="
if (Test-Path "$cPath\Acrobat\Acrobat.exe") {
    Write-Host "  OK: C path now resolves to Q (junction works)"
} elseif (Test-Path "$cPath\Acrobat Elements\Acrobat Elements.exe") {
    Write-Host "  OK: Acrobat Elements accessible via C path"
} else {
    Write-Host "  WARN: junction may not have worked"
}

Write-Host ""
Write-Host "=== Step 5: Set PDF default app via UserChoice registry ==="
$pdfKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.pdf\UserChoice'
$current = (Get-ItemProperty $pdfKey -ErrorAction SilentlyContinue).ProgId
Write-Host ("  Current .pdf ProgId: {0}" -f $current)
Write-Host "  (Permanent change requires Settings app - manual step)"
Write-Host ""
Write-Host "  설정 > 앱 > 기본 앱 > .pdf 검색 > Acrobat Pro DC 선택"
Write-Host "  (UserChoice has hash protection, must use Settings UI)"

Write-Host ""
Write-Host "=== Step 6: AcroExch.Document ProgId points to ==="
$progId = (Get-ItemProperty 'HKLM:\SOFTWARE\Classes\AcroExch.Document.DC\shell\Open\command' -ErrorAction SilentlyContinue).'(default)'
if ($progId) {
    Write-Host ("  AcroExch.Document.DC -> {0}" -f $progId)
}
$progId2 = (Get-ItemProperty 'HKLM:\SOFTWARE\Classes\AcroExch.Document\shell\Open\command' -ErrorAction SilentlyContinue).'(default)'
if ($progId2) {
    Write-Host ("  AcroExch.Document -> {0}" -f $progId2)
}
