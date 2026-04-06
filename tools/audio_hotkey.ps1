# audio_hotkey.ps1 — Ctrl+Alt+H 글로벌 핫키로 헤드셋/스피커 토글
# 시스템 트레이에 상주하며 핫키 대기
# 사용법: powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File audio_hotkey.ps1

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using System.Drawing;
using System.Threading;

// ── Core Audio COM ──
[ComImport, Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDE6 {
    int EnumAudioEndpoints(int dataFlow, int stateMask, out IMMDC6 devices);
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMD6 endpoint);
}
[ComImport, Guid("0BD7A1BE-7A1A-44DB-8397-CC5392387B5E"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDC6 { int GetCount(out int count); int Item(int index, out IMMD6 device); }
[ComImport, Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMD6 {
    int Activate(ref Guid iid, int clsCtx, IntPtr p, [MarshalAs(UnmanagedType.IUnknown)] out object iface);
    int OpenPropertyStore(int access, out IPS6 props);
    int GetId([MarshalAs(UnmanagedType.LPWStr)] out string id);
    int GetState(out int state);
}
[ComImport, Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IPS6 { int GetCount(out int c); int GetAt(int i, out PK6 k); int GetValue(ref PK6 k, out PV6 v); }
[StructLayout(LayoutKind.Sequential)] public struct PK6 { public Guid fmtid; public int pid; }
[StructLayout(LayoutKind.Sequential)] public struct PV6 { public ushort vt; public ushort r1; public ushort r2; public ushort r3; public IntPtr d1; public IntPtr d2; }
[ComImport, Guid("F8679F50-850A-41CF-9C72-430F290290C8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IPC6 {
    int _0(); int _1(); int _2(); int _3(); int _4(); int _5(); int _6(); int _7(); int _8(); int _9();
    int SetDefaultEndpoint([MarshalAs(UnmanagedType.LPWStr)] string deviceId, int role);
}

public static class AudioToggle {
    [DllImport("ole32.dll")]
    static extern int CoCreateInstance(ref Guid c, IntPtr o, int x, ref Guid i, [MarshalAs(UnmanagedType.IUnknown)] out object obj);
    [DllImport("user32.dll")] public static extern bool RegisterHotKey(IntPtr hWnd, int id, uint mod, uint vk);
    [DllImport("user32.dll")] public static extern bool UnregisterHotKey(IntPtr hWnd, int id);

    static readonly Guid C1 = new Guid("BCDE0395-E52F-467C-8E3D-C4579291692E");
    static readonly Guid I1 = new Guid("A95664D2-9614-4F35-A746-DE8DB63617E6");
    static readonly Guid C2 = new Guid("870AF99C-171D-4F9E-AF0D-E63DF40C2BC9");
    static readonly Guid I2 = new Guid("F8679F50-850A-41CF-9C72-430F290290C8");
    static PK6 PKN = new PK6 { fmtid = new Guid("A45C254E-DF1C-4EFD-8020-67D146A850E0"), pid = 14 };

    struct DevInfo { public string Id; public string Name; }

    static DevInfo FindDevice(string keyword) {
        object o; Guid c = C1, i = I1;
        CoCreateInstance(ref c, IntPtr.Zero, 1, ref i, out o);
        var en = (IMMDE6)o; IMMDC6 col; en.EnumAudioEndpoints(0, 1, out col);
        int cnt; col.GetCount(out cnt);
        for (int j = 0; j < cnt; j++) {
            IMMD6 d; col.Item(j, out d); IPS6 ps; d.OpenPropertyStore(0, out ps);
            PV6 val; ps.GetValue(ref PKN, out val);
            string nm = Marshal.PtrToStringUni(val.d1) ?? "";
            if (nm.Contains(keyword)) { string id; d.GetId(out id); return new DevInfo { Id = id, Name = nm }; }
        }
        return new DevInfo { Id = null, Name = null };
    }

    static string GetDefaultId() {
        object o; Guid c = C1, i = I1;
        CoCreateInstance(ref c, IntPtr.Zero, 1, ref i, out o);
        var en = (IMMDE6)o; IMMD6 d; en.GetDefaultAudioEndpoint(0, 0, out d);
        string id; d.GetId(out id); return id;
    }

    static void SetDefault(string deviceId) {
        object o; Guid c = C2, i = I2;
        CoCreateInstance(ref c, IntPtr.Zero, 1, ref i, out o);
        var pc = (IPC6)o;
        pc.SetDefaultEndpoint(deviceId, 0);
        pc.SetDefaultEndpoint(deviceId, 1);
        pc.SetDefaultEndpoint(deviceId, 2);
    }

    public static string Toggle(string headsetKw, string speakerKw) {
        var headset = FindDevice(headsetKw);
        var speaker = FindDevice(speakerKw);
        if (headset.Id == null || speaker.Id == null) return "Device not found";

        string cur = GetDefaultId();
        if (cur == headset.Id) {
            SetDefault(speaker.Id);
            return "SPEAKER: " + speaker.Name;
        } else {
            SetDefault(headset.Id);
            return "HEADSET: " + headset.Name;
        }
    }

    public static string GetCurrent(string headsetKw) {
        var headset = FindDevice(headsetKw);
        string cur = GetDefaultId();
        return (headset.Id != null && cur == headset.Id) ? "HEADSET" : "SPEAKER";
    }
}
'@ -ReferencedAssemblies System.Windows.Forms, System.Drawing -ErrorAction Stop

# ── 트레이 아이콘 + 핫키 ──
$HEADSET = "Captain 780"
$SPEAKER = "High Definition Audio Device"

# 초기 상태 확인
$initState = [AudioToggle]::GetCurrent($HEADSET)

# 트레이 아이콘 생성
$appContext = New-Object System.Windows.Forms.ApplicationContext
$trayIcon = New-Object System.Windows.Forms.NotifyIcon
$trayIcon.Visible = $true
$trayIcon.Text = "Audio Toggle (Ctrl+Alt+H) - $initState"

# 아이콘: 스피커 모양 (시스템 아이콘 사용)
$iconPath = [System.Environment]::GetFolderPath("System") + "\SndVol.exe"
if (Test-Path $iconPath) {
    $trayIcon.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon($iconPath)
} else {
    $trayIcon.Icon = [System.Drawing.SystemIcons]::Information
}

# 컨텍스트 메뉴
$menu = New-Object System.Windows.Forms.ContextMenuStrip
$toggleItem = $menu.Items.Add("Toggle (Ctrl+Shift+F9)")
$toggleItem.Add_Click({
    $result = [AudioToggle]::Toggle($HEADSET, $SPEAKER)
    $trayIcon.Text = "Audio: $result"
    $trayIcon.ShowBalloonTip(2000, "Audio Switch", $result, [System.Windows.Forms.ToolTipIcon]::Info)
})
$exitItem = $menu.Items.Add("Exit")
$exitItem.Add_Click({
    $trayIcon.Visible = $false
    [System.Windows.Forms.Application]::Exit()
})
$trayIcon.ContextMenuStrip = $menu

# 트레이 아이콘 더블클릭 = 토글
$trayIcon.Add_DoubleClick({
    $result = [AudioToggle]::Toggle($HEADSET, $SPEAKER)
    $trayIcon.Text = "Audio: $result"
    $trayIcon.ShowBalloonTip(2000, "Audio Switch", $result, [System.Windows.Forms.ToolTipIcon]::Info)
})

# 핫키 등록: Ctrl+Shift+F9 (MOD_CONTROL=2, MOD_SHIFT=4, F9=0x78)
$hiddenForm = New-Object System.Windows.Forms.Form
$hiddenForm.WindowState = "Minimized"
$hiddenForm.ShowInTaskbar = $false
$hiddenForm.Opacity = 0
$hiddenForm.Show()
$hiddenForm.Hide()

$HOTKEY_ID = 9001
[AudioToggle]::RegisterHotKey($hiddenForm.Handle, $HOTKEY_ID, 6, 0x78) | Out-Null  # 6 = Ctrl+Shift, 0x78 = F9

# 메시지 루프에서 핫키 감지
$hiddenForm.Add_Disposed({
    [AudioToggle]::UnregisterHotKey($hiddenForm.Handle, $HOTKEY_ID) | Out-Null
})

# WM_HOTKEY = 0x0312
$messageFilter = {
    param($sender, $e)
    if ($e.Msg -eq 0x0312 -and $e.WParam.ToInt32() -eq $HOTKEY_ID) {
        $result = [AudioToggle]::Toggle($HEADSET, $SPEAKER)
        $trayIcon.Text = "Audio: $result"
        $trayIcon.ShowBalloonTip(2000, "Audio Switch", $result, [System.Windows.Forms.ToolTipIcon]::Info)
    }
}

# Timer로 핫키 메시지 폴링 (WndProc 오버라이드 대신)
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 100

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class HotKeyMsg {
    [DllImport("user32.dll")]
    public static extern bool PeekMessage(out MSG msg, IntPtr hWnd, uint min, uint max, uint remove);
    [StructLayout(LayoutKind.Sequential)]
    public struct MSG {
        public IntPtr hwnd; public uint message; public IntPtr wParam; public IntPtr lParam;
        public uint time; public int ptX; public int ptY;
    }
}
'@ -ErrorAction SilentlyContinue

$timer.Add_Tick({
    $msg = New-Object HotKeyMsg+MSG
    # PeekMessage for WM_HOTKEY (0x0312)
    while ([HotKeyMsg]::PeekMessage([ref]$msg, [IntPtr]::Zero, 0x0312, 0x0312, 1)) {
        if ($msg.wParam.ToInt32() -eq $HOTKEY_ID) {
            $result = [AudioToggle]::Toggle($HEADSET, $SPEAKER)
            $trayIcon.Text = "Audio: $result"
            $trayIcon.ShowBalloonTip(2000, "Audio Switch", $result, [System.Windows.Forms.ToolTipIcon]::Info)
        }
    }
})
$timer.Start()

$trayIcon.ShowBalloonTip(3000, "Audio Switch", "Ctrl+Shift+F9 to toggle | Current: $initState", [System.Windows.Forms.ToolTipIcon]::Info)

# 메인 루프
try {
    [System.Windows.Forms.Application]::Run($appContext)
}
finally {
    $timer.Stop()
    [AudioToggle]::UnregisterHotKey($hiddenForm.Handle, $HOTKEY_ID) | Out-Null
    $trayIcon.Visible = $false
    $trayIcon.Dispose()
}
