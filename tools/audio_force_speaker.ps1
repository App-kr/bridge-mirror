# audio_force_speaker.ps1 — 강제 스피커 기본 설정
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

[ComImport, Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDevE5 {
    int EnumAudioEndpoints(int dataFlow, int stateMask, out IMMDevC5 devices);
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDev5 endpoint);
}
[ComImport, Guid("0BD7A1BE-7A1A-44DB-8397-CC5392387B5E"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDevC5 { int GetCount(out int count); int Item(int index, out IMMDev5 device); }
[ComImport, Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDev5 {
    int Activate(ref Guid iid, int clsCtx, IntPtr p, [MarshalAs(UnmanagedType.IUnknown)] out object iface);
    int OpenPropertyStore(int access, out IPS5 props);
    int GetId([MarshalAs(UnmanagedType.LPWStr)] out string id);
    int GetState(out int state);
}
[ComImport, Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IPS5 { int GetCount(out int count); int GetAt(int index, out PK5 key); int GetValue(ref PK5 key, out PV5 val); }
[StructLayout(LayoutKind.Sequential)] public struct PK5 { public Guid fmtid; public int pid; }
[StructLayout(LayoutKind.Sequential)] public struct PV5 { public ushort vt; public ushort r1; public ushort r2; public ushort r3; public IntPtr d1; public IntPtr d2; }
[ComImport, Guid("F8679F50-850A-41CF-9C72-430F290290C8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IPC5 {
    int _0(); int _1(); int _2(); int _3(); int _4(); int _5(); int _6(); int _7(); int _8(); int _9();
    int SetDefaultEndpoint([MarshalAs(UnmanagedType.LPWStr)] string deviceId, int role);
}
public static class AF5 {
    [DllImport("ole32.dll")] static extern int CoCreateInstance(ref Guid c, IntPtr o, int x, ref Guid i, [MarshalAs(UnmanagedType.IUnknown)] out object obj);
    static readonly Guid C1=new Guid("BCDE0395-E52F-467C-8E3D-C4579291692E"), I1=new Guid("A95664D2-9614-4F35-A746-DE8DB63617E6");
    static readonly Guid C2=new Guid("870AF99C-171D-4F9E-AF0D-E63DF40C2BC9"), I2=new Guid("F8679F50-850A-41CF-9C72-430F290290C8");
    static PK5 PKN=new PK5{fmtid=new Guid("A45C254E-DF1C-4EFD-8020-67D146A850E0"),pid=14};
    public static string SetSpeaker(string keyword) {
        object o; Guid c=C1; Guid i=I1; CoCreateInstance(ref c,IntPtr.Zero,1,ref i,out o);
        var en=(IMMDevE5)o; IMMDevC5 col; en.EnumAudioEndpoints(0,1,out col);
        int cnt; col.GetCount(out cnt);
        for(int j=0;j<cnt;j++){
            IMMDev5 d; col.Item(j,out d); IPS5 ps; d.OpenPropertyStore(0,out ps);
            PV5 val; ps.GetValue(ref PKN,out val);
            string nm=Marshal.PtrToStringUni(val.d1)??"";
            if(nm.Contains(keyword)){
                string id; d.GetId(out id);
                Guid c2=C2; Guid i2=I2; CoCreateInstance(ref c2,IntPtr.Zero,1,ref i2,out o);
                var pc=(IPC5)o; pc.SetDefaultEndpoint(id,0); pc.SetDefaultEndpoint(id,1); pc.SetDefaultEndpoint(id,2);
                return nm;
            }
        }
        return null;
    }
}
'@ -ErrorAction Stop

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$result = [AF5]::SetSpeaker("High Definition Audio Device")
if ($result) { Write-Host "[OK] Default -> $result" } else { Write-Host "[FAIL] Speaker not found" }
