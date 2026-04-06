# audio_switch.ps1 — 헤드셋/스피커 이벤트 기반 자동 전환기
# Q:\Claudework\bridge base\tools\audio_switch.ps1
# 사용법:
#   powershell -NoProfile -ExecutionPolicy Bypass -File audio_switch.ps1
#     → 이벤트 감시 모드 (장치 변경 감지 시에만 전환)
#   powershell -NoProfile -ExecutionPolicy Bypass -File audio_switch.ps1 -Once
#     → 1회 상태 확인 + 전환

param([switch]$Once)

# ── COM Interop: Windows Core Audio PolicyConfig ──
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

[ComImport, Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"),
 InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDeviceEnumerator {
    int EnumAudioEndpoints(int dataFlow, int stateMask, out IMMDeviceCollection devices);
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice endpoint);
}

[ComImport, Guid("0BD7A1BE-7A1A-44DB-8397-CC5392387B5E"),
 InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDeviceCollection {
    int GetCount(out int count);
    int Item(int index, out IMMDevice device);
}

[ComImport, Guid("D666063F-1587-4E43-81F1-B948E807363F"),
 InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDevice {
    int Activate(ref Guid iid, int clsCtx, IntPtr activationParams, [MarshalAs(UnmanagedType.IUnknown)] out object iface);
    int OpenPropertyStore(int access, out IPropertyStore props);
    int GetId([MarshalAs(UnmanagedType.LPWStr)] out string id);
    int GetState(out int state);
}

[ComImport, Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"),
 InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IPropertyStore {
    int GetCount(out int count);
    int GetAt(int index, out PROPERTYKEY key);
    int GetValue(ref PROPERTYKEY key, out PROPVARIANT val);
}

[StructLayout(LayoutKind.Sequential)]
public struct PROPERTYKEY {
    public Guid fmtid;
    public int pid;
}

[StructLayout(LayoutKind.Sequential)]
public struct PROPVARIANT {
    public ushort vt;
    public ushort r1; public ushort r2; public ushort r3;
    public IntPtr data1;
    public IntPtr data2;
}

[ComImport, Guid("F8679F50-850A-41CF-9C72-430F290290C8"),
 InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IPolicyConfig {
    int _0(); int _1(); int _2(); int _3(); int _4();
    int _5(); int _6(); int _7(); int _8(); int _9();
    int SetDefaultEndpoint([MarshalAs(UnmanagedType.LPWStr)] string deviceId, int role);
}

public static class AudioHelper {
    [DllImport("ole32.dll")]
    static extern int CoCreateInstance(ref Guid clsid, IntPtr outer, int ctx, ref Guid iid, [MarshalAs(UnmanagedType.IUnknown)] out object obj);

    static readonly Guid CLSID_MMDeviceEnumerator = new Guid("BCDE0395-E52F-467C-8E3D-C4579291692E");
    static readonly Guid IID_IMMDeviceEnumerator = new Guid("A95664D2-9614-4F35-A746-DE8DB63617E6");
    static readonly Guid CLSID_PolicyConfig = new Guid("870AF99C-171D-4F9E-AF0D-E63DF40C2BC9");
    static readonly Guid IID_IPolicyConfig = new Guid("F8679F50-850A-41CF-9C72-430F290290C8");

    static PROPERTYKEY PKEY_FriendlyName = new PROPERTYKEY {
        fmtid = new Guid("A45C254E-DF1C-4EFD-8020-67D146A850E0"),
        pid = 14
    };

    public static IMMDeviceEnumerator GetEnumerator() {
        object obj;
        Guid cls = CLSID_MMDeviceEnumerator;
        Guid iid = IID_IMMDeviceEnumerator;
        CoCreateInstance(ref cls, IntPtr.Zero, 1, ref iid, out obj);
        return (IMMDeviceEnumerator)obj;
    }

    public static IPolicyConfig GetPolicyConfig() {
        object obj;
        Guid cls = CLSID_PolicyConfig;
        Guid iid = IID_IPolicyConfig;
        CoCreateInstance(ref cls, IntPtr.Zero, 1, ref iid, out obj);
        return (IPolicyConfig)obj;
    }

    public static string GetFriendlyName(IMMDevice dev) {
        IPropertyStore ps;
        dev.OpenPropertyStore(0, out ps);
        PROPVARIANT val;
        ps.GetValue(ref PKEY_FriendlyName, out val);
        return Marshal.PtrToStringUni(val.data1) ?? "";
    }

    public static void ListDevices(int stateMask, out string[] ids, out string[] names, out int[] states) {
        var en = GetEnumerator();
        IMMDeviceCollection col;
        en.EnumAudioEndpoints(0, stateMask, out col);
        int cnt; col.GetCount(out cnt);
        ids = new string[cnt]; names = new string[cnt]; states = new int[cnt];
        for (int i = 0; i < cnt; i++) {
            IMMDevice d; col.Item(i, out d);
            d.GetId(out ids[i]);
            names[i] = GetFriendlyName(d);
            d.GetState(out states[i]);
        }
    }

    public static string GetDefaultId() {
        var en = GetEnumerator();
        IMMDevice d;
        en.GetDefaultAudioEndpoint(0, 0, out d);
        string id; d.GetId(out id);
        return id;
    }

    public static void SetDefault(string deviceId) {
        var pc = GetPolicyConfig();
        pc.SetDefaultEndpoint(deviceId, 0); // eConsole
        pc.SetDefaultEndpoint(deviceId, 1); // eMultimedia
        pc.SetDefaultEndpoint(deviceId, 2); // eCommunications
    }
}
'@ -ErrorAction Stop

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# ── 설정 ──
$HEADSET_KEYWORD = "Captain 780"
$SPEAKER_KEYWORD = "High Definition Audio Device"

function Get-Devices {
    $ids = $null; $names = $null; $sts = $null
    [AudioHelper]::ListDevices(15, [ref]$ids, [ref]$names, [ref]$sts)
    for ($i = 0; $i -lt $ids.Count; $i++) {
        [PSCustomObject]@{ Id = $ids[$i]; Name = $names[$i]; State = $sts[$i] }
    }
}

function Switch-Audio {
    $devices = Get-Devices
    $defaultId = [AudioHelper]::GetDefaultId()

    $headset = $devices | Where-Object { $_.Name -like "*$HEADSET_KEYWORD*" -and $_.Name -like "*스피커*" }
    $speaker = $devices | Where-Object { $_.Name -like "*$SPEAKER_KEYWORD*" -and $_.Name -like "*스피커*" }

    if (-not $headset) { return }
    if (-not $speaker) { return }

    $headsetActive = ($headset.State -eq 1)
    $currentIsHeadset = ($defaultId -eq $headset.Id)
    $ts = Get-Date -Format "HH:mm:ss"

    if ($headsetActive -and -not $currentIsHeadset) {
        [AudioHelper]::SetDefault($headset.Id)
        Write-Host "[$ts] >> HEADSET ON  (Captain 780LITE)"
    }
    elseif (-not $headsetActive -and $currentIsHeadset) {
        [AudioHelper]::SetDefault($speaker.Id)
        Write-Host "[$ts] >> SPEAKER ON  (Default Speaker)"
    }
}

function Show-Status {
    Write-Host "=== Audio Devices ==="
    $devices = Get-Devices
    $defaultId = [AudioHelper]::GetDefaultId()
    foreach ($d in $devices) {
        if ($d.Name -like "*스피커*") {
            $st = switch ($d.State) { 1 {"[ON] "} 8 {"[OFF]"} default {"[?=$($d.State)]"} }
            $def = if ($d.Id -eq $defaultId) { " << DEFAULT" } else { "" }
            Write-Host "  $st $($d.Name)$def"
        }
    }
    Write-Host ""
}

# ── 메인 ──
if ($Once) {
    Show-Status
    Switch-Audio
    exit
}

# ── 이벤트 감시 모드 ──
Show-Status
Write-Host "=== Event Monitor Started ==="
Write-Host "    Headset : $HEADSET_KEYWORD"
Write-Host "    Speaker : $SPEAKER_KEYWORD"
Write-Host "    Ctrl+C to stop"
Write-Host ""

# 초기 1회 전환
Switch-Audio

# WMI 이벤트 구독: 사운드 장치 상태 변경 감지
# __InstanceModificationEvent: 기존 장치 상태(ON/OFF) 변경
# __InstanceCreationEvent: 새 장치 연결
# __InstanceDeletionEvent: 장치 제거
$wmiNs = "root\cimv2"
$queryMod = "SELECT * FROM __InstanceModificationEvent WITHIN 2 WHERE TargetInstance ISA 'Win32_PnPEntity' AND TargetInstance.PNPClass = 'AudioEndpoint'"
$queryAdd = "SELECT * FROM __InstanceCreationEvent WITHIN 2 WHERE TargetInstance ISA 'Win32_PnPEntity' AND TargetInstance.PNPClass = 'AudioEndpoint'"
$queryDel = "SELECT * FROM __InstanceDeletionEvent WITHIN 2 WHERE TargetInstance ISA 'Win32_PnPEntity' AND TargetInstance.PNPClass = 'AudioEndpoint'"

# 이벤트 핸들러
$action = {
    # 이벤트 발생 후 1초 대기 (장치 상태 안정화)
    Start-Sleep -Seconds 1
    $ts = Get-Date -Format "HH:mm:ss"
    $dev = $Event.SourceEventArgs.NewEvent.TargetInstance
    $evType = $Event.SourceIdentifier
    Write-Host "[$ts] [EVENT] $evType - $($dev.Name)"

    # Switch-Audio 함수 인라인 실행 (스크립트 스코프 접근)
    try {
        $ids = $null; $names = $null; $sts = $null
        [AudioHelper]::ListDevices(15, [ref]$ids, [ref]$names, [ref]$sts)

        $headsetId = $null; $headsetState = -1
        $speakerId = $null
        for ($i = 0; $i -lt $ids.Count; $i++) {
            if ($names[$i] -like "*Captain 780*" -and $names[$i] -like "*스피커*") {
                $headsetId = $ids[$i]; $headsetState = $sts[$i]
            }
            if ($names[$i] -like "*High Definition Audio Device*" -and $names[$i] -like "*스피커*") {
                $speakerId = $ids[$i]
            }
        }

        if ($headsetId -and $speakerId) {
            $defaultId = [AudioHelper]::GetDefaultId()
            if ($headsetState -eq 1 -and $defaultId -ne $headsetId) {
                [AudioHelper]::SetDefault($headsetId)
                Write-Host "[$ts] >> HEADSET ON  (Captain 780LITE)"
            }
            elseif ($headsetState -ne 1 -and $defaultId -eq $headsetId) {
                [AudioHelper]::SetDefault($speakerId)
                Write-Host "[$ts] >> SPEAKER ON  (Default Speaker)"
            }
        }
    } catch {
        Write-Host "[$ts] [ERR] $_"
    }
}

# 3개 이벤트 구독 등록
Register-WmiEvent -Query $queryMod -SourceIdentifier "AudioMod" -Action $action | Out-Null
Register-WmiEvent -Query $queryAdd -SourceIdentifier "AudioAdd" -Action $action | Out-Null
Register-WmiEvent -Query $queryDel -SourceIdentifier "AudioDel" -Action $action | Out-Null

Write-Host "[OK] 3 WMI event subscriptions registered (Mod/Add/Del)"
Write-Host "[OK] Waiting for device changes..."
Write-Host ""

# 메인 스레드 대기 (이벤트 처리는 백그라운드 스레드)
try {
    while ($true) {
        Wait-Event -Timeout 3600 | Out-Null
        # 1시간마다 heartbeat
        $ts = Get-Date -Format "HH:mm:ss"
        Write-Host "[$ts] [HEARTBEAT] still listening..."
    }
}
finally {
    # 정리
    Unregister-Event -SourceIdentifier "AudioMod" -ErrorAction SilentlyContinue
    Unregister-Event -SourceIdentifier "AudioAdd" -ErrorAction SilentlyContinue
    Unregister-Event -SourceIdentifier "AudioDel" -ErrorAction SilentlyContinue
    Write-Host "[EXIT] Event subscriptions cleaned up."
}
