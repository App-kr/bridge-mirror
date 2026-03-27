#Requires AutoHotkey v2.0
#SingleInstance Force
Persistent

global gOverlay := ""
global gTrayIndicator := ""
global gTrayVisible := false
global gFootstepOn := false
global gEqGui := ""
global gTestBackup := ""

; ===== WM_NCHITTEST — drag EQ window by top bar =====
OnMessage(0x84, EQ_HitTest)

; ===== 모니터 신호 감지 (USB 이벤트 기반) =====
SetTimer CheckMonitorSignal, 1000

CheckMonitorSignal() {
    headsetSignal := "Q:\Claudework\bridge base\scripts\audio\signal-headset-on.txt"
    speakerSignal := "Q:\Claudework\bridge base\scripts\audio\signal-speaker-on.txt"

    if FileExist(headsetSignal) {
        FileDelete(headsetSignal)
        ShowOverlay("🎧", "Headset ON", "Captain 780", "0x6C5CE7")
    }
    if FileExist(speakerSignal) {
        FileDelete(speakerSignal)
        ShowOverlay("🔊", "Speaker ON", "Stand Mic + Speaker", "0xFFA502")
    }
}

EQ_HitTest(wParam, lParam, msg, hwnd) {
    global gEqGui
    if !IsObject(gEqGui)
        return
    try guiHwnd := gEqGui.Hwnd
    catch
        return
    isParent := (hwnd = guiHwnd)
    isChild := false
    if !isParent {
        par := DllCall("GetParent", "Ptr", hwnd, "Ptr")
        isChild := (par = guiHwnd)
    }
    if !isParent and !isChild
        return
    sx := lParam & 0xFFFF
    sy := (lParam >> 16) & 0xFFFF
    if (sx > 32767)
        sx -= 65536
    if (sy > 32767)
        sy -= 65536
    try WinGetPos(&wx, &wy,,, guiHwnd)
    catch
        return
    ry := sy - wy
    rx := sx - wx
    if (ry >= 0 and ry < 52 and rx < 630) {
        if isParent
            return 2
        return -1
    }
}

; ===== Helper: Write file in-place (APO detects changes) =====
WriteConfig(path, content) {
    try {
        f := FileOpen(path, "w", "UTF-8-RAW")
        f.Write(content)
        f.Close()
    } catch as e {
        try FileDelete(path)
        FileAppend(content, path)
    }
}

; ===== Helper: Build EQ config text from arrays =====
BuildEQText(freqs, gains, preamp) {
    eqStr := ""
    loop freqs.Length {
        if A_Index > 1
            eqStr .= "; "
        eqStr .= freqs[A_Index] " " gains[A_Index] ".0"
    }
    return "Preamp: " preamp " dB`nGraphicEQ: " eqStr "`n"
}

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
        WriteConfig(cf, "Include: flat.txt")
        gFootstepOn := false
        ShowOverlay("👟", "Footstep OFF", "Normal Audio", "0x636e72")
        HideTray()
    } else {
        WriteConfig(cf, "Include: footstep-boost.txt")
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
    global gEqGui, gFootstepOn

    if gEqGui {
        gEqGui.Destroy()
        gEqGui := ""
    }

    fNames := ["25","40","63","100","160","250","400","630","1K","1.6K","2.5K","4K","6.3K","10K","16K"]
    fNums := [25,40,63,100,160,250,400,630,1000,1600,2500,4000,6300,10000,16000]
    vals := LoadEQ()

    sw := 36
    sh := 200
    px := 46
    py := 96
    guiW := 720

    eg := Gui("+AlwaysOnTop -Caption -Border +ToolWindow +E0x80000")
    eg.BackColor := "1e2a14"

    ; ═══ TOP BAR (drag to move) ═══
    eg.Add("Text", "x0 y0 w" guiW " h52 +0x1000 Background1a2210")
    eg.SetFont("s20 cFFFFFF", "Segoe UI Emoji")
    eg.Add("Text", "x16 y8 w40 BackgroundTrans", "🎯")
    eg.SetFont("s13 cF0C040 Bold", "Segoe UI")
    eg.Add("Text", "x52 y8 w300 BackgroundTrans", "TACTICAL AUDIO")
    eg.SetFont("s8 c6a7a4a", "Segoe UI")
    eg.Add("Text", "x52 y30 w300 BackgroundTrans", "Sound Enhancement System")

    ; Close button (wide)
    eg.Add("Text", "x" (guiW - 96) " y8 w86 h34 +0x1000 Background2a1515")
    eg.SetFont("s11 cCC6666 Bold", "Segoe UI")
    xBtn := eg.Add("Text", "x" (guiW - 96) " y14 w86 h22 Center BackgroundTrans", "✕ 닫기")
    xBtn.OnEvent("Click", CloseEQ)

    ; ═══ ZONE LABELS ═══
    zY := 58
    eg.SetFont("s8 cFF6B6B", "Consolas")
    eg.Add("Text", "x" px " y" zY " w180 BackgroundTrans", "● BASS  25~250Hz")
    eg.SetFont("s8 c88CC88", "Consolas")
    eg.Add("Text", "x" (px + 192) " y" zY " w170 BackgroundTrans", "● MID  400~1.6KHz")
    eg.SetFont("s8 cFFAA44", "Consolas")
    eg.Add("Text", "x" (px + 384) " y" zY " w170 BackgroundTrans", "● HIGH  2.5K~16KHz")

    ; ═══ dB SCALE ═══
    eg.SetFont("s7 c4a5a3a", "Consolas")
    eg.Add("Text", "x2 y" (py - 2) " w40 Right BackgroundTrans", "+12")
    eg.Add("Text", "x2 y" (py + sh // 2 - 6) " w40 Right BackgroundTrans", "  0")
    eg.Add("Text", "x2 y" (py + sh - 12) " w40 Right BackgroundTrans", "-12")
    eg.Add("Text", "x" px " y" (py + sh // 2) " w" (15 * (sw + 2)) " h1 +0x1000 Background3a4a2a")

    ; ═══ SLIDERS ═══
    loop 15 {
        i := A_Index
        xp := px + (i - 1) * (sw + 2)
        eg.SetFont("s7 cF0C040", "Consolas")
        eg.Add("Text", "x" xp " y" (py - 16) " w" sw " Center BackgroundTrans vVL" i, String(vals[i]))
        eg.Add("Slider", "x" xp " y" py " w" sw " h" sh " Vertical Range-12-12 Invert NoTicks vEQ" i, vals[i])
        if (i >= 2 and i <= 5) {
            eg.SetFont("s6 cFF6B6B", "Consolas")
        } else if (i >= 11) {
            eg.SetFont("s6 cFFAA44", "Consolas")
        } else {
            eg.SetFont("s6 c6a7a4a", "Consolas")
        }
        eg.Add("Text", "x" xp " y" (py + sh + 4) " w" sw " Center BackgroundTrans", fNames[i])
    }

    ; ═══ PREAMP ═══
    pY := py + sh + 26
    eg.SetFont("s9 cF0C040 Bold", "Segoe UI")
    eg.Add("Text", "x16 y" pY " w80 BackgroundTrans", "⚡ VOL")
    eg.Add("Slider", "x90 y" (pY - 2) " w400 Range-12-6 ToolTip vPreamp", vals[16])
    eg.SetFont("s10 cFFFFFF Bold", "Consolas")
    eg.Add("Text", "x500 y" pY " w60 BackgroundTrans vPL", String(vals[16]) " dB")

    ; ═══ PRESETS 2x2 ═══
    bY := pY + 40
    gap := 10
    cW := (guiW - 32 - gap) // 2
    cH := 56
    x1 := 16
    x2 := x1 + cW + gap

    ; FPS MODE
    eg.Add("Text", "x" x1 " y" bY " w" cW " h" cH " +0x1000 Background3a1a1a")
    eg.SetFont("s22", "Segoe UI Emoji")
    eg.Add("Text", "x" (x1 + 12) " y" (bY + 8) " w40 BackgroundTrans", "🎮")
    eg.SetFont("s12 cFF6B6B Bold", "Segoe UI")
    eg.Add("Text", "x" (x1 + 52) " y" (bY + 6) " w200 BackgroundTrans", "FPS MODE")
    eg.SetFont("s8 cBB8888", "Segoe UI")
    eg.Add("Text", "x" (x1 + 52) " y" (bY + 30) " w200 BackgroundTrans", "Footstep & Gunshot")
    b1c := eg.Add("Text", "x" x1 " y" bY " w" cW " h" cH " +0x1000 BackgroundTrans")
    b1c.OnEvent("Click", DoFPS)

    ; BASS DROP
    eg.Add("Text", "x" x2 " y" bY " w" cW " h" cH " +0x1000 Background1a1a3a")
    eg.SetFont("s22", "Segoe UI Emoji")
    eg.Add("Text", "x" (x2 + 12) " y" (bY + 8) " w40 BackgroundTrans", "💥")
    eg.SetFont("s12 c7777FF Bold", "Segoe UI")
    eg.Add("Text", "x" (x2 + 52) " y" (bY + 6) " w200 BackgroundTrans", "BASS DROP")
    eg.SetFont("s8 c8888BB", "Segoe UI")
    eg.Add("Text", "x" (x2 + 52) " y" (bY + 30) " w200 BackgroundTrans", "Heavy Sub-Bass")
    b2c := eg.Add("Text", "x" x2 " y" bY " w" cW " h" cH " +0x1000 BackgroundTrans")
    b2c.OnEvent("Click", DoBass)

    ; BALANCED
    bY2 := bY + cH + gap
    eg.Add("Text", "x" x1 " y" bY2 " w" cW " h" cH " +0x1000 Background1a3a1a")
    eg.SetFont("s22", "Segoe UI Emoji")
    eg.Add("Text", "x" (x1 + 12) " y" (bY2 + 8) " w40 BackgroundTrans", "🎵")
    eg.SetFont("s12 c66CC66 Bold", "Segoe UI")
    eg.Add("Text", "x" (x1 + 52) " y" (bY2 + 6) " w200 BackgroundTrans", "BALANCED")
    eg.SetFont("s8 c88BB88", "Segoe UI")
    eg.Add("Text", "x" (x1 + 52) " y" (bY2 + 30) " w200 BackgroundTrans", "All-Round Clean")
    b3c := eg.Add("Text", "x" x1 " y" bY2 " w" cW " h" cH " +0x1000 BackgroundTrans")
    b3c.OnEvent("Click", DoBalanced)

    ; FLAT RESET
    eg.Add("Text", "x" x2 " y" bY2 " w" cW " h" cH " +0x1000 Background2a2a2a")
    eg.SetFont("s22", "Segoe UI Emoji")
    eg.Add("Text", "x" (x2 + 12) " y" (bY2 + 8) " w40 BackgroundTrans", "⬜")
    eg.SetFont("s12 cAAAAAA Bold", "Segoe UI")
    eg.Add("Text", "x" (x2 + 52) " y" (bY2 + 6) " w200 BackgroundTrans", "FLAT RESET")
    eg.SetFont("s8 c999999", "Segoe UI")
    eg.Add("Text", "x" (x2 + 52) " y" (bY2 + 30) " w200 BackgroundTrans", "No Effect")
    b4c := eg.Add("Text", "x" x2 " y" bY2 " w" cW " h" cH " +0x1000 BackgroundTrans")
    b4c.OnEvent("Click", DoFlat)

    ; ═══ 3 ACTION BUTTONS: 테스트 | 적용 | 닫기 ═══
    aY := bY2 + cH + 14
    btnGap := 10
    btnW := (guiW - 32 - btnGap * 2) // 3
    bx1 := 16
    bx2 := bx1 + btnW + btnGap
    bx3 := bx2 + btnW + btnGap
    btnH := 48

    ; 테스트 (blue — preview 5 seconds then revert)
    eg.Add("Text", "x" bx1 " y" aY " w" btnW " h" btnH " +0x1000 Background1a2a4a")
    eg.SetFont("s13 cAAAAFF Bold", "Segoe UI")
    eg.Add("Text", "x" bx1 " y" (aY + 12) " w" btnW " h24 Center BackgroundTrans", "🔊 테스트")
    tst := eg.Add("Text", "x" bx1 " y" aY " w" btnW " h" btnH " +0x1000 BackgroundTrans")
    tst.OnEvent("Click", DoTest)

    ; 적용 (green — save & activate)
    eg.Add("Text", "x" bx2 " y" aY " w" btnW " h" btnH " +0x1000 Background2a4a1a")
    eg.SetFont("s13 cAAFFAA Bold", "Segoe UI")
    eg.Add("Text", "x" bx2 " y" (aY + 12) " w" btnW " h24 Center BackgroundTrans", "✅ 적용")
    abc := eg.Add("Text", "x" bx2 " y" aY " w" btnW " h" btnH " +0x1000 BackgroundTrans")
    abc.OnEvent("Click", DoApply)

    ; 닫기 (dark red — close window)
    eg.Add("Text", "x" bx3 " y" aY " w" btnW " h" btnH " +0x1000 Background3a1a1a")
    eg.SetFont("s13 cFF8888 Bold", "Segoe UI")
    eg.Add("Text", "x" bx3 " y" (aY + 12) " w" btnW " h24 Center BackgroundTrans", "✕ 닫기")
    cls := eg.Add("Text", "x" bx3 " y" aY " w" btnW " h" btnH " +0x1000 BackgroundTrans")
    cls.OnEvent("Click", CloseEQ)

    ; ═══ FOOTER ═══
    fY := aY + btnH + 8
    eg.SetFont("s7 c4a5a3a", "Segoe UI")
    eg.Add("Text", "x16 y" fY " w" (guiW - 32) " Center BackgroundTrans", "TACTICAL AUDIO  //  PUBG EDITION")

    totalH := fY + 20
    gEqGui := eg
    eg.Show("w" guiW " h" totalH " NoActivate")

    DoFPS(*)      => FillEQ(eg, [-2,4,7,8,6,4,1,-1,-2,0,4,5,2,-1,-3], -8)
    DoBass(*)     => FillEQ(eg, [3,7,9,10,7,4,0,-2,-3,-2,0,1,0,-1,-2], -10)
    DoBalanced(*) => FillEQ(eg, [0,2,4,5,4,3,1,0,0,1,3,3,1,0,-1], -5)
    DoFlat(*)     => FillEQ(eg, [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0], 0)

    DoTest(*) {
        global gTestBackup
        fp := "C:\Program Files\EqualizerAPO\config\footstep-boost.txt"
        mc := "C:\Program Files\EqualizerAPO\config\config.txt"
        testWav := "Q:\Claudework\bridge base\scripts\test-sweep.wav"

        ; Save current config for revert
        try gTestBackup := FileRead(fp)
        catch
            gTestBackup := ""

        ; Read slider values and apply temporarily
        pr := eg["Preamp"].Value
        gains := []
        loop 15 {
            v := eg["EQ" A_Index].Value
            gains.Push(v)
            eg["VL" A_Index].Value := String(v)
        }
        eg["PL"].Value := String(pr) " dB"

        txt := BuildEQText(fNums, gains, pr)
        WriteConfig(fp, txt)
        WriteConfig(mc, "Include: footstep-boost.txt")

        ; Wait for APO to reload config
        Sleep(400)

        ; Play test sweep tone (40Hz~12kHz) so user hears the EQ effect
        try SoundPlay(testWav)

        ShowOverlay("🔊", "TESTING", "스윕 재생 중... 4초 후 복원", "0x4488FF")

        ; Auto-revert after 5 seconds (tone is 4s + 1s buffer)
        SetTimer(RevertTest, -5000)
    }

    DoApply(*) {
        global gTestBackup, gFootstepOn
        fp := "C:\Program Files\EqualizerAPO\config\footstep-boost.txt"
        mc := "C:\Program Files\EqualizerAPO\config\config.txt"

        ; Cancel any pending test revert
        SetTimer(RevertTest, 0)
        gTestBackup := ""

        pr := eg["Preamp"].Value
        gains := []
        loop 15 {
            v := eg["EQ" A_Index].Value
            gains.Push(v)
            eg["VL" A_Index].Value := String(v)
        }
        eg["PL"].Value := String(pr) " dB"

        txt := BuildEQText(fNums, gains, pr)
        WriteConfig(fp, txt)
        WriteConfig(mc, "Include: footstep-boost.txt")

        gFootstepOn := true
        ShowTray()
        ShowOverlay("✅", "APPLIED", "EQ Saved", "0x66CC66")
    }

    CloseEQ(*) {
        global gEqGui, gTestBackup
        ; Cancel pending test revert
        SetTimer(RevertTest, 0)
        ; If there was a test in progress, revert
        if gTestBackup != "" {
            fp := "C:\Program Files\EqualizerAPO\config\footstep-boost.txt"
            WriteConfig(fp, gTestBackup)
            gTestBackup := ""
        }
        if gEqGui {
            gEqGui.Destroy()
            gEqGui := ""
        }
    }
}

RevertTest() {
    global gTestBackup
    if gTestBackup != "" {
        fp := "C:\Program Files\EqualizerAPO\config\footstep-boost.txt"
        WriteConfig(fp, gTestBackup)
        gTestBackup := ""
        ShowOverlay("↩️", "REVERTED", "테스트 종료", "0xFFAA44")
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
                            if sp.Length >= 2 {
                                numStr := RegExReplace(sp[2], "\.0$", "")
                                vals.Push(Integer(numStr))
                            }
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
    global gTrayIndicator, gTrayVisible
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
    gTrayVisible := true
    SetTimer(ChkDesk, 1000)
}

HideTray() {
    global gTrayIndicator, gTrayVisible
    if gTrayIndicator {
        gTrayIndicator.Destroy()
        gTrayIndicator := ""
    }
    gTrayVisible := false
    SetTimer(ChkDesk, 0)
}

ChkDesk() {
    global gTrayIndicator, gFootstepOn, gTrayVisible
    if !gFootstepOn or !gTrayIndicator
        return
    try {
        ac := WinGetClass("A")
        ae := ""
        try ae := WinGetProcessName("A")
        ok := (ac = "Progman" or ac = "WorkerW" or ac = "Shell_TrayWnd" or ac = "CabinetWClass" or ae = "explorer.exe")
        ; Use transparency instead of Show/Hide to never steal focus from fullscreen games
        if ok and !gTrayVisible {
            try WinSetTransparent(140, gTrayIndicator)
            gTrayVisible := true
        } else if !ok and gTrayVisible {
            try WinSetTransparent(0, gTrayIndicator)
            gTrayVisible := false
        }
    } catch {
        ; No active window (lock screen, desktop switch, etc.)
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
    gOverlay := Gui("+AlwaysOnTop -Caption +ToolWindow +E0x20 +E0x80000")
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
