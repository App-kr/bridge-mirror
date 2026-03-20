Add-Type -AssemblyName System.Drawing

$outPath = "Q:\Claudework\bridge base\eslcafe_manager\ESLCafe.ico"
$sizes = @(256, 48, 32, 16)
$images = @()

foreach ($sz in $sizes) {
    $bmp = New-Object System.Drawing.Bitmap($sz, $sz)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = 'HighQuality'
    $g.TextRenderingHint = 'AntiAliasGridFit'
    $g.InterpolationMode = 'HighQualityBicubic'
    $g.PixelOffsetMode = 'HighQuality'

    # Gradient background
    $bgBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
        (New-Object System.Drawing.Point(0, 0)),
        (New-Object System.Drawing.Point($sz, $sz)),
        [System.Drawing.ColorTranslator]::FromHtml("#1a5ff8"),
        [System.Drawing.ColorTranslator]::FromHtml("#7c3aed")
    )

    # Rounded rect
    $r = [int]($sz * 0.2)
    $path = New-Object System.Drawing.Drawing2D.GraphicsPath
    $path.AddArc(0, 0, $r*2, $r*2, 180, 90)
    $path.AddArc($sz - $r*2, 0, $r*2, $r*2, 270, 90)
    $path.AddArc($sz - $r*2, $sz - $r*2, $r*2, $r*2, 0, 90)
    $path.AddArc(0, $sz - $r*2, $r*2, $r*2, 90, 90)
    $path.CloseFigure()
    $g.FillPath($bgBrush, $path)

    # ESL text
    $fontSize = [Math]::Max(7, [int]($sz * 0.33))
    $font = New-Object System.Drawing.Font("Segoe UI", $fontSize, [System.Drawing.FontStyle]::Bold)
    $whiteBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)
    $sf = New-Object System.Drawing.StringFormat
    $sf.Alignment = 'Center'
    $sf.LineAlignment = 'Center'
    $textRect = New-Object System.Drawing.RectangleF(0, 0, $sz, [int]($sz * 0.88))
    $g.DrawString("ESL", $font, $whiteBrush, $textRect, $sf)

    # Green accent bar at bottom
    $barH = [Math]::Max(2, [int]($sz * 0.055))
    $barW = [int]($sz * 0.48)
    $barX = [int](($sz - $barW) / 2)
    $barY = [int]($sz * 0.80)
    $greenBrush = New-Object System.Drawing.SolidBrush([System.Drawing.ColorTranslator]::FromHtml("#05b97d"))
    $g.FillRectangle($greenBrush, $barX, $barY, $barW, $barH)

    $g.Dispose()
    $font.Dispose()
    $images += $bmp
}

# Build ICO file
$ms = New-Object System.IO.MemoryStream
$bw = New-Object System.IO.BinaryWriter($ms)

$bw.Write([UInt16]0)
$bw.Write([UInt16]1)
$bw.Write([UInt16]$sizes.Count)

$pngDatas = @()
foreach ($img in $images) {
    $pngMs = New-Object System.IO.MemoryStream
    $img.Save($pngMs, [System.Drawing.Imaging.ImageFormat]::Png)
    $pngDatas += ,($pngMs.ToArray())
    $pngMs.Dispose()
}

$headerSize = 6 + ($sizes.Count * 16)
$dataOffset = $headerSize

for ($i = 0; $i -lt $sizes.Count; $i++) {
    $w = if ($sizes[$i] -ge 256) { 0 } else { [byte]$sizes[$i] }
    $bw.Write([byte]$w)
    $bw.Write([byte]$w)
    $bw.Write([byte]0)
    $bw.Write([byte]0)
    $bw.Write([UInt16]1)
    $bw.Write([UInt16]32)
    $bw.Write([UInt32]$pngDatas[$i].Length)
    $bw.Write([UInt32]$dataOffset)
    $dataOffset += $pngDatas[$i].Length
}

foreach ($png in $pngDatas) {
    $bw.Write($png)
}

[System.IO.File]::WriteAllBytes($outPath, $ms.ToArray())
$bw.Dispose()
$ms.Dispose()
foreach ($img in $images) { $img.Dispose() }

Write-Host "Icon created: $outPath"

# Create .lnk shortcut on desktop
$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut("C:\Users\Scarlett\Desktop\BRIDGE ESLCafe.lnk")
$shortcut.TargetPath = "Q:\Claudework\bridge base\eslcafe_manager\BRIDGE_ESLCafe.html"
$shortcut.IconLocation = $outPath + ",0"
$shortcut.Description = "BRIDGE ESLCafe Ad Manager"
$shortcut.WorkingDirectory = "Q:\Claudework\bridge base\eslcafe_manager"
$shortcut.Save()
Write-Host "Shortcut created on Desktop"

# Remove old copy if exists
$oldCopy = "C:\Users\Scarlett\Desktop\BRIDGE_ESLCafe.html"
if (Test-Path $oldCopy) {
    Remove-Item $oldCopy -Force
    Write-Host "Removed old HTML copy from Desktop"
}
