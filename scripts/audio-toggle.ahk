#Requires AutoHotkey v2.0
#SingleInstance Force
Persistent

global gOverlay := ""
global gTrayIndicator := ""
global gFootstepOn := false
global gLastAudioState := ""

; ===== Auto-detect headset every 3 seconds =====
SetTimer(AutoDetect, 3000)

AutoDetect() {
    global gLastAudioState
    result := RunCmd('powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -Command "Import-Module AudioDeviceCmdlets; $d = Get-AudioDevice -List; $c = Get-AudioDevice -Playback; $has = ($d | Where-Object { $_.Type -eq ''Playback'' -and $_.Name -like ''*Captain*'' }); if ($c.Name -like ''*Captain*'') { Write-Output ''ON_HEADSET'' } elseif ($has) { Write-Output ''AVAIL'' } else { Write-Output ''OFF'' }"')
    result := Trim(result)

    if InStr(result, "AVAIL") and gLastAudioState != "headset" {
        ; Headset just appeared - auto switch
        RunCmd('powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File "Q:\Claudework\bridge base\scripts\audio-toggle-to-headset.ps1"')
        gLastAudioState := "headset"
        ShowOverlay("🎧", "Headset ON", "Auto-detected", "0x6C5CE7")
    } else if InStr(result, "OFF") and gLastAudioState != "speaker" {
        ; Headset disappeared - auto switch to speaker
        gLastAudioState := "speaker"
        ; Already on speaker since device is gone, just show overlay on first detect
        if gLastAudioState = "" {
            return
        }
        ShowOverlay("🔊", "Speaker ON", "Headset disconnected", "0xFFA502")
    } else if InStr(result, "ON_HEADSET") {
        gLastAudioState := "headset"
    }
}

; ===== Ctrl+Shift+F9: Manual Audio Toggle =====
^+F9:: {
    result := RunCmd('powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File "Q:\Claudework\bridge base\scripts\audio-toggle.ps1"')
    result := Trim(result)
    if InStr(result, "HEADSET") {
        ShowOverlay("🎧", "Headset ON", "Captain 780LITE", "0x6C5CE7")
    } else if InStr(result, "NO_HEADSET") {
        ShowOverlay("❌", "No Headset", "Turn on headset first", "0xFF4757")
    } else {
        ShowOverlay("🔊", "Speaker ON", "Stand Mic + Speaker", "0xFFA502")
    }
}

; ===== Ctrl+Shift+F10: Footstep Toggle =====
^+F10:: {
    global gFootstepOn
    cf := "C:\Program Files\EqualizerAPO\config\config.txt"
    if gFootstepOn {
        try FileDelete(cf)
        FileAppend("Include: flat.txt", cf)
        gFootstepOn := false
        ShowOverlay("👟", "Footstep OFF", "Normal Audio", "0x636e72")
        HideTray()
    } else {
        try FileDelete(cf)
        FileAppend("Include: footstep-boost.txt", cf)
        gFootstepOn := true
        ShowOverlay("🦶", "Footstep ON", "Bass Enhanced", "0xFF6348")
        ShowTray()
    }
}

; ===== Ctrl+Shift+F11: EQ Editor =====
^+F11:: {
    OpenEQ()
}

; ==================== EQ EDITOR ====================
OpenEQ() {
    global gFootstepOn
    static eg := ""
    if eg {
        eg.Destroy()
        eg := ""
    }

    fNames := ["25","40","63","100","160","250","400","630","1K","1.6K","2.5K","4K","6.3K","10K","16K"]
    fNums := [25,40,63,100,160,250,400,630,1000,1600,2500,4000,6300,10000,16000]
    vals := LoadEQ()

    sw := 36
    sh := 200
    px := 44
    py := 80

    eg := Gui("+AlwaysOnTop -MaximizeBox", "🎛️ EQ Editor")
    eg.BackColor := "16161e"

    eg.SetFont("s14 cFFFFFF Bold", "Segoe UI")
    eg.Add("Text", "x20 y14 w200", "🎛️ EQ Editor")
    eg.SetFont("s8 c555555", "Segoe UI")
    eg.Add("Text", "x400 y20 w180 Right", "EqualizerAPO")

    eg.SetFont("s8 c444444", "Consolas")
    eg.Add("Text", "x6 y" py " w34 Right", "+12")
    eg.Add("Text", "x6 y" (py + sh // 2 - 6) " w34 Right", " 0")
    eg.Add("Text", "x6 y" (py + sh - 12) " w34 Right", "-12")

    loop 15 {
        i := A_Index
        xp := px + (i - 1) * (sw + 4)

        eg.SetFont("s7 c888888", "Consolas")
        eg.Add("Text", "x" xp " y" (py - 16) " w" sw " Center vVL" i, String(vals[i]))

        eg.Add("Slider", "x" xp " y" py " w" sw " h" sh " Vertical Range-12-12 Invert NoTicks vEQ" i, vals[i])

        if (i >= 2 and i <= 5) {
            eg.SetFont("s7 cFF6348 Bold", "Segoe UI")
        } else if (i >= 11 and i <= 13) {
            eg.SetFont("s7 cFFA502 Bold", "Segoe UI")
        } else {
            eg.SetFont("s7 c666666", "Segoe UI")
        }
        eg.Add("Text", "x" xp " y" (py + sh + 4) " w" sw " Center", fNames[i])
    }

    eg.SetFont("s7 cFF6348", "Segoe UI")
    eg.Add("Text", "x" (px + 1 * 40) " y" (py + sh + 20) " w120", "🔴 LOW 쿵쿵")
    eg.SetFont("s7 cFFA502", "Segoe UI")
    eg.Add("Text", "x" (px + 10 * 40) " y" (py + sh + 20) " w120", "🟠 HIGH 딱딱")

    pY := py + sh + 44
    eg.SetFont("s9 c888888", "Segoe UI")
    eg.Add("Text", "x" px " y" pY " w55", "Preamp")
    eg.Add("Slider", "x" (px + 60) " y" (pY - 2) " w200 Range-12-6 ToolTip vPreamp", vals[16])
    eg.SetFont("s9 cCCCCCC", "Consolas")
    eg.Add("Text", "x" (px + 270) " y" pY " w50 vPL", String(vals[16]) " dB")

    bY := pY + 38
    eg.SetFont("s9 cFFFFFF", "Segoe UI")
    b1 := eg.Add("Button", "x" px " y" bY " w105 h30", "🎮 FPS")
    b2 := eg.Add("Button", "x" (px + 113) " y" bY " w105 h30", "💥 Bass")
    b3 := eg.Add("Button", "x" (px + 226) " y" bY " w105 h30", "🎵 Balanced")
    b4 := eg.Add("Button", "x" (px + 339) " y" bY " w105 h30", "⬜ Flat")

    b1.OnEvent("Click", DoFPS)
    b2.OnEvent("Click", DoBass)
    b3.OnEvent("Click", DoBalanced)
    b4.OnEvent("Click", DoFlat)

    aY := bY + 42
    eg.SetFont("s12 cFFFFFF Bold", "Segoe UI")
    ab := eg.Add("Button", "x" (px + 150) " y" aY " w180 h38", "✅  APPLY")
    ab.OnEvent("Click", DoApply)

    gH := aY + 52
    eg.Show("w600 h" gH)

    DoFPS(*)      => FillEQ(eg, [-2,4,7,8,6,4,1,-1,-2,0,4,5,2,-1,-3], -3)
    DoBass(*)     => FillEQ(eg, [3,7,9,10,7,4,0,-2,-3,-2,0,1,0,-1,-2], -5)
    DoBalanced(*) => FillEQ(eg, [0,2,4,5,4,3,1,0,0,1,3,3,1,0,-1], -2)
    DoFlat(*)     => FillEQ(eg, [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0], 0)

    DoApply(*) {
        pr := eg["Preamp"].Value
        parts := []
        loop 15 {
            v := eg["EQ" A_Index].Value
            parts.Push(fNums[A_Index] " " v)
            eg["VL" A_Index].Value := String(v)
        }
        eg["PL"].Value := String(pr) " dB"

        eqStr := ""
        for idx, p in parts {
            if idx > 1
                eqStr .= "; "
            eqStr .= p
        }

        txt := "# Footstep Amplifier`nPreamp: " pr " dB`nGraphicEQ: " eqStr "`n"
        fp := "C:\Program Files\EqualizerAPO\config\footstep-boost.txt"
        try FileDelete(fp)
        FileAppend(txt, fp)

        if gFootstepOn {
            mc := "C:\Program Files\EqualizerAPO\config\config.txt"
            try FileDelete(mc)
            FileAppend("Include: footstep-boost.txt", mc)
        }
        ShowOverlay("✅", "EQ Applied", "Settings Saved", "0x2ed573")
    }
}

FillEQ(g, v, pr) {
    loop 15 {
        g["EQ" A_Index].Value := v[A_Index]
        g["VL" A_Index].Value := String(v[A_Index])
    }
    g["Preamp"].Value := pr
    g["PL"].Value := String(pr) " dB"
}

LoadEQ() {
    fp := "C:\Program Files\EqualizerAPO\config\footstep-boost.txt"
    vals := []
    pr := -3
    try {
        content := FileRead(fp)
        loop Parse content, "`n" {
            line := A_LoopField
            if InStr(line, "Preamp:") {
                if RegExMatch(line, "(-?\d+)", &m)
                    pr := Integer(m[0])
            }
            if InStr(line, "GraphicEQ:") {
                if RegExMatch(line, "GraphicEQ:\s*(.*)", &em) {
                    loop Parse em[1], ";" {
                        pair := Trim(A_LoopField)
                        if pair != "" {
                            sp := StrSplit(pair, " ")
                            if sp.Length >= 2
                                vals.Push(Integer(sp[2]))
                        }
                    }
                }
            }
        }
    }
    while vals.Length < 15
        vals.Push(0)
    vals.Push(pr)
    return vals
}

; ==================== TRAY INDICATOR ====================
ShowTray() {
    global gTrayIndicator
    if gTrayIndicator {
        gTrayIndicator.Destroy()
        gTrayIndicator := ""
    }
    gTrayIndicator := Gui("+AlwaysOnTop -Caption +ToolWindow +E0x20 +E0x80000")
    gTrayIndicator.BackColor := "0a0a1a"
    WinSetTransparent(140, gTrayIndicator)
    gTrayIndicator.SetFont("s18 cFF6348", "Segoe UI Emoji")
    gTrayIndicator.Add("Text", "x4 y2 w36 Center", "🦶")
    gTrayIndicator.SetFont("s7 cFF6348", "Segoe UI")
    gTrayIndicator.Add("Text", "x0 y28 w44 Center", "BOOST")
    gTrayIndicator.Show("x" (A_ScreenWidth - 56) " y" (A_ScreenHeight - 86) " w44 h42 NoActivate")
    SetTimer(ChkDesk, 1000)
}

HideTray() {
    global gTrayIndicator
    if gTrayIndicator {
        gTrayIndicator.Destroy()
        gTrayIndicator := ""
    }
    SetTimer(ChkDesk, 0)
}

ChkDesk() {
    global gTrayIndicator, gFootstepOn
    if !gFootstepOn or !gTrayIndicator
        return
    ac := WinGetClass("A")
    ae := ""
    try ae := WinGetProcessName("A")
    ok := (ac = "Progman" or ac = "WorkerW" or ac = "Shell_TrayWnd" or ac = "CabinetWClass" or ae = "explorer.exe")
    if ok {
        try gTrayIndicator.Show("NoActivate")
    } else {
        try gTrayIndicator.Hide()
    }
}

; ==================== OVERLAY ====================
ShowOverlay(emoji, title, subtitle, accentColor) {
    global gOverlay
    if gOverlay {
        gOverlay.Destroy()
        gOverlay := ""
    }
    gw := 340
    gh := 200
    gOverlay := Gui("+AlwaysOnTop -Caption +ToolWindow +E0x20")
    gOverlay.BackColor := "1a1a2e"
    WinSetTransparent(220, gOverlay)
    gOverlay.SetFont("s80 cFFFFFF", "Segoe UI Emoji")
    gOverlay.Add("Text", "x0 y8 w" gw " Center", emoji)
    gOverlay.SetFont("s20 c" accentColor " Bold", "Segoe UI")
    gOverlay.Add("Text", "x0 y110 w" gw " Center", title)
    gOverlay.SetFont("s11 cAAAAAA", "Segoe UI")
    gOverlay.Add("Text", "x0 y145 w" gw " Center", subtitle)
    gOverlay.SetFont("s2 c" accentColor, "Segoe UI")
    gOverlay.Add("Text", "x70 y175 w200 Center", "━━━━━━━━━━━━━━━━━━━━")
    gOverlay.Show("x" ((A_ScreenWidth - gw) // 2) " y" ((A_ScreenHeight - gh) // 2) " w" gw " h" gh " NoActivate")
    SetTimer(CloseOL, -2000)
}

CloseOL() {
    global gOverlay
    if gOverlay {
        gOverlay.Destroy()
        gOverlay := ""
    }
}

RunCmd(command) {
    sh := ComObject("WScript.Shell")
    ex := sh.Exec(command)
    return ex.StdOut.ReadAll()
}
