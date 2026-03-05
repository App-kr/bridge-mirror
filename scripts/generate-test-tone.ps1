# Generate frequency sweep WAV for EQ testing
# Low(40Hz) -> Mid(1kHz) -> High(12kHz) over 4 seconds

$outPath = Join-Path $PSScriptRoot "test-sweep.wav"

$sampleRate = 44100
$duration = 4.0
$totalSamples = [int]($sampleRate * $duration)
$data = New-Object byte[] ($totalSamples * 2)

for ($i = 0; $i -lt $totalSamples; $i++) {
    $t = $i / $sampleRate
    # Logarithmic sweep 40Hz -> 12000Hz
    $freq = 40.0 * [Math]::Pow(300.0, $t / $duration)
    # Amplitude envelope: fade in 0.1s, fade out 0.2s
    $env = 1.0
    if ($t -lt 0.1) { $env = $t / 0.1 }
    if ($t -gt ($duration - 0.2)) { $env = ($duration - $t) / 0.2 }
    $sample = [Math]::Sin(2.0 * [Math]::PI * $freq * $t) * 0.6 * $env
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
$bw.Write([int16]1)           # PCM
$bw.Write([int16]1)           # Mono
$bw.Write([int]$sampleRate)   # Sample rate
$bw.Write([int]($sampleRate * 2))  # Byte rate
$bw.Write([int16]2)           # Block align
$bw.Write([int16]16)          # Bits per sample

# data chunk
$bw.Write([System.Text.Encoding]::ASCII.GetBytes("data"))
$bw.Write([int]$data.Length)
$bw.Write($data)

$bw.Close()
$fs.Close()

Write-Output "OK: $outPath ($([Math]::Round((Get-Item $outPath).Length / 1024)) KB)"
