#Requires AutoHotkey v2.0
#SingleInstance Force
Persistent

global gOverlay := ""

; ===== Audio Toggle: Ctrl+Shift+F9 =====
^+F9:: {
    result := RunWaitOne('powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File "Q:\Claudework\bridge base\scripts\audio-toggle.ps1"')
    result := Trim(result)

    if InStr(result, "HEADSET")
        ShowOverlay("🎧", "Headset ON", "Captain 780LITE", "0x6C5CE7")
    else
        ShowOverlay("🔊", "Speaker ON", "Stand Mic + Speaker", "0xFFA502")
}

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

    ; Big emoji
    gOverlay.SetFont("s80 c0xFFFFFF", "Segoe UI Emoji")
    gOverlay.Add("Text", "x0 y8 w" guiW " Center", emoji)

    ; Title
    gOverlay.SetFont("s20 c" accentColor " Bold", "Segoe UI")
    gOverlay.Add("Text", "x0 y110 w" guiW " Center", title)

    ; Subtitle
    gOverlay.SetFont("s11 c0xAAAAAA", "Segoe UI")
    gOverlay.Add("Text", "x0 y145 w" guiW " Center", subtitle)

    ; Decorative line
    gOverlay.SetFont("s2 c" accentColor, "Segoe UI")
    gOverlay.Add("Text", "x70 y175 w200 Center", "━━━━━━━━━━━━━━━━━━━━")

    screenW := A_ScreenWidth
    screenH := A_ScreenHeight
    posX := (screenW - guiW) // 2
    posY := (screenH - guiH) // 2

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
