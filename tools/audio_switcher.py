#!/usr/bin/env python3
"""
audio_switcher.py
헤드셋 끊기면 PC 스피커로 자동 전환 + 시작시 PC 스피커 기본 설정

사용법:
  python audio_switcher.py          # 실행 (모니터링 시작)
  python audio_switcher.py --detect # 현재 장치 목록만 출력
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
CLSID_MMDV = comtypes.GUID('{BCDE0395-E52F-467C-8E3D-C4579291692E}')
CLSID_PolicyConfig = comtypes.GUID('{870af99c-171d-4f9e-af0d-e63df40c2bc9}')
DEVICE_STATE_ACTIVE = 0x00000001

PC_SPEAKER_ID   = '{0.0.0.00000000}.{73776834-c98c-45aa-b9e4-eecb239fd1e8}'
PC_SPEAKER_NAME = '스피커(High Definition Audio Device)'

POLL_INTERVAL = 1.5  # 초

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


def get_active_playback_ids() -> set:
    """현재 활성(연결+활성화) 재생 장치 ID 집합 반환."""
    try:
        enum = comtypes.client.CreateObject(CLSID_MMDV, interface=IMMDeviceEnumerator, clsctx=CLSCTX_ALL)
        coll = enum.EnumAudioEndpoints(EDataFlow.eRender.value, DEVICE_STATE_ACTIVE)
        return {coll.Item(i).GetId() for i in range(coll.GetCount())}
    except Exception as e:
        log(f'[ERROR] get_active_playback_ids: {e}')
        return set()


def get_default_device_id() -> str | None:
    """현재 기본 재생 장치 ID 반환."""
    try:
        enum = comtypes.client.CreateObject(CLSID_MMDV, interface=IMMDeviceEnumerator, clsctx=CLSCTX_ALL)
        dev = enum.GetDefaultAudioEndpoint(EDataFlow.eRender.value, 0)  # eRender, eConsole
        return dev.GetId() if dev else None
    except:
        return None


def log(msg: str):
    print(msg, flush=True)


# ─── 장치 탐색 모드 ──────────────────────────────────────────────────────────
def detect_mode():
    """현재 활성 장치 목록 + 기본 장치 출력."""
    ids = get_active_playback_ids()
    default = get_default_device_id()
    all_devs = AudioUtilities.GetAllDevices()
    name_map = {d.id: d.FriendlyName for d in all_devs if d.id}

    log('=== 활성 재생 장치 ===')
    for i, did in enumerate(sorted(ids)):
        name = name_map.get(did, '(이름 불명)')
        marker = ' [기본]' if did == default else ''
        marker += ' [PC스피커]' if did == PC_SPEAKER_ID else ''
        log(f'  [{i}] {name}{marker}')
        log(f'       {did}')

    log(f'\n기본 장치 ID: {default}')
    log(f'PC 스피커 ID: {PC_SPEAKER_ID}')
    pc_ok = PC_SPEAKER_ID in ids
    log(f'PC 스피커 활성 여부: {"OK" if pc_ok else "NOT FOUND"}')


# ─── 메인 모니터링 루프 ──────────────────────────────────────────────────────
def main():
    log('[오디오 자동 전환] 시작')
    log(f'대상: {PC_SPEAKER_NAME}')
    log(f'ID  : {PC_SPEAKER_ID}')
    log(f'폴링: {POLL_INTERVAL}초마다')

    # 시작 즉시 PC 스피커로 설정
    active = get_active_playback_ids()
    if PC_SPEAKER_ID not in active:
        log('[경고] PC 스피커가 활성 장치 목록에 없음! 설정 불가')
    else:
        if set_default_device(PC_SPEAKER_ID):
            log('[초기화] PC 스피커를 기본 장치로 설정 완료')
        else:
            log('[경고] 초기 PC 스피커 설정 실패')

    prev = get_active_playback_ids()

    while True:
        time.sleep(POLL_INTERVAL)
        try:
            current = get_active_playback_ids()
            removed = prev - current

            if removed:
                default_id = get_default_device_id()
                log(f'[감지] 장치 제거됨 ({len(removed)}개)')

                # 제거된 장치가 현재 기본 장치였거나, 이미 잘못된 상태면 전환
                if default_id in removed or default_id != PC_SPEAKER_ID:
                    if PC_SPEAKER_ID in current:
                        if set_default_device(PC_SPEAKER_ID):
                            log(f'[전환] PC 스피커로 자동 전환 완료')
                    else:
                        log('[경고] PC 스피커 비활성 — 전환 불가')

            prev = current

        except Exception as e:
            log(f'[ERROR] 루프 오류: {e}')
            time.sleep(3)


# ─── 중복 실행 방지 ──────────────────────────────────────────────────────────
def ensure_single_instance():
    """이미 실행 중이면 종료."""
    import ctypes
    mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "AudioAutoSwitcher_Mutex")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        log("[종료] 이미 실행 중. 중복 실행 차단.")
        sys.exit(0)
    return mutex  # GC 방지용 반환


# ─── 진입점 ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    if '--detect' in sys.argv:
        detect_mode()
    else:
        _mutex = ensure_single_instance()
        main()
