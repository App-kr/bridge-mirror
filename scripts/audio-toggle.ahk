#Requires AutoHotkey v2.0
#SingleInstance Force
Persistent

global gOverlay := ""
global gTrayIndicator := ""
global gFootstepOn := false
global gEqGui := ""

; ===== Audio Toggle: Ctrl+Shift+F9 =====
^+F9:: {
    result := RunWaitOne('powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File "Q:\Claudework\bridge base\scripts\audio-toggle.ps1"')
    result := Trim(result)
    if InStr(result, "HEADSET")
        ShowOverlay("🎧", "Headset ON", "Captain 780LITE", "0x6C5CE7")
    else
        ShowOverlay("🔊", "Speaker ON", "Stand Mic + Speaker", "0xFFA502")
}

; ===== Footstep Boost Toggle: Ctrl+Shift+F10 =====
^+F10:: {
    global gFootstepOn
    configFile := "C:\Program Files\EqualizerAPO\config\config.txt"
    if gFootstepOn {
        FileDelete(configFile)
        FileAppend("Include: flat.txt", configFile)
        gFootstepOn := false
        ShowOverlay("👟", "Footstep OFF", "Normal Audio", "0x636e72")
        HideTrayIndicator()
    } else {
        FileDelete(configFile)
        FileAppend("Include: footstep-boost.txt", configFile)
        gFootstepOn := true
        ShowOverlay("🦶", "Footstep ON", "Bass + Step Enhanced", "0xFF6348")
        ShowTrayIndicator()
    }
}

; ===== EQ Editor: Ctrl+Shift+F11 =====
^+F11:: {
    OpenEQEditor()
}

; ==================== EQ EDITOR ====================
OpenEQEditor() {
    global gEqGui

    if gEqGui {
        gEqGui.Destroy()
        gEqGui := ""
    }

    freqNames := ["25", "40", "63", "100", "160", "250", "400", "630", "1K", "1.6K", "2.5K", "4K", "6.3K", "10K", "16K"]
    freqNums  := [25, 40, 63, 100, 160, 250, 400, 630, 1000, 1600, 2500, 4000, 6300, 10000, 16000]

    ; Read current values
    vals := ReadEQValues()
    preampVal := vals.RemoveAt(vals.Length)

    sliderW := 36
    sliderH := 200
    padLeft := 40
    padTop := 90
    gap := 4
    totalSliders := 15
    guiW := padLeft + totalSliders * (sliderW + gap) + 40
    guiH := padTop + sliderH + 160

    gEqGui := Gui("+AlwaysOnTop -MaximizeBox", "")
    gEqGui.BackColor := "16161e"
    gEqGui.MarginX := 0
    gEqGui.MarginY := 0

    ; Header
    gEqGui.SetFont("s16 c0xFFFFFF Bold", "Segoe UI")
    gEqGui.Add("Text", "x20 y16 w300", "🎛️  EQ Editor")

    gEqGui.SetFont("s9 c0x555555", "Segoe UI")
    gEqGui.Add("Text", "x" (guiW - 200) " y22 w180 Right", "EqualizerAPO")

    ; +12 / 0 / -12 guide labels
    gEqGui.SetFont("s8 c0x444444", "Consolas")
    guideX := 8
    gEqGui.Add("Text", "x" guideX " y" padTop " w30 Right", "+12")
    gEqGui.Add("Text", "x" guideX " y" (padTop + sliderH // 2 - 6) " w30 Right", "0")
    gEqGui.Add("Text", "x" guideX " y" (padTop + sliderH - 12) " w30 Right", "-12")

    ; Zero line
    lineY := padTop + sliderH // 2
    gEqGui.SetFont("s1 c0x2a2a3a", "Segoe UI")
    gEqGui.Add("Text", "x" padLeft " y" lineY " w" (totalSliders * (sliderW + gap)) " h1 +0x1000")

    ; Vertical sliders + labels
    loop totalSliders {
        i := A_Index
        xPos := padLeft + (i - 1) * (sliderW + gap)

        ; dB value label (top)
        gEqGui.SetFont("s7 c0x888888", "Consolas")
        gEqGui.Add("Text", "x" xPos " y" (padTop - 16) " w" sliderW " Center vValLabel" i, vals[i])

        ; Vertical slider
        gEqGui.Add("Slider", "x" xPos " y" padTop " w" sliderW " h" sliderH " Vertical Range-12-12 Invert NoTicks vEQ" i, Integer(vals[i]))

        ; Freq label (bottom) - color coded
        freqY := padTop + sliderH + 6
        if i >= 2 and i <= 5
            gEqGui.SetFont("s7 c0xFF6348 Bold", "Segoe UI")  ; Low = red
        else if i >= 11 and i <= 13
            gEqGui.SetFont("s7 c0xFFA502 Bold", "Segoe UI")  ; High = orange
        else
            gEqGui.SetFont("s7 c0x666666", "Segoe UI")

        gEqGui.Add("Text", "x" xPos " y" freqY " w" sliderW " Center", freqNames[i])

        ; Zone label
        if i = 3 {
            gEqGui.SetFont("s7 c0xFF6348", "Segoe UI")
            gEqGui.Add("Text", "x" xPos " y" (freqY + 16) " w120 Center", "🔴 LOW 쿵쿵")
        }
        if i = 11 {
            gEqGui.SetFont("s7 c0xFFA502", "Segoe UI")
            gEqGui.Add("Text", "x" xPos " y" (freqY + 16) " w120 Center", "🟠 HIGH 딱딱")
        }
    }

    ; Preamp
    preampY := padTop + sliderH + 50
    gEqGui.SetFont("s9 c0x888888", "Segoe UI")
    gEqGui.Add("Text", "x" padLeft " y" preampY " w60", "Preamp")
    gEqGui.Add("Slider", "x" (padLeft + 65) " y" (preampY - 2) " w200 Range-12-6 ToolTip vPreamp", Integer(preampVal))
    gEqGui.SetFont("s9 c0xCCCCCC", "Consolas")
    gEqGui.Add("Text", "x" (padLeft + 275) " y" preampY " w50 vPreampLabel", preampVal " dB")

    ; Buttons
    btnY := preampY + 40
    btnW := 110
    btnH := 32

    ; Presets
    gEqGui.SetFont("s9 c0xFFFFFF", "Segoe UI")
    b1 := gEqGui.Add("Button", "x" padLeft " y" btnY " w" btnW " h" btnH, "🎮 FPS")
    b1.OnEvent("Click", (*) => SetPreset([-2,4,7,8,6,4,1,-1,-2,0,4,5,2,-1,-3], -3))

    b2 := gEqGui.Add("Button", "x" (padLeft + btnW + 8) " y" btnY " w" btnW " h" btnH, "💥 Bass")
    b2.OnEvent("Click", (*) => SetPreset([3,7,9,10,7,4,0,-2,-3,-2,0,1,0,-1,-2], -5))

    b3 := gEqGui.Add("Button", "x" (padLeft + (btnW + 8) * 2) " y" btnY " w" btnW " h" btnH, "🎵 Balanced")
    b3.OnEvent("Click", (*) => SetPreset([0,2,4,5,4,3,1,0,0,1,3,3,1,0,-1], -2))

    b4 := gEqGui.Add("Button", "x" (padLeft + (btnW + 8) * 3) " y" btnY " w" btnW " h" btnH, "⬜ Flat")
    b4.OnEvent("Click", (*) => SetPreset([0,0,0,0,0,0,0,0,0,0,0,0,0,0,0], 0))

    ; Apply button
    applyY := btnY + 44
    gEqGui.SetFont("s11 c0xFFFFFF Bold", "Segoe UI")
    applyBtn := gEqGui.Add("Button", "x" (guiW // 2 - 80) " y" applyY " w160 h38", "✅  APPLY")
    applyBtn.OnEvent("Click", (*) => ApplyEQSettings())

    guiH := applyY + 55
    gEqGui.Show("w" guiW " h" guiH)
}

SetPreset(vals, preamp) {
    global gEqGui
    if !gEqGui
        return
    loop 15 {
        gEqGui["EQ" A_Index].Value := Integer(vals[A_Index])
        gEqGui["ValLabel" A_Index].Value := vals[A_Index]
    }
    gEqGui["Preamp"].Value := Integer(preamp)
    gEqGui["PreampLabel"].Value := preamp " dB"
}

ApplyEQSettings() {
    global gEqGui, gFootstepOn
    if !gEqGui
        return

    freqNums := [25, 40, 63, 100, 160, 250, 400, 630, 1000, 1600, 2500, 4000, 6300, 10000, 16000]
    preamp := gEqGui["Preamp"].Value
    eqParts := []

    loop 15 {
        val := gEqGui["EQ" A_Index].Value
        eqParts.Push(freqNums[A_Index] " " val)
        gEqGui["ValLabel" A_Index].Value := val
    }
    gEqGui["PreampLabel"].Value := preamp " dB"

    eqStr := ""
    for i, part in eqParts {
        if i > 1
            eqStr .= "; "
        eqStr .= part
    }

    content := "# Footstep Amplifier - custom`nPreamp: " preamp " dB`nGraphicEQ: " eqStr "`n"

    configPath := "C:\Program Files\EqualizerAPO\config\footstep-boost.txt"
    try FileDelete(configPath)
    FileAppend(content, configPath)

    if gFootstepOn {
        mainConfig := "C:\Program Files\EqualizerAPO\config\config.txt"
        try FileDelete(mainConfig)
        FileAppend("Include: footstep-boost.txt", mainConfig)
    }

    ShowOverlay("✅", "EQ Applied", "Settings Saved", "0x2ed573")
}

ReadEQValues() {
    configPath := "C:\Program Files\EqualizerAPO\config\footstep-boost.txt"
    vals := []
    preamp := -3

    try {
        content := FileRead(configPath)
        for line in StrSplit(content, "`n") {
            if InStr(line, "Preamp:") {
                RegExMatch(line, "(-?\d+)", &m)
                if m
                    preamp := Integer(m[0])
            }
            if InStr(line, "GraphicEQ:") {
                RegExMatch(line, "GraphicEQ:\s*(.*)", &eqMatch)
                if eqMatch {
                    for pair in StrSplit(eqMatch[1], ";") {
                        pair := Trim(pair)
                        if pair {
                            parts := StrSplit(pair, " ")
                            if parts.Length >= 2
                                vals.Push(Integer(parts[2]))
                        }
                    }
                }
            }
        }
    }

    while vals.Length < 15
        vals.Push(0)
    vals.Push(preamp)
    return vals
}

; ==================== TRAY INDICATOR ====================
ShowTrayIndicator() {
    global gTrayIndicator
    if gTrayIndicator {
        gTrayIndicator.Destroy()
        gTrayIndicator := ""
    }

    gTrayIndicator := Gui("+AlwaysOnTop -Caption +ToolWindow +E0x20 +E0x80000")
    gTrayIndicator.BackColor := "0a0a1a"
    WinSetTransparent(140, gTrayIndicator)

    gTrayIndicator.SetFont("s18 c0xFF6348", "Segoe UI Emoji")
    gTrayIndicator.Add("Text", "x4 y2 w36 Center", "🦶")
    gTrayIndicator.SetFont("s7 c0xFF6348", "Segoe UI")
    gTrayIndicator.Add("Text", "x0 y28 w44 Center", "BOOST")

    posX := A_ScreenWidth - 56
    posY := A_ScreenHeight - 86
    gTrayIndicator.Show("x" posX " y" posY " w44 h42 NoActivate")
    SetTimer(CheckDesktop, 1000)
}

HideTrayIndicator() {
    global gTrayIndicator
    if gTrayIndicator {
        gTrayIndicator.Destroy()
        gTrayIndicator := ""
    }
    SetTimer(CheckDesktop, 0)
}

CheckDesktop() {
    global gTrayIndicator, gFootstepOn
    if !gFootstepOn or !gTrayIndicator
        return
    activeClass := WinGetClass("A")
    activeExe := ""
    try activeExe := WinGetProcessName("A")

    isDesktop := (activeClass = "Progman" or activeClass = "WorkerW" or activeClass = "Shell_TrayWnd" or activeClass = "CabinetWClass" or activeExe = "explorer.exe")

    if isDesktop
        try gTrayIndicator.Show("NoActivate")
    else
        try gTrayIndicator.Hide()
}

; ==================== OVERLAY ====================
ShowOverlay(emoji, title, subtitle, accentColor) {
    global gOverlay
    if gOverlay {
        gOverlay.Destroy()
        gOverlay := ""
    }

    guiW := 340
    guiH := 200
    gOverlay := Gui("+AlwaysOnTop -Caption +ToolWindow +E0x20")
    gOverlay.BackColor := "1a1a2e"
    WinSetTransparent(220, gOverlay)

    gOverlay.SetFont("s80 c0xFFFFFF", "Segoe UI Emoji")
    gOverlay.Add("Text", "x0 y8 w" guiW " Center", emoji)
    gOverlay.SetFont("s20 c" accentColor " Bold", "Segoe UI")
    gOverlay.Add("Text", "x0 y110 w" guiW " Center", title)
    gOverlay.SetFont("s11 c0xAAAAAA", "Segoe UI")
    gOverlay.Add("Text", "x0 y145 w" guiW " Center", subtitle)
    gOverlay.SetFont("s2 c" accentColor, "Segoe UI")
    gOverlay.Add("Text", "x70 y175 w200 Center", "━━━━━━━━━━━━━━━━━━━━")

    posX := (A_ScreenWidth - guiW) // 2
    posY := (A_ScreenHeight - guiH) // 2
    gOverlay.Show("x" posX " y" posY " w" guiW " h" guiH " NoActivate")
    SetTimer(CloseOverlay, -2000)
}

CloseOverlay() {
    global gOverlay
    if gOverlay {
        gOverlay.Destroy()
        gOverlay := ""
    }
}

RunWaitOne(command) {
    shell := ComObject("WScript.Shell")
    exec := shell.Exec(command)
    return exec.StdOut.ReadAll()
}
