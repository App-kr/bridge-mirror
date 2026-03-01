"""
ftp_download.py — Cafe24 FTP 덤프 파일 다운로더
실행: python ftp_download.py
"""
import ftplib
import getpass
from pathlib import Path

HOST     = "coreabridge3.cafe24.com"
PORT     = 21
USER     = "coreabridge3"
REMOTE   = "/coreabridge3-20260224.dump"
LOCAL    = Path("Q:/Claudework/bridge base/coreabridge3-20260224.dump")

def main():
    password = getpass.getpass(f"[{USER}@{HOST}] FTP 비밀번호: ")

    print(f"[접속중] {HOST}:{PORT} ...")
    try:
        ftp = ftplib.FTP()
        ftp.connect(HOST, PORT, timeout=30)
        ftp.login(USER, password)
        ftp.set_pasv(True)   # 수동(PASV) 모드
        print(f"[성공] 로그인 완료")

        # 루트 파일 목록 확인
        print("[파일목록]")
        ftp.retrlines("LIST")

        # 파일 크기 확인
        try:
            size = ftp.size(REMOTE)
            print(f"\n[다운로드] {REMOTE}  ({size:,} bytes)")
        except Exception:
            print(f"\n[다운로드] {REMOTE}")

        # 다운로드
        LOCAL.parent.mkdir(parents=True, exist_ok=True)
        downloaded = 0
        def progress(data):
            nonlocal downloaded
            downloaded += len(data)
            f.write(data)
            print(f"\r  {downloaded:,} bytes", end="", flush=True)

        with LOCAL.open("wb") as f:
            ftp.retrbinary(f"RETR {REMOTE}", f.write, blocksize=8192)

        print(f"\n[완료] 저장됨: {LOCAL}")
        ftp.quit()

    except ftplib.error_perm as e:
        print(f"[오류] 권한/로그인 실패: {e}")
    except Exception as e:
        print(f"[오류] {e}")

if __name__ == "__main__":
    main()
