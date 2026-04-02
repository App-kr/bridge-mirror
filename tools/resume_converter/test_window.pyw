"""최소 창 테스트 - VBS에서 실행해서 창이 뜨는지 확인"""
import tkinter as tk
import os
from pathlib import Path

log = Path(__file__).parent / "logs" / "test_window.log"
log.parent.mkdir(exist_ok=True)

def w(msg):
    with open(log, "a", encoding="utf-8") as f:
        import datetime
        f.write(f"[{datetime.datetime.now():%H:%M:%S}] {msg}\n")

w("시작")

root = tk.Tk()
w("Tk() 완료")

root.title("TEST WINDOW")
root.geometry("400x200+100+100")  # 위치 명시 (좌상단에서 100,100)
root.configure(bg="red")  # 빨간 배경 — 눈에 잘 띔

tk.Label(root, text="TEST OK\n이 창이 보이면 성공",
         bg="red", fg="white", font=("Arial", 20, "bold")).pack(expand=True)

w("위젯 생성 완료")

root.lift()
root.focus_force()
root.attributes("-topmost", True)
root.update()

w("mainloop 진입")
root.mainloop()
w("mainloop 종료")
