# Audio Auto-Switcher Full Test
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$PC_SPEAKER_ID = '{0.0.0.00000000}.{73776834-c98c-45aa-b9e4-eecb239fd1e8}'

Write-Host "=== Audio Auto-Switcher Test ==="

# 1. Current default
$before = python -X utf8 -c "
import comtypes, comtypes.client
from pycaw.pycaw import IMMDeviceEnumerator, EDataFlow, AudioUtilities
from comtypes import CLSCTX_ALL
CLSID_MMDV = comtypes.GUID('{BCDE0395-E52F-467C-8E3D-C4579291692E}')
enum = comtypes.client.CreateObject(CLSID_MMDV, interface=IMMDeviceEnumerator, clsctx=CLSCTX_ALL)
dev = enum.GetDefaultAudioEndpoint(EDataFlow.eRender.value, 0)
did = dev.GetId()
all_devs = AudioUtilities.GetAllDevices()
name_map = {d.id: d.FriendlyName for d in all_devs if d.id}
print(name_map.get(did, did))
" 2>&1
Write-Host "[1] Current default: $before"

# 2. Start task
Write-Host "[2] Starting AudioAutoSwitcher task..."
Start-ScheduledTask -TaskName 'AudioAutoSwitcher' -ErrorAction SilentlyContinue
Start-Sleep 3

# 3. After switch
$after = python -X utf8 -c "
import comtypes, comtypes.client
from pycaw.pycaw import IMMDeviceEnumerator, EDataFlow, AudioUtilities
from comtypes import CLSCTX_ALL
CLSID_MMDV = comtypes.GUID('{BCDE0395-E52F-467C-8E3D-C4579291692E}')
enum = comtypes.client.CreateObject(CLSID_MMDV, interface=IMMDeviceEnumerator, clsctx=CLSCTX_ALL)
dev = enum.GetDefaultAudioEndpoint(EDataFlow.eRender.value, 0)
did = dev.GetId()
all_devs = AudioUtilities.GetAllDevices()
name_map = {d.id: d.FriendlyName for d in all_devs if d.id}
print(name_map.get(did, did))
" 2>&1
Write-Host "[3] After switch: $after"

# 4. Process check
$procs = Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like '*audio_switcher*' }
Write-Host "[4] Monitor process running: $($procs.Count)"

# 5. Result
if ($after -like '*High Definition Audio*') {
    Write-Host "[PASS] PC Speaker auto-switch OK"
} else {
    Write-Host "[FAIL] Not switched - current: $after"
}

Write-Host "[INFO] Task will auto-run on next login"
