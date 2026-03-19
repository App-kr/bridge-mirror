Add-Type @"
using System;
using System.Runtime.InteropServices;

public class TokenPrivileges {
    [DllImport("advapi32.dll", SetLastError = true)]
    public static extern bool LookupPrivilegeValue(string host, string name, ref long luid);

    [DllImport("advapi32.dll", SetLastError = true)]
    public static extern bool AdjustTokenPrivileges(IntPtr token, bool disableAll, ref TOKEN_PRIVILEGES newState, int bufLen, IntPtr prev, IntPtr ret);

    [DllImport("advapi32.dll", SetLastError = true)]
    public static extern bool OpenProcessToken(IntPtr process, int access, ref IntPtr token);

    [DllImport("kernel32.dll")]
    public static extern IntPtr GetCurrentProcess();

    [StructLayout(LayoutKind.Sequential)]
    public struct TOKEN_PRIVILEGES {
        public int PrivilegeCount;
        public long Luid;
        public int Attributes;
    }

    public static void EnablePrivilege(string privilege) {
        IntPtr token = IntPtr.Zero;
        OpenProcessToken(GetCurrentProcess(), 0x28, ref token);
        TOKEN_PRIVILEGES tp = new TOKEN_PRIVILEGES();
        tp.PrivilegeCount = 1;
        LookupPrivilegeValue(null, privilege, ref tp.Luid);
        tp.Attributes = 2; // SE_PRIVILEGE_ENABLED
        AdjustTokenPrivileges(token, false, ref tp, 0, IntPtr.Zero, IntPtr.Zero);
    }
}
"@

# TakeOwnership 권한 활성화
[TokenPrivileges]::EnablePrivilege("SeTakeOwnershipPrivilege")
[TokenPrivileges]::EnablePrivilege("SeRestorePrivilege")
[TokenPrivileges]::EnablePrivilege("SeBackupPrivilege")

$keyPath = "SOFTWARE\Adobe\Adobe ARM\Legacy"
$hklm = [Microsoft.Win32.Registry]::LocalMachine

try {
    $key = $hklm.OpenSubKey($keyPath, [Microsoft.Win32.RegistryKeyPermissionCheck]::ReadWriteSubTree, [System.Security.AccessControl.RegistryRights]::TakeOwnership)
    if ($key) {
        $acl = $key.GetAccessControl([System.Security.AccessControl.AccessControlSections.None])
        $me = [System.Security.Principal.NTAccount]$env:USERNAME
        $acl.SetOwner($me)
        $key.SetAccessControl($acl)
        Write-Host "Owner set to $env:USERNAME"
        $key.Close()
    }
} catch {
    Write-Host "Owner step failed: $_"
}

# 권한 부여
try {
    $key2 = $hklm.OpenSubKey($keyPath, [Microsoft.Win32.RegistryKeyPermissionCheck]::ReadWriteSubTree, [System.Security.AccessControl.RegistryRights]::ChangePermissions)
    if ($key2) {
        $acl2 = $key2.GetAccessControl()
        $rule = New-Object System.Security.AccessControl.RegistryAccessRule(
            $env:USERNAME,
            "FullControl",
            "ContainerInherit,ObjectInherit",
            "None",
            "Allow"
        )
        $acl2.SetAccessRule($rule)
        $key2.SetAccessControl($acl2)
        Write-Host "FullControl granted"
        $key2.Close()
    }
} catch {
    Write-Host "Permission step failed: $_"
}

# 이제 키 생성 시도
$result = & reg add "HKLM\SOFTWARE\Adobe\Adobe ARM\Legacy\Acrobat\{AC76BA86-1033-FFFF-7760-0C0F074F4100}" /v "Check" /t REG_DWORD /d 0 /f 2>&1
Write-Host "reg add result: $result"
