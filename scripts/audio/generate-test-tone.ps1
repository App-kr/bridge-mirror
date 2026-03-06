# Generate footstep-like test WAV for EQ testing
# Bass-heavy thuds at walking pace: 쿵... 쿵... 쿵쿵... 쿵

$outPath = Join-Path $PSScriptRoot "test-sweep.wav"

$sampleRate = 44100
$duration = 5.0
$totalSamples = [int]($sampleRate * $duration)
$data = New-Object byte[] ($totalSamples * 2)

# Footstep timing (seconds) - natural walking rhythm
$steps = @(0.3, 0.95, 1.6, 2.1, 2.5, 3.2, 3.85, 4.5)

function Get-StepSample($t, $stepTime) {
    $dt = $t - $stepTime
    if ($dt -lt 0 -or $dt -gt 0.35) { return 0.0 }

    # Quick attack, medium decay envelope
    $env = [Math]::Exp(-$dt * 12.0) * (1.0 - [Math]::Exp(-$dt * 200.0))

    # Layer 1: Deep bass thump (55Hz) - the core "쿵"
    $bass = [Math]::Sin(2.0 * [Math]::PI * 55.0 * $dt) * 0.7

    # Layer 2: Low-mid body (120Hz) - weight of the step
    $body = [Math]::Sin(2.0 * [Math]::PI * 120.0 * $dt) * 0.4

    # Layer 3: Floor impact transient (250Hz, faster decay)
    $impact = [Math]::Sin(2.0 * [Math]::PI * 250.0 * $dt) * 0.25 * [Math]::Exp(-$dt * 25.0)

    # Layer 4: High click/crunch (2kHz~4kHz, very fast decay) - shoe contact
    $click = ([Math]::Sin(2.0 * [Math]::PI * 2500.0 * $dt) + [Math]::Sin(2.0 * [Math]::PI * 4000.0 * $dt) * 0.3) * 0.15 * [Math]::Exp(-$dt * 50.0)

    return ($bass + $body + $impact + $click) * $env
}

for ($i = 0; $i -lt $totalSamples; $i++) {
    $t = $i / $sampleRate
    $sample = 0.0

    foreach ($s in $steps) {
        $sample += Get-StepSample $t $s
    }

    # Soft clip
    if ($sample -gt 0.95) { $sample = 0.95 }
    if ($sample -lt -0.95) { $sample = -0.95 }

    $val = [int]($sample * 32767)
    if ($val -gt 32767) { $val = 32767 }
    if ($val -lt -32768) { $val = -32768 }
    $data[$i * 2] = [byte]($val -band 0xFF)
    $data[$i * 2 + 1] = [byte](($val -shr 8) -band 0xFF)
}

$fs = [System.IO.File]::Create($outPath)
$bw = New-Object System.IO.BinaryWriter($fs)

# RIFF header
$bw.Write([System.Text.Encoding]::ASCII.GetBytes("RIFF"))
$bw.Write([int]($data.Length + 36))
$bw.Write([System.Text.Encoding]::ASCII.GetBytes("WAVE"))

# fmt chunk
$bw.Write([System.Text.Encoding]::ASCII.GetBytes("fmt "))
$bw.Write([int]16)
$bw.Write([int16]1)
$bw.Write([int16]1)
$bw.Write([int]$sampleRate)
$bw.Write([int]($sampleRate * 2))
$bw.Write([int16]2)
$bw.Write([int16]16)

# data chunk
$bw.Write([System.Text.Encoding]::ASCII.GetBytes("data"))
$bw.Write([int]$data.Length)
$bw.Write($data)

$bw.Close()
$fs.Close()

Write-Output "OK: $outPath ($([Math]::Round((Get-Item $outPath).Length / 1024)) KB)"
