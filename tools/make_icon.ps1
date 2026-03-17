Add-Type -AssemblyName System.Drawing

function New-BridgeFrame([int]$size) {
    $bmp = New-Object System.Drawing.Bitmap($size, $size, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g   = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode   = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceOver
    $g.Clear([System.Drawing.Color]::Transparent)

    # ── Rounded square background (purple → indigo) ──────────
    $grad = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
        [System.Drawing.Point]::new(0, 0),
        [System.Drawing.Point]::new(0, $size),
        [System.Drawing.Color]::FromArgb(255, 124, 58, 237),
        [System.Drawing.Color]::FromArgb(255, 59, 130, 246)
    )
    $r    = [int]($size / 5)
    $path = New-Object System.Drawing.Drawing2D.GraphicsPath
    $path.AddArc(0,          0,          2*$r, 2*$r, 180, 90)
    $path.AddArc($size-2*$r, 0,          2*$r, 2*$r, 270, 90)
    $path.AddArc($size-2*$r, $size-2*$r, 2*$r, 2*$r, 0,   90)
    $path.AddArc(0,          $size-2*$r, 2*$r, 2*$r, 90,  90)
    $path.CloseFigure()
    $g.FillPath($grad, $path)
    $grad.Dispose(); $path.Dispose()

    # ── Camera body (white rounded rect) ──────────────────────
    $m   = [int]($size / 7.0)
    $bw  = $size - 2*$m
    $bh  = [int]($bw * 0.60)
    $bx  = $m
    $by  = [int](($size - $bh) / 2) + [int]($size / 18)
    $cr  = [int]($size / 9)

    $wBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(235, 255, 255, 255))
    $cp     = New-Object System.Drawing.Drawing2D.GraphicsPath
    $cp.AddArc($bx,        $by,        2*$cr, 2*$cr, 180, 90)
    $cp.AddArc($bx+$bw-2*$cr, $by,    2*$cr, 2*$cr, 270, 90)
    $cp.AddArc($bx+$bw-2*$cr, $by+$bh-2*$cr, 2*$cr, 2*$cr, 0, 90)
    $cp.AddArc($bx,        $by+$bh-2*$cr, 2*$cr, 2*$cr, 90, 90)
    $cp.CloseFigure()
    $g.FillPath($wBrush, $cp)
    $cp.Dispose()

    # ── Viewfinder bump (top-center) ──────────────────────────
    $vw = [int]($bw / 3.2)
    $vh = [int]($size / 10)
    $vx = $bx + [int](($bw - $vw) / 2)
    $g.FillRectangle($wBrush, $vx, $by - $vh + 2, $vw, $vh)
    $wBrush.Dispose()

    # ── Lens outer (indigo) ───────────────────────────────────
    $cx = $bx + [int]($bw / 2)
    $cy = $by + [int]($bh / 2)
    $lo = [int]($bh * 0.33)
    $b1 = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 99, 102, 241))
    $g.FillEllipse($b1, $cx-$lo, $cy-$lo, 2*$lo, 2*$lo)
    $b1.Dispose()

    # ── Lens inner (violet) ───────────────────────────────────
    $li = [int]($lo * 0.60)
    $b2 = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 167, 139, 250))
    $g.FillEllipse($b2, $cx-$li, $cy-$li, 2*$li, 2*$li)
    $b2.Dispose()

    # ── Lens glint (white dot) ────────────────────────────────
    $gd = [int]($lo * 0.30)
    $gx = $cx - [int]($lo * 0.28)
    $gy = $cy - [int]($lo * 0.28)
    $b3 = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(210, 255, 255, 255))
    $g.FillEllipse($b3, $gx, $gy, $gd, $gd)
    $b3.Dispose()

    # ── Sparkle dots (yellow) ─────────────────────────────────
    $sb  = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(220, 253, 224, 71))
    $sr   = [int]([Math]::Max(1, $size / 14))
    $sx1  = [int]($m * 0.6)
    $sx2  = $size - [int]($m * 0.6) - $sr
    $sy   = [int]($m * 0.55)
    $g.FillEllipse($sb, $sx1 - [int]($sr/2), $sy - [int]($sr/2), $sr, $sr)
    $g.FillEllipse($sb, $sx2 - [int]($sr/2), $sy - [int]($sr/2), $sr, $sr)
    $sb.Dispose()

    # ── Small heart (pink, bottom-right corner) ───────────────
    $hs  = [int]($size / 9)
    $hx  = $size - $m - $hs + 1
    $hy  = $size - $m - $hs
    $hb  = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(220, 249, 168, 212))
    $hr  = [int]($hs / 2)
    # Two circles + triangle approximation
    $g.FillEllipse($hb, $hx,       $hy,       $hr, $hr)
    $g.FillEllipse($hb, $hx+$hr-1, $hy,       $hr, $hr)
    $pts = [System.Drawing.Point[]]@(
        [System.Drawing.Point]::new($hx,              $hy + [int]($hr*0.7)),
        [System.Drawing.Point]::new($hx + $hs,        $hy + [int]($hr*0.7)),
        [System.Drawing.Point]::new($hx + [int]($hs/2), $hy + $hs + 1)
    )
    $g.FillPolygon($hb, $pts)
    $hb.Dispose()

    $g.Dispose()
    return $bmp
}

# ── Build ICO (multiple sizes) ────────────────────────────────
$sizes   = @(16, 24, 32, 48)
$bitmaps = $sizes | ForEach-Object { New-BridgeFrame $_ }

$pngDatas = foreach ($bmp in $bitmaps) {
    $ms = New-Object System.IO.MemoryStream
    $bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
    ,$ms.ToArray()
    $ms.Dispose()
}

$stream = New-Object System.IO.MemoryStream
$w      = New-Object System.IO.BinaryWriter($stream)

# ICONDIR header
$w.Write([uint16]0)           # reserved
$w.Write([uint16]1)           # type: ICO
$w.Write([uint16]$sizes.Count)

# Entries
$offset = 6 + 16 * $sizes.Count
for ($i = 0; $i -lt $sizes.Count; $i++) {
    $dim = if ($sizes[$i] -ge 256) { 0 } else { [byte]$sizes[$i] }
    $w.Write([byte]$dim)        # width
    $w.Write([byte]$dim)        # height
    $w.Write([byte]0)           # palette
    $w.Write([byte]0)           # reserved
    $w.Write([uint16]1)         # planes
    $w.Write([uint16]32)        # bpp
    $w.Write([uint32]$pngDatas[$i].Length)
    $w.Write([uint32]$offset)
    $offset += $pngDatas[$i].Length
}
foreach ($d in $pngDatas) { $w.Write($d) }
$w.Flush()

$iconPath = "Q:\Claudework\bridge base\tools\bridge_prompt.ico"
[System.IO.File]::WriteAllBytes($iconPath, $stream.ToArray())
$stream.Dispose()
foreach ($bmp in $bitmaps) { $bmp.Dispose() }

Write-Host "OK — icon created: $iconPath"
