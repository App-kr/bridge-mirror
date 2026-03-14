import ctypes, os

path = r'\\?\Q:\Claudework\bridge base\nul'
GENERIC_WRITE = 0x40000000
FILE_SHARE_DELETE = 0x4
OPEN_EXISTING = 3
FILE_FLAG_DELETE_ON_CLOSE = 0x4000000

h = ctypes.windll.kernel32.CreateFileW(
    path, GENERIC_WRITE, FILE_SHARE_DELETE,
    None, OPEN_EXISTING, FILE_FLAG_DELETE_ON_CLOSE, None
)
if h != ctypes.c_void_p(-1).value:
    ctypes.windll.kernel32.CloseHandle(h)
    print("nul 파일 삭제 성공 (DeleteOnClose)")
else:
    err = ctypes.windll.kernel32.GetLastError()
    print(f"삭제 실패 error={err} — 수동으로 삭제 필요 (탐색기에서 직접)")
