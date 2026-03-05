#Requires AutoHotkey v2.0
#SingleInstance Force

; Simple EQ editor test
^+F11:: {
    g := Gui("+AlwaysOnTop", "EQ Test")
    g.BackColor := "1a1a2e"
    g.SetFont("s12 c0xFFFFFF", "Segoe UI")
    g.Add("Text", "x20 y10 w300", "EQ Editor Test")
    g.Add("Slider", "x20 y50 w300 Range-12-12 ToolTip vS1", 5)
    btn := g.Add("Button", "x20 y100 w100 h30", "OK")
    btn.OnEvent("Click", (*) => g.Destroy())
    g.Show("w340 h150")
}
