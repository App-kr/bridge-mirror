# -*- coding: utf-8 -*-
"""
BRIDGE RPA Overlay — 완전 독립 프로세스
부모 프로세스와 무관하게 생존. overlay_state.json 폴링으로 진행 표시.
"""
import os
import sys
import json
import time
import tkinter as tk
from datetime import datetime as _dt
from tkinter import messagebox
from datetime import datetime
from pathlib import Path

if sys.executable.lower().endswith("python.exe") and "--no-relaunch" not in sys.argv:
    _pw = Path(sys.executable).with_name("pythonw.exe")
    if _pw.exists():
        import subprocess as _sp
        _rla_env = os.environ.copy()
        _rla_env['_RLA_EXE']  = str(_pw)
        _rla_env['_RLA_ARGS'] = " ".join(
            ['"' + os.path.abspath(__file__) + '"', "--no-relaunch"] + sys.argv[1:]
        )
        _rla_env['_RLA_DIR']  = str(Path(__file__).parent)
        _sp.Popen(
            ['powershell', '-NonInteractive', '-NoProfile', '-WindowStyle', 'Hidden',
             '-Command',
             '(New-Object -ComObject Shell.Application)'
             '.ShellExecute($env:_RLA_EXE,$env:_RLA_ARGS,$env:_RLA_DIR,"open",1)'],
            creationflags=_sp.CREATE_NO_WINDOW, env=_rla_env,
            stdin=_sp.DEVNULL, stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
        )
        os._exit(0)

BASE_DIR          = Path(__file__).parent
OVERLAY_STATE     = BASE_DIR / "overlay_state.json"
OVERLAY_STOP_FLAG = BASE_DIR / "overlay_stop.flag"

# ── 색상 ─────────────────────────────────────────────────────────────
C_BG     = "#2b2b2b"
C_HEADER = "#4a235a"
C_GREEN  = "#27ae60"
C_BROWN  = "#7d5a3c"
C_WHITE  = "#f0f0f0"
C_YELLOW = "#f1c40f"
C_RED    = "#c0392b"
C_DARK   = "#1e1e1e"


class OverlayApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BRIDGE Craigslist RPA")
        self.root.configure(bg=C_BG)
        self.root.geometry("540x460")
        self.root.resizable(False, False)

        self._is_done   = False
        self._auto_close_after = None   # after() id
        self._started_at = time.time()  # 오버레이 시작 시각

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(500, self._poll)
        self.root.mainloop()

    # ── UI 구성 ──────────────────────────────────────────────────────
    def _build_ui(self):
        # 헤더 (보라)
        hdr = tk.Frame(self.root, bg=C_HEADER)
        hdr.pack(fill="x")
        tk.Label(hdr, text="BRIDGE  Craigslist RPA",
                 bg=C_HEADER, fg=C_WHITE,
                 font=("Consolas", 15, "bold")).pack(pady=12)

        # 정보 패널 (갈색)
        self.info_frame = tk.Frame(self.root, bg=C_BROWN, pady=6)
        self.info_frame.pack(fill="x", padx=10, pady=(8, 0))

        self.lbl_account = self._info_row("Account", "—")
        self.lbl_started = self._info_row("Started", "—")
        self.lbl_progress = self._info_row("Progress", "0 / 0")
        self.lbl_current  = self._info_row("Current", "대기 중...")

        # 진행 바
        bar_frame = tk.Frame(self.root, bg=C_BG)
        bar_frame.pack(fill="x", padx=10, pady=(6, 0))
        self.canvas_bar = tk.Canvas(bar_frame, bg="#444", height=12,
                                    highlightthickness=0)
        self.canvas_bar.pack(fill="x")

        # 구분선
        tk.Frame(self.root, bg=C_GREEN, height=2).pack(fill="x", padx=10, pady=4)

        # 로그 창
        self.log_text = tk.Text(self.root, bg=C_DARK, fg=C_WHITE,
                                font=("Consolas", 9), height=10,
                                relief="flat", state="disabled",
                                wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=10)

        # 하단 버튼
        foot = tk.Frame(self.root, bg=C_BG)
        foot.pack(fill="x", padx=10, pady=6)
        self.btn_stop = tk.Button(foot, text="⛔  중단하기",
                                  bg=C_RED, fg=C_WHITE,
                                  font=("Consolas", 10, "bold"),
                                  relief="flat", cursor="hand2",
                                  command=self._request_stop)
        self.btn_stop.pack(side="left")
        self.lbl_status = tk.Label(foot, text="작업 중...",
                                   bg=C_BG, fg=C_YELLOW,
                                   font=("Consolas", 9))
        self.lbl_status.pack(side="right")

    def _info_row(self, label: str, value: str):
        row = tk.Frame(self.info_frame, bg=C_BROWN)
        row.pack(anchor="w", padx=10)
        tk.Label(row, text=f"{label:<10}: ",
                 bg=C_BROWN, fg=C_YELLOW,
                 font=("Consolas", 10, "bold")).pack(side="left")
        lbl = tk.Label(row, text=value, bg=C_BROWN, fg=C_WHITE,
                       font=("Consolas", 10))
        lbl.pack(side="left")
        return lbl

    # ── 폴링 ─────────────────────────────────────────────────────────
    def _poll(self):
        try:
            state = json.loads(OVERLAY_STATE.read_text(encoding="utf-8"))
            self._refresh(state)
        except Exception:
            pass
        self.root.after(1000, self._poll)

    def _refresh(self, state: dict):
        self.lbl_account.config(text=state.get("account", "—"))
        self.lbl_started.config(text=state.get("started", "—"))

        total   = state.get("total", 0)
        done    = state.get("done", 0)
        success = state.get("success", 0)
        self.lbl_progress.config(text=f"{done} / {total}  (성공 {success})")
        self.lbl_current.config(text=state.get("current", "")[:55])

        # 진행 바 갱신
        self.canvas_bar.update_idletasks()
        w = self.canvas_bar.winfo_width()
        self.canvas_bar.delete("bar")
        if total > 0:
            fill_w = int(w * done / total)
            self.canvas_bar.create_rectangle(0, 0, fill_w, 12,
                                             fill=C_GREEN, tags="bar")

        # 로그 갱신 (새 항목만)
        new_logs = state.get("logs", [])
        current_lines = int(self.log_text.index("end-1c").split(".")[0])
        if len(new_logs) > current_lines:
            self.log_text.configure(state="normal")
            for line in new_logs[current_lines:]:
                self.log_text.insert("end", line + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

        # 완료 처리
        # 오버레이 시작 후 최소 15초 또는 launched_at 이후 상태만 인정
        if state.get("status") == "done" and not self._is_done:
            uptime = time.time() - self._started_at
            # 방어 1: 시작 후 15초 미만이면 스테일 state 가능성 — 무시
            if uptime < 15:
                pass
            # 방어 2: launched_at 타임스탬프가 있으면 그 이후 updated만 인정
            elif state.get("launched_at"):
                try:
                    launched = _dt.fromisoformat(state["launched_at"])
                    updated  = _dt.fromisoformat(state.get("updated", "2000-01-01"))
                    if updated >= launched:
                        self._is_done = True
                        self.lbl_status.config(text=f"완료 — {success}/{total}건 성공", fg=C_GREEN)
                        self.btn_stop.config(state="disabled")
                        self._auto_close_after = self.root.after(5000, self.root.destroy)
                except Exception:
                    self._is_done = True
                    self.lbl_status.config(text=f"완료 — {success}/{total}건 성공", fg=C_GREEN)
                    self.btn_stop.config(state="disabled")
                    self._auto_close_after = self.root.after(5000, self.root.destroy)
            else:
                # launched_at 없으면 uptime >= 15 인 경우만 처리
                self._is_done = True
                self.lbl_status.config(text=f"완료 — {success}/{total}건 성공", fg=C_GREEN)
                self.btn_stop.config(state="disabled")
                self._auto_close_after = self.root.after(5000, self.root.destroy)

    # ── 액션 ─────────────────────────────────────────────────────────
    def _request_stop(self):
        if messagebox.askyesno("중단 확인", "진행 중인 게시를 중단할까요?"):
            OVERLAY_STOP_FLAG.write_text("STOP", encoding="utf-8")
            self.btn_stop.config(state="disabled", text="중단 요청됨")
            self.lbl_status.config(text="중단 요청 — 현재 건 완료 후 중단", fg=C_YELLOW)

    def _on_close(self):
        if self._is_done:
            # 완료 후 → 그냥 종료
            if self._auto_close_after:
                self.root.after_cancel(self._auto_close_after)
            self.root.destroy()
        else:
            # 작업 중 → 최소화
            self.root.iconify()


if __name__ == "__main__":
    OverlayApp()
