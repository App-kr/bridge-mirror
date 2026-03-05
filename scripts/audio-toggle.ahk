#Requires AutoHotkey v2.0
#SingleInstance Force
Persistent

global gOverlay := ""
global gTrayIndicator := ""
global gFootstepOn := false

; ===== Ctrl+Shift+F9: Audio Toggle =====
^+F9:: {
    try {
        sh := ComObject("WScript.Shell")
        ex := sh.Exec('powershell.exe -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File "Q:\Claudework\bridge base\scripts\audio-toggle.ps1"')
        result := Trim(ex.StdOut.ReadAll())
        if InStr(result, "HEADSET") {
            ShowOverlay("🎧", "Headset ON", "Captain 780LITE", "0x6C5CE7")
        } else if InStr(result, "NO_HEADSET") {
            ShowOverlay("❌", "No Headset", "Turn on headset first", "0xFF4757")
        } else {
            ShowOverlay("🔊", "Speaker ON", "Stand Mic + Speaker", "0xFFA502")
        }
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

; ==================== EQ EDITOR (PUBG STYLE) ====================
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

    sw := 38
    sh := 220
    px := 50
    py := 105
    guiW := 660

    eg := Gui("+AlwaysOnTop -MaximizeBox", "BATTLEGROUND AUDIO")
    eg.BackColor := "1a1f0e"

    ; === HEADER: Military title bar ===
    eg.SetFont("s7 c3d4a1a", "Consolas")
    eg.Add("Text", "x0 y0 w" guiW " h28 +0x1000 Background2b3316")
    eg.SetFont("s13 cF2A900 Bold", "Consolas")
    eg.Add("Text", "x18 y4 w400", ">> SOUND TACTICAL EQ")
    eg.SetFont("s8 c5a6b2a", "Consolas")
    eg.Add("Text", "x" (guiW - 180) " y8 w170 Right", "[ EQUALIZE & DOMINATE ]")

    ; === Subtitle ===
    eg.SetFont("s8 c6b7d3a", "Consolas")
    eg.Add("Text", "x18 y36 w300", "FREQUENCY CONTROL SYSTEM v2.0")

    ; === Zone header ===
    eg.SetFont("s9 cD4442A Bold", "Consolas")
    eg.Add("Text", "x" px " y56 w180", "!! FOOTSTEP ZONE")
    eg.SetFont("s9 c8B8000 Bold", "Consolas")
    eg.Add("Text", "x" (px + 200) " y56 w120", "-- NEUTRAL --")
    eg.SetFont("s9 cD4842A Bold", "Consolas")
    eg.Add("Text", "x" (px + 380) " y56 w180", "!! STEP DETAIL")

    ; === dB Guide ===
    eg.SetFont("s8 c4a5a2a", "Consolas")
    eg.Add("Text", "x4 y" py " w42 Right", "+12dB")
    eg.Add("Text", "x4 y" (py + sh // 2 - 6) " w42 Right", "  0dB")
    eg.Add("Text", "x4 y" (py + sh - 12) " w42 Right", "-12dB")

    ; === Zero line (horizontal) ===
    zeroY := py + sh // 2
    eg.SetFont("s1 c2b3316", "Consolas")
    eg.Add("Text", "x" px " y" zeroY " w" (15 * (sw + 2)) " h1 +0x1000 Background3d4a1a")

    ; === Sliders ===
    loop 15 {
        i := A_Index
        xp := px + (i - 1) * (sw + 2)

        ; dB value top
        eg.SetFont("s7 cF2A900", "Consolas")
        eg.Add("Text", "x" xp " y" (py - 16) " w" sw " Center vVL" i, String(vals[i]))

        ; Slider
        eg.Add("Slider", "x" xp " y" py " w" sw " h" sh " Vertical Range-12-12 Invert NoTicks vEQ" i, vals[i])

        ; Freq label bottom - color by zone
        if (i >= 2 and i <= 5) {
            eg.SetFont("s7 cFF4444 Bold", "Consolas")
        } else if (i >= 11 and i <= 13) {
            eg.SetFont("s7 cFF8C00 Bold", "Consolas")
        } else {
            eg.SetFont("s7 c5a6b2a", "Consolas")
        }
        eg.Add("Text", "x" xp " y" (py + sh + 4) " w" sw " Center", fNames[i])
    }

    ; === Zone markers ===
    markerY := py + sh + 22
    eg.SetFont("s7 cFF4444", "Consolas")
    eg.Add("Text", "x" (px + 1 * 40) " y" markerY " w150", "[BOOM] Low Freq")
    eg.SetFont("s7 cFF8C00", "Consolas")
    eg.Add("Text", "x" (px + 10 * 40) " y" markerY " w150", "[TAP] High Freq")

    ; === Preamp ===
    pY := markerY + 26
    eg.SetFont("s1 c2b3316", "Consolas")
    eg.Add("Text", "x18 y" (pY - 8) " w" (guiW - 36) " h1 +0x1000 Background3d4a1a")

    eg.SetFont("s9 cF2A900 Bold", "Consolas")
    eg.Add("Text", "x" px " y" pY " w70", "PREAMP")
    eg.Add("Slider", "x" (px + 75) " y" (pY - 2) " w220 Range-12-6 ToolTip vPreamp", vals[16])
    eg.SetFont("s9 cF2A900", "Consolas")
    eg.Add("Text", "x" (px + 305) " y" pY " w60 vPL", String(vals[16]) " dB")

    ; === Preset Buttons (PUBG loot style) ===
    bY := pY + 38
    eg.SetFont("s9 cFFFFFF Bold", "Consolas")
    b1 := eg.Add("Button", "x" px " y" bY " w120 h32", ">> PUBG FPS")
    b2 := eg.Add("Button", "x" (px + 128) " y" bY " w120 h32", ">> BASS DROP")
    b3 := eg.Add("Button", "x" (px + 256) " y" bY " w120 h32", ">> BALANCED")
    b4 := eg.Add("Button", "x" (px + 384) " y" bY " w120 h32", ">> FLAT RESET")

    b1.OnEvent("Click", DoFPS)
    b2.OnEvent("Click", DoBass)
    b3.OnEvent("Click", DoBalanced)
    b4.OnEvent("Click", DoFlat)

    ; === DEPLOY Button ===
    aY := bY + 46
    eg.SetFont("s13 c1a1f0e Bold", "Consolas")
    ab := eg.Add("Button", "x" (px + 140) " y" aY " w220 h42", "DEPLOY  >>")
    ab.OnEvent("Click", DoApply)

    ; === Footer ===
    fY := aY + 50
    eg.SetFont("s7 c3d4a1a", "Consolas")
    eg.Add("Text", "x18 y" fY " w" (guiW - 36) " Center", "WINNER WINNER CHICKEN DINNER")

    eg.Show("w" guiW " h" (fY + 22))

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
        ShowOverlay("🎯", "DEPLOYED", "EQ Config Active", "0xF2A900")
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

; ==================== TRAY ====================
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
