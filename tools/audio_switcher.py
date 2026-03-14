#!/usr/bin/env python3
"""
audio_switcher.py
USB 헤드폰 전원/연결 토글 자동 감지 → PC 스피커 ↔ 헤드폰 자동 전환

사용법:
  python audio_switcher.py          # 모니터링 시작
  python audio_switcher.py --detect # 현재 장치 목록 출력 (ID 확인용)
"""

import sys
import time
import ctypes
import comtypes
import comtypes.client
from ctypes import c_wchar_p, c_int, POINTER
from pycaw.pycaw import AudioUtilities, IMMDeviceEnumerator, EDataFlow
from comtypes import CLSCTX_ALL

# ─── 설정 ────────────────────────────────────────────────────────────────────
CLSID_MMDV         = comtypes.GUID('{BCDE0395-E52F-467C-8E3D-C4579291692E}')
CLSID_PolicyConfig = comtypes.GUID('{870af99c-171d-4f9e-af0d-e63df40c2bc9}')
DEVICE_STATE_ACTIVE = 0x00000001

# ★ PC 스피커 (내장 HDA) — --detect 로 확인한 실제 ID
PC_SPEAKER_ID    = '{0.0.0.00000000}.{72a4012c-1080-4d09-9986-f81535429a15}'
PC_SPEAKER_NAME  = 'High Definition Audio Device'

# ★ USB 헤드폰 이름 패턴 (부분 일치) — 헤드폰 장치를 이름으로도 인식
USB_HEADPHONE_KEYWORDS = ['Captain 780LITE', 'Headset', 'Headphone', 'USB Audio']

POLL_INTERVAL = 1.0  # 초 (반응성 향상)


# ─── PolicyConfig COM ────────────────────────────────────────────────────────
class IPolicyConfig(comtypes.IUnknown):
    _iid_ = comtypes.GUID('{f8679f50-850a-41cf-9c72-430f290290c8}')
    _methods_ = [
        comtypes.COMMETHOD([], comtypes.HRESULT, 'GetMixFormat',
            (['in'], c_wchar_p), (['out'], POINTER(ctypes.c_void_p))),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'GetDeviceFormat',
            (['in'], c_wchar_p), (['in'], c_int), (['out'], POINTER(ctypes.c_void_p))),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'ResetDeviceFormat',
            (['in'], c_wchar_p)),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'SetDeviceFormat',
            (['in'], c_wchar_p), (['in'], ctypes.c_void_p), (['in'], ctypes.c_void_p)),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'GetProcessingPeriod',
            (['in'], c_wchar_p), (['in'], c_int),
            (['out'], POINTER(ctypes.c_int64)), (['out'], POINTER(ctypes.c_int64))),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'SetProcessingPeriod',
            (['in'], c_wchar_p), (['in'], POINTER(ctypes.c_int64))),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'GetShareMode',
            (['in'], c_wchar_p), (['out'], POINTER(c_int))),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'SetShareMode',
            (['in'], c_wchar_p), (['in'], POINTER(c_int))),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'GetPropertyValue',
            (['in'], c_wchar_p), (['in'], c_int),
            (['in'], ctypes.c_void_p), (['out'], ctypes.c_void_p)),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'SetPropertyValue',
            (['in'], c_wchar_p), (['in'], c_int),
            (['in'], ctypes.c_void_p), (['in'], ctypes.c_void_p)),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'SetDefaultEndpoint',
            (['in'], c_wchar_p, 'deviceId'),
            (['in'], c_int, 'role')),
        comtypes.COMMETHOD([], comtypes.HRESULT, 'SetEndpointVisibility',
            (['in'], c_wchar_p), (['in'], c_int)),
    ]


# ─── 핵심 함수 ───────────────────────────────────────────────────────────────
def set_default_device(device_id: str) -> bool:
    """지정 ID를 기본 재생 장치로 설정 (eConsole/eCommunications/eMultimedia 전부)."""
    try:
        policy = comtypes.client.CreateObject(CLSID_PolicyConfig, interface=IPolicyConfig)
        for role in [0, 1, 2]:
            policy.SetDefaultEndpoint(device_id, role)
        return True
    except Exception as e:
        log(f'[ERROR] set_default_device: {e}')
        return False


def get_active_playback_devices() -> dict:
    """현재 활성 재생 장치 {id: 이름} 반환."""
    try:
        enum = comtypes.client.CreateObject(CLSID_MMDV, interface=IMMDeviceEnumerator, clsctx=CLSCTX_ALL)
        coll = enum.EnumAudioEndpoints(EDataFlow.eRender.value, DEVICE_STATE_ACTIVE)
        all_devs = AudioUtilities.GetAllDevices()
        name_map = {d.id: d.FriendlyName for d in all_devs if d.id}
        result = {}
        for i in range(coll.GetCount()):
            did = coll.Item(i).GetId()
            result[did] = name_map.get(did, '(이름 불명)')
        return result
    except Exception as e:
        log(f'[ERROR] get_active_playback_devices: {e}')
        return {}


def get_default_device_id() -> str | None:
    """현재 기본 재생 장치 ID 반환."""
    try:
        enum = comtypes.client.CreateObject(CLSID_MMDV, interface=IMMDeviceEnumerator, clsctx=CLSCTX_ALL)
        dev = enum.GetDefaultAudioEndpoint(EDataFlow.eRender.value, 0)
        return dev.GetId() if dev else None
    except:
        return None


def is_headphone(device_id: str, device_name: str) -> bool:
    """USB 헤드폰 장치인지 판별 (ID 또는 이름 키워드 기준)."""
    for kw in USB_HEADPHONE_KEYWORDS:
        if kw.lower() in device_name.lower():
            return True
    return False


def find_best_headphone(devices: dict) -> str | None:
    """활성 장치 중 헤드폰 ID 반환 (우선순위: 키워드 일치)."""
    for did, name in devices.items():
        if is_headphone(did, name):
            return did
    return None


def log(msg: str):
    ts = time.strftime('%H:%M:%S')
    print(f'[{ts}] {msg}', flush=True)


# ─── 장치 탐색 모드 ──────────────────────────────────────────────────────────
def detect_mode():
    """현재 활성 장치 목록 + 기본 장치 출력."""
    devices = get_active_playback_devices()
    default = get_default_device_id()

    log('=== 활성 재생 장치 ===')
    for did, name in sorted(devices.items()):
        markers = []
        if did == default:             markers.append('기본')
        if did == PC_SPEAKER_ID:       markers.append('PC스피커')
        if is_headphone(did, name):    markers.append('헤드폰')
        marker_str = f'  [{"/".join(markers)}]' if markers else ''
        log(f'  {name}{marker_str}')
        log(f'       {did}')

    log(f'\n기본 장치 ID : {default}')
    log(f'PC 스피커 ID : {PC_SPEAKER_ID}')
    pc_ok = PC_SPEAKER_ID in devices
    log(f'PC 스피커 상태: {"OK - 활성" if pc_ok else "NOT FOUND - 비활성 또는 ID 불일치"}')
    hp = find_best_headphone(devices)
    log(f'헤드폰 감지   : {devices.get(hp, "없음") if hp else "없음"}')


# ─── 메인 모니터링 루프 ──────────────────────────────────────────────────────
def main():
    log('[오디오 자동 전환] 시작')
    log(f'PC 스피커: {PC_SPEAKER_NAME} ({PC_SPEAKER_ID})')
    log(f'폴링 간격: {POLL_INTERVAL}초')
    log('헤드폰 키워드: ' + ', '.join(USB_HEADPHONE_KEYWORDS))
    log('─' * 60)

    # 시작 시 현재 상태 확인
    prev_devices = get_active_playback_devices()
    prev_ids = set(prev_devices.keys())

    # 시작 시 PC 스피커 활성 여부 확인
    if PC_SPEAKER_ID not in prev_ids:
        log('[경고] PC 스피커가 활성 목록에 없음. --detect 로 올바른 ID 확인 필요')
    else:
        log('[초기화] PC 스피커 확인됨')

    # 시작 시 헤드폰이 없으면 PC 스피커로 설정
    hp = find_best_headphone(prev_devices)
    if hp is None and PC_SPEAKER_ID in prev_ids:
        default_id = get_default_device_id()
        if default_id != PC_SPEAKER_ID:
            if set_default_device(PC_SPEAKER_ID):
                log(f'[초기화] 헤드폰 없음 → PC 스피커로 초기 설정')
    elif hp:
        log(f'[초기화] 헤드폰 감지: {prev_devices[hp]} → 헤드폰 유지')

    while True:
        time.sleep(POLL_INTERVAL)
        try:
            current_devices = get_active_playback_devices()
            current_ids = set(current_devices.keys())

            removed_ids = prev_ids - current_ids
            added_ids   = current_ids - prev_ids

            # ── 장치 제거 감지 (헤드폰 전원 끔 / 연결 해제) ──────────────
            if removed_ids:
                removed_names = [prev_devices.get(d, d) for d in removed_ids]
                log(f'[감지] 장치 제거: {", ".join(removed_names)}')

                # 제거된 것 중 헤드폰이 있으면 → PC 스피커로 전환
                hp_removed = [d for d in removed_ids if is_headphone(d, prev_devices.get(d, ''))]
                if hp_removed:
                    log(f'[헤드폰 OFF] {", ".join(prev_devices.get(d,"?") for d in hp_removed)}')
                    if PC_SPEAKER_ID in current_ids:
                        if set_default_device(PC_SPEAKER_ID):
                            log(f'[전환] ✅ PC 스피커로 자동 전환')
                        else:
                            log(f'[전환] ❌ PC 스피커 전환 실패')
                    else:
                        log(f'[전환] ⚠ PC 스피커 비활성 — 전환 불가')
                else:
                    # 헤드폰 아닌 장치 제거 시: 현재 기본이 PC스피커가 아니면 교정
                    default_id = get_default_device_id()
                    if default_id in removed_ids and PC_SPEAKER_ID in current_ids:
                        if set_default_device(PC_SPEAKER_ID):
                            log(f'[교정] 기본 장치 제거됨 → PC 스피커로 전환')

            # ── 장치 추가 감지 (헤드폰 전원 켬 / 연결) ───────────────────
            if added_ids:
                added_names = [current_devices.get(d, d) for d in added_ids]
                log(f'[감지] 장치 추가: {", ".join(added_names)}')

                # 추가된 것 중 헤드폰이 있으면 → 헤드폰으로 전환
                hp_added = [d for d in added_ids if is_headphone(d, current_devices.get(d, ''))]
                if hp_added:
                    target_id = hp_added[0]  # 첫 번째 헤드폰 우선
                    log(f'[헤드폰 ON] {current_devices.get(target_id, target_id)}')
                    if set_default_device(target_id):
                        log(f'[전환] ✅ 헤드폰으로 자동 전환')
                    else:
                        log(f'[전환] ❌ 헤드폰 전환 실패')

            prev_devices = current_devices
            prev_ids = current_ids

        except Exception as e:
            log(f'[ERROR] 루프 오류: {e}')
            time.sleep(3)


# ─── 중복 실행 방지 ──────────────────────────────────────────────────────────
def ensure_single_instance():
    mutex = ctypes.windll.kernel32.CreateMutexW(None, True, 'AudioAutoSwitcher_Mutex')
    if ctypes.windll.kernel32.GetLastError() == 183:
        log('[종료] 이미 실행 중. 중복 실행 차단.')
        sys.exit(0)
    return mutex


# ─── 진입점 ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    if '--detect' in sys.argv:
        detect_mode()
    else:
        _mutex = ensure_single_instance()
        main()
