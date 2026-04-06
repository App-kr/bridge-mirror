# audio_probe.ps1 — Captain 780LITE 오디오 엔드포인트 속성 전수 조사
# 헤드셋 OFF 상태에서 1회, ON 상태에서 1회 실행하여 차이 비교
param([string]$Tag = "unknown")

Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;

[ComImport, Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDE7 {
    int EnumAudioEndpoints(int dataFlow, int stateMask, out IMMDC7 devices);
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMD7 endpoint);
}
[ComImport, Guid("0BD7A1BE-7A1A-44DB-8397-CC5392387B5E"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDC7 { int GetCount(out int count); int Item(int index, out IMMD7 device); }
[ComImport, Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMD7 {
    int Activate(ref Guid iid, int clsCtx, IntPtr p, [MarshalAs(UnmanagedType.IUnknown)] out object iface);
    int OpenPropertyStore(int access, out IPS7 props);
    int GetId([MarshalAs(UnmanagedType.LPWStr)] out string id);
    int GetState(out int state);
}
[ComImport, Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IPS7 {
    int GetCount(out int count);
    int GetAt(int index, out PK7 key);
    int GetValue(ref PK7 key, out PV7 val);
}
[StructLayout(LayoutKind.Sequential)] public struct PK7 { public Guid fmtid; public int pid; }
[StructLayout(LayoutKind.Sequential)]
public struct PV7 {
    public ushort vt;
    public ushort r1; public ushort r2; public ushort r3;
    public IntPtr data1;
    public IntPtr data2;
}

// IAudioEndpointVolume
[ComImport, Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IAudioEndpointVolume {
    int RegisterControlChangeNotify(IntPtr p);
    int UnregisterControlChangeNotify(IntPtr p);
    int GetChannelCount(out uint count);
    int SetMasterVolumeLevel(float fLevelDB, ref Guid ctx);
    int SetMasterVolumeLevelScalar(float fLevel, ref Guid ctx);
    int GetMasterVolumeLevel(out float fLevelDB);
    int GetMasterVolumeLevelScalar(out float fLevel);
}

// IAudioMeterInformation
[ComImport, Guid("C02216F6-8C67-4B5B-9D00-D008E73E0064"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IAudioMeterInformation {
    int GetPeakValue(out float peak);
    int GetMeteringChannelCount(out uint count);
}

public static class AudioProbe {
    [DllImport("ole32.dll")]
    static extern int CoCreateInstance(ref Guid c, IntPtr o, int x, ref Guid i, [MarshalAs(UnmanagedType.IUnknown)] out object obj);

    static readonly Guid C1 = new Guid("BCDE0395-E52F-467C-8E3D-C4579291692E");
    static readonly Guid I1 = new Guid("A95664D2-9614-4F35-A746-DE8DB63617E6");
    static readonly Guid IID_IAudioEndpointVolume = new Guid("5CDF2C82-841E-4546-9722-0CF74078229A");
    static readonly Guid IID_IAudioMeterInformation = new Guid("C02216F6-8C67-4B5B-9D00-D008E73E0064");
    static PK7 PKN = new PK7 { fmtid = new Guid("A45C254E-DF1C-4EFD-8020-67D146A850E0"), pid = 14 };

    public static string ProbeDevice(string keyword) {
        object o; Guid c = C1, i = I1;
        CoCreateInstance(ref c, IntPtr.Zero, 1, ref i, out o);
        var en = (IMMDE7)o; IMMDC7 col;
        // stateMask=15: all states
        en.EnumAudioEndpoints(0, 15, out col);
        int cnt; col.GetCount(out cnt);
        var result = new List<string>();

        for (int j = 0; j < cnt; j++) {
            IMMD7 d; col.Item(j, out d);
            IPS7 ps; d.OpenPropertyStore(0, out ps);
            PV7 val; ps.GetValue(ref PKN, out val);
            string nm = Marshal.PtrToStringUni(val.data1) ?? "";
            if (!nm.Contains(keyword)) continue;

            string id; d.GetId(out id);
            int state; d.GetState(out state);
            result.Add("DEVICE: " + nm);
            result.Add("ID: " + id);
            result.Add("STATE: " + state + " (1=ACTIVE,2=DISABLED,4=NOTPRESENT,8=UNPLUGGED)");

            // Dump all properties
            int propCount; ps.GetCount(out propCount);
            result.Add("PROPERTY_COUNT: " + propCount);
            for (int p = 0; p < propCount; p++) {
                PK7 key; ps.GetAt(p, out key);
                PV7 pval; ps.GetValue(ref key, out pval);
                string valStr = "vt=" + pval.vt;
                // VT_LPWSTR=31, VT_UI4=19, VT_BOOL=11, VT_BLOB=65
                if (pval.vt == 31 && pval.data1 != IntPtr.Zero)
                    valStr += " str=" + Marshal.PtrToStringUni(pval.data1);
                else if (pval.vt == 19)
                    valStr += " uint=" + pval.data1.ToInt64();
                else if (pval.vt == 11)
                    valStr += " bool=" + (pval.data1.ToInt64() != 0);
                else
                    valStr += " raw=" + pval.data1.ToInt64() + "/" + pval.data2.ToInt64();
                result.Add(string.Format("  [{0}] {1}:{2} = {3}", p, key.fmtid, key.pid, valStr));
            }

            // Try IAudioEndpointVolume
            try {
                Guid volIid = IID_IAudioEndpointVolume;
                object volObj;
                int hr = d.Activate(ref volIid, 1, IntPtr.Zero, out volObj);
                result.Add("VOLUME_ACTIVATE_HR: 0x" + hr.ToString("X8"));
                if (hr == 0 && volObj != null) {
                    var vol = (IAudioEndpointVolume)volObj;
                    float levelDB, levelScalar;
                    uint chCount;
                    vol.GetMasterVolumeLevel(out levelDB);
                    vol.GetMasterVolumeLevelScalar(out levelScalar);
                    vol.GetChannelCount(out chCount);
                    result.Add("VOLUME_DB: " + levelDB);
                    result.Add("VOLUME_SCALAR: " + levelScalar);
                    result.Add("CHANNEL_COUNT: " + chCount);
                }
            } catch (Exception ex) {
                result.Add("VOLUME_ERROR: " + ex.Message);
            }

            // Try IAudioMeterInformation
            try {
                Guid meterIid = IID_IAudioMeterInformation;
                object meterObj;
                int hr = d.Activate(ref meterIid, 1, IntPtr.Zero, out meterObj);
                result.Add("METER_ACTIVATE_HR: 0x" + hr.ToString("X8"));
                if (hr == 0 && meterObj != null) {
                    var meter = (IAudioMeterInformation)meterObj;
                    float peak; uint mchCount;
                    meter.GetPeakValue(out peak);
                    meter.GetMeteringChannelCount(out mchCount);
                    result.Add("METER_PEAK: " + peak);
                    result.Add("METER_CHANNELS: " + mchCount);
                }
            } catch (Exception ex) {
                result.Add("METER_ERROR: " + ex.Message);
            }
        }
        return string.Join("\n", result);
    }
}
'@ -ErrorAction Stop

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$outFile = "Q:\Claudework\bridge base\tools\audio_probe_$Tag.txt"
$result = [AudioProbe]::ProbeDevice("Captain 780")
$result | Out-File -FilePath $outFile -Encoding UTF8
Write-Host "Saved to: $outFile"
Write-Host ""
Write-Host $result
