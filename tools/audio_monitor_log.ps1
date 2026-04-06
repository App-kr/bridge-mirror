# audio_monitor_log.ps1 — 기본 오디오 장치 변경 감시 + 로그
# 누가/뭐가 기본 장치를 바꾸는지 추적
# 사용법: powershell -NoProfile -ExecutionPolicy Bypass -File audio_monitor_log.ps1

$logFile = "Q:\Claudework\bridge base\tools\audio_change.log"

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

[ComImport, Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"),
 InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDeviceEnumerator3 {
    int EnumAudioEndpoints(int dataFlow, int stateMask, out IMMDeviceCollection3 devices);
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice3 endpoint);
}

[ComImport, Guid("0BD7A1BE-7A1A-44DB-8397-CC5392387B5E"),
 InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDeviceCollection3 {
    int GetCount(out int count);
    int Item(int index, out IMMDevice3 device);
}

[ComImport, Guid("D666063F-1587-4E43-81F1-B948E807363F"),
 InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDevice3 {
    int Activate(ref Guid iid, int clsCtx, IntPtr activationParams, [MarshalAs(UnmanagedType.IUnknown)] out object iface);
    int OpenPropertyStore(int access, out IPropertyStore3 props);
    int GetId([MarshalAs(UnmanagedType.LPWStr)] out string id);
    int GetState(out int state);
}

[ComImport, Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"),
 InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IPropertyStore3 {
    int GetCount(out int count);
    int GetAt(int index, out PROPERTYKEY3 key);
    int GetValue(ref PROPERTYKEY3 key, out PROPVARIANT3 val);
}

[StructLayout(LayoutKind.Sequential)]
public struct PROPERTYKEY3 {
    public Guid fmtid;
    public int pid;
}

[StructLayout(LayoutKind.Sequential)]
public struct PROPVARIANT3 {
    public ushort vt;
    public ushort r1; public ushort r2; public ushort r3;
    public IntPtr data1;
    public IntPtr data2;
}

public static class AudioMon {
    [DllImport("ole32.dll")]
    static extern int CoCreateInstance(ref Guid clsid, IntPtr outer, int ctx, ref Guid iid, [MarshalAs(UnmanagedType.IUnknown)] out object obj);

    static readonly Guid CLSID_MMDeviceEnumerator = new Guid("BCDE0395-E52F-467C-8E3D-C4579291692E");
    static readonly Guid IID_IMMDeviceEnumerator = new Guid("A95664D2-9614-4F35-A746-DE8DB63617E6");

    static PROPERTYKEY3 PKEY_FriendlyName = new PROPERTYKEY3 {
        fmtid = new Guid("A45C254E-DF1C-4EFD-8020-67D146A850E0"),
        pid = 14
    };

    public static string GetDefaultName() {
        object obj;
        Guid cls = CLSID_MMDeviceEnumerator;
        Guid iid = IID_IMMDeviceEnumerator;
        CoCreateInstance(ref cls, IntPtr.Zero, 1, ref iid, out obj);
        var en = (IMMDeviceEnumerator3)obj;
        IMMDevice3 d;
        en.GetDefaultAudioEndpoint(0, 0, out d);
        IPropertyStore3 ps;
        d.OpenPropertyStore(0, out ps);
        PROPVARIANT3 val;
        ps.GetValue(ref PKEY_FriendlyName, out val);
        string name = Marshal.PtrToStringUni(val.data1) ?? "?";
        string id; d.GetId(out id);
        return name + "|" + id;
    }
}
'@ -ErrorAction Stop

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$prev = ""
$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$msg = "[$ts] === Audio Monitor Log Started ==="
Write-Host $msg
Add-Content -Path $logFile -Value $msg -Encoding UTF8

# 초기 상태 기록
$cur = [AudioMon]::GetDefaultName()
$name, $id = $cur -split '\|', 2
$msg = "[$ts] CURRENT DEFAULT: $name"
Write-Host $msg
Add-Content -Path $logFile -Value $msg -Encoding UTF8
$prev = $cur

Write-Host "Monitoring... (Ctrl+C to stop, log: $logFile)"
Write-Host ""

# 2초마다 기본 장치 확인 - 변경 시에만 로그 기록
while ($true) {
    Start-Sleep -Seconds 2
    try {
        $cur = [AudioMon]::GetDefaultName()
        if ($cur -ne $prev) {
            $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            $name, $id = $cur -split '\|', 2
            $prevName = ($prev -split '\|', 2)[0]

            # 콜스택/프로세스 정보 수집
            $audioProcs = Get-Process | Where-Object {
                $_.ProcessName -match 'audio|sound|realtek|nahimic|sonic|voicemeeter|steelseries|corsair|hyperx|razer|logitech'
            } | ForEach-Object { "$($_.ProcessName)($($_.Id))" }
            $procInfo = if ($audioProcs) { $audioProcs -join ", " } else { "none detected" }

            $msg = "[$ts] CHANGED: $prevName -> $name | AudioProcs: $procInfo"
            Write-Host $msg
            Add-Content -Path $logFile -Value $msg -Encoding UTF8
            $prev = $cur
        }
    } catch {
        $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $msg = "[$ts] ERROR: $_"
        Write-Host $msg
        Add-Content -Path $logFile -Value $msg -Encoding UTF8
    }
}
