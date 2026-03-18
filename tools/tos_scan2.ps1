$ErrorActionPreference = "SilentlyContinue"
Write-Host "=== Acrobat Preferences & TOS Deep Scan ==="

# Acrobat 설정 파일 위치
$prefPaths = @(
    "$env:APPDATA\Adobe\Acrobat\DC\Preferences",
    "$env:LOCALAPPDATA\Adobe\Acrobat\DC",
    "$env:APPDATA\Adobe\Acrobat\DC"
)
foreach ($p in $prefPaths) {
    if (Test-Path $p) {
        Write-Host "`nPref dir: $p"
        Get-ChildItem $p -Recurse -File -ErrorAction SilentlyContinue | Select-Object FullName, Length | Format-Table -AutoSize
    }
}

# TOS 관련 프리프 파일 내용 검색
Write-Host "`n=== JSON/pref files containing TOS/EULA ==="
$searchDirs = @(
    "$env:APPDATA\Adobe\Acrobat",
    "$env:LOCALAPPDATA\Adobe\Acrobat"
)
foreach ($dir in $searchDirs) {
    if (Test-Path $dir) {
        Get-ChildItem $dir -Recurse -File -Include "*.json","*.prefs","*.xml","*.cfg" -ErrorAction SilentlyContinue | ForEach-Object {
            $content = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue
            if ($content -match "TOS|EULA|Terms|tou|tos|eula|accept") {
                Write-Host "  MATCH: $($_.FullName)"
                $content | Select-String -Pattern "TOS|EULA|Terms|tou|tos|eula|accept" | Select-Object -First 5 | ForEach-Object {
                    Write-Host "    $($_.Line.Trim())"
                }
            }
        }
    }
}

# AVGeneral 전체 덤프 (TOS 관련 키 찾기)
Write-Host "`n=== HKCU AVGeneral TOS-related ==="
$avgen = Get-ItemProperty "HKCU:\SOFTWARE\Adobe\Adobe Acrobat\DC\AVGeneral" -ErrorAction SilentlyContinue
if ($avgen) {
    $avgen.PSObject.Properties | Where-Object { $_.Name -match "IMS|TOS|Sign|Login|Cloud|Account|Accept|ims" -and $_.Name -notlike "PS*" } | ForEach-Object {
        Write-Host "  $($_.Name) = $($_.Value)"
    }
}

# IMS 관련 키 (Adobe Identity Management)
Write-Host "`n=== IMS Registry Keys ==="
@("HKCU:\SOFTWARE\Adobe\Adobe Acrobat\DC\IMS",
  "HKCU:\SOFTWARE\Adobe\Adobe Acrobat\DC\IMSTrusted",
  "HKCU:\SOFTWARE\Adobe\CommonFiles\IMS") | ForEach-Object {
    if (Test-Path $_) {
        Write-Host "[$_]"
        Get-ItemProperty $_ | ForEach-Object {
            $_.PSObject.Properties | Where-Object { $_.Name -notlike "PS*" } | ForEach-Object {
                Write-Host "  $($_.Name) = $($_.Value)"
            }
        }
    }
}
