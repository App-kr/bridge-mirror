"""
BRIDGE Control Center — 통합 관리 패널
========================================
이 파일 하나로 BRIDGE의 모든 유지보수 작업을 GUI로 실행.
코드를 작성하지 않고도 배포·백업·상태 확인·Git 작업 전부 가능.

실행:
  BRIDGE_Control.bat 더블클릭 (프로젝트 루트)
  또는: python tools/bridge_control.py
"""

import os
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from tkinter import font as tkfont
from tkinter import messagebox, scrolledtext, simpledialog, ttk
import tkinter as tk

# ── 경로 ───────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(r"Q:\Claudework\bridge base")
PYTHON_EXE = r"Q:\Phtyon 3\python.exe"
TOOLS_DIR  = BASE_DIR / "tools"
HEALTH_URL = "https://bridge-n7hk.onrender.com/health"

# ── 색상 ───────────────────────────────────────────────────────────────────────
BG      = "#0f172a"
BG2     = "#1e293b"
BG3     = "#334155"
ACCENT  = "#3b82f6"
GREEN   = "#22c55e"
RED     = "#ef4444"
YELLOW  = "#eab308"
PURPLE  = "#8b5cf6"
CYAN    = "#06b6d4"
ORANGE  = "#f59e0b"
TEXT    = "#f1f5f9"
DIM     = "#94a3b8"
FONT_UI = ("Segoe UI", 10)
FONT_H  = ("Segoe UI", 11, "bold")
FONT_M  = ("Consolas", 9)


class BridgeControl(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BRIDGE Control Center")
        self.geometry("820x660")
        self.configure(bg=BG)
        self.resizable(True, True)
        self._build_ui()
        self._update_clock()
        self._refresh_status()
        self.after(60_000, self._auto_refresh)

    # ── UI 빌드 ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        # 헤더
        hdr = tk.Frame(self, bg=BG2, pady=9)
        hdr.pack(fill="x")
        tk.Label(hdr, text="BRIDGE Control Center", bg=BG2, fg=ACCENT,
                 font=("Segoe UI", 15, "bold")).pack(side="left", padx=16)
        self._time_lbl = tk.Label(hdr, text="", bg=BG2, fg=DIM, font=("Consolas", 11))
        self._time_lbl.pack(side="right", padx=16)

        # 상태 패널
        sf = tk.LabelFrame(self, text="  시스템 상태  ", bg=BG, fg=DIM, font=FONT_UI,
                            padx=12, pady=8)
        sf.pack(fill="x", padx=12, pady=(8, 4))

        r1 = tk.Frame(sf, bg=BG)
        r1.pack(fill="x")

        tk.Label(r1, text="Render:", bg=BG, fg=DIM, font=FONT_UI).pack(side="left")
        self._render_lbl = tk.Label(r1, text="확인 중", bg=BG, fg=YELLOW, font=FONT_UI)
        self._render_lbl.pack(side="left", padx=(4, 24))

        tk.Label(r1, text="Git:", bg=BG, fg=DIM, font=FONT_UI).pack(side="left")
        self._git_lbl = tk.Label(r1, text="확인 중", bg=BG, fg=YELLOW, font=FONT_UI)
        self._git_lbl.pack(side="left", padx=(4, 24))

        tk.Label(r1, text="마지막 백업:", bg=BG, fg=DIM, font=FONT_UI).pack(side="left")
        self._backup_lbl = tk.Label(r1, text="-", bg=BG, fg=DIM, font=FONT_UI)
        self._backup_lbl.pack(side="left", padx=(4, 0))

        # 버튼 패널
        bf = tk.Frame(self, bg=BG)
        bf.pack(fill="x", padx=12, pady=6)

        sections = [
            ("배포 / 헬스", [
                ("Render 헬스 확인",  self._check_health,   ACCENT),
                ("Render 배포 실행",  self._render_deploy,  PURPLE),
            ]),
            ("백업 / 덤프", [
                ("로컬 DB 백업",      self._local_backup,   GREEN),
                ("Render DB 덤프",   self._render_db_dump, CYAN),
            ]),
            ("대시보드", [
                ("관리 대시보드",     self._open_admin,     ORANGE),
                ("에이전트 HQ",       self._open_hq,        ORANGE),
            ]),
            ("Git", [
                ("Git 상태 확인",     self._git_status,    BG3),
                ("커밋 & 푸시",       self._git_commit,    GREEN),
            ]),
        ]

        for i, (sec, btns) in enumerate(sections):
            lf = tk.LabelFrame(bf, text=f"  {sec}  ", bg=BG, fg=DIM, font=FONT_UI,
                               padx=8, pady=8)
            lf.grid(row=0, column=i, padx=4, pady=2, sticky="nsew")
            bf.columnconfigure(i, weight=1)
            for label, cmd, color in btns:
                tk.Button(lf, text=label, command=cmd,
                          bg=color, fg="white", font=FONT_UI,
                          relief="flat", padx=6, pady=6, cursor="hand2",
                          width=17).pack(fill="x", pady=2)

        # 하단 유틸 버튼
        uf = tk.Frame(self, bg=BG)
        uf.pack(fill="x", padx=12, pady=(0, 4))

        tk.Button(uf, text="[BX] 인증 키 관리  (RENDER_API_KEY / ADMIN_API_KEY 등)",
                  command=self._bx_manage, bg=BG2, fg=DIM, font=FONT_UI,
                  relief="flat", padx=8, pady=4).pack(side="left", fill="x", expand=True, padx=(0, 4))

        tk.Button(uf, text="[스케줄러] 자동화 작업 등록",
                  command=self._setup_scheduler, bg=BG2, fg=DIM, font=FONT_UI,
                  relief="flat", padx=8, pady=4).pack(side="left", fill="x", expand=True)

        # 로그 창
        lf2 = tk.LabelFrame(self, text="  실행 로그  ", bg=BG, fg=DIM, font=FONT_UI)
        lf2.pack(fill="both", expand=True, padx=12, pady=(2, 10))

        self._log = scrolledtext.ScrolledText(
            lf2, bg="#090f1c", fg=TEXT, font=FONT_M,
            wrap="word", state="disabled", height=13
        )
        self._log.pack(fill="both", expand=True, padx=4, pady=4)
        self._log.tag_config("cmd",  foreground=ACCENT)
        self._log.tag_config("ok",   foreground=GREEN)
        self._log.tag_config("err",  foreground=RED)
        self._log.tag_config("warn", foreground=YELLOW)

        self._log_write("BRIDGE Control Center 시작됨", "ok")
        self._log_write(f"프로젝트 경로: {BASE_DIR}", "")

    # ── 시계 ─────────────────────────────────────────────────────────────────
    def _update_clock(self):
        self._time_lbl.config(text=datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))
        self.after(1000, self._update_clock)

    # ── 자동 갱신 (1분마다) ──────────────────────────────────────────────────
    def _auto_refresh(self):
        self._refresh_status()
        self.after(60_000, self._auto_refresh)

    def _refresh_status(self):
        threading.Thread(target=self._poll_render,  daemon=True).start()
        threading.Thread(target=self._poll_git,     daemon=True).start()
        threading.Thread(target=self._poll_backup,  daemon=True).start()

    # ── 상태 폴링 ─────────────────────────────────────────────────────────────
    def _poll_render(self):
        import urllib.request
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=10):
                self.after(0, lambda: self._render_lbl.config(text="ONLINE", fg=GREEN))
        except Exception:
            self.after(0, lambda: self._render_lbl.config(text="OFFLINE / SLEEPING", fg=RED))

    def _poll_git(self):
        try:
            r = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, cwd=str(BASE_DIR), timeout=10
            )
            lines = [l for l in r.stdout.splitlines() if l.strip()]
            if not lines:
                self.after(0, lambda: self._git_lbl.config(text="clean", fg=GREEN))
            else:
                n = len(lines)
                self.after(0, lambda: self._git_lbl.config(text=f"변경 {n}개", fg=YELLOW))
        except Exception:
            self.after(0, lambda: self._git_lbl.config(text="오류", fg=RED))

    def _poll_backup(self):
        backup_dir = BASE_DIR / "backups"
        try:
            dirs = sorted(backup_dir.glob("*/"), key=lambda p: p.stat().st_mtime, reverse=True)
            if dirs:
                mt = datetime.fromtimestamp(dirs[0].stat().st_mtime)
                label = mt.strftime("%m/%d %H:%M")
                self.after(0, lambda: self._backup_lbl.config(text=label, fg=DIM))
        except Exception:
            pass

    # ── 로그 출력 ─────────────────────────────────────────────────────────────
    def _log_write(self, text: str, tag: str = ""):
        def _do():
            self._log.configure(state="normal")
            ts = datetime.now().strftime("%H:%M:%S")
            self._log.insert("end", f"[{ts}] {text}\n", tag)
            self._log.see("end")
            self._log.configure(state="disabled")
        self.after(0, _do)

    # ── 명령 실행 공통 (subprocess → 로그) ────────────────────────────────────
    def _run_cmd(self, cmd: list, cwd: str | None = None, env: dict | None = None):
        label = " ".join(str(c) for c in cmd[-3:])
        self._log_write(f"$ {label}", "cmd")
        try:
            _env = os.environ.copy()
            if env:
                _env.update(env)
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                cwd=cwd or str(BASE_DIR),
                env=_env,
            )
            for line in proc.stdout:
                line = line.rstrip()
                if not line:
                    continue
                low = line.lower()
                if any(w in low for w in ("error", "fail", "traceback", "오류")):
                    tag = "err"
                elif any(w in low for w in ("완료", "success", "live", "ok", "done")):
                    tag = "ok"
                else:
                    tag = ""
                self._log_write(line, tag)
            proc.wait()
            tag = "ok" if proc.returncode == 0 else "err"
            self._log_write(f"--- exit {proc.returncode}", tag)
        except Exception as e:
            self._log_write(f"실행 오류: {e}", "err")
        self._poll_git()

    # ── 버튼 핸들러 ──────────────────────────────────────────────────────────

    def _check_health(self):
        self._log_write("Render 헬스 확인 중...", "warn")
        cmd = [PYTHON_EXE, str(TOOLS_DIR / "render_deploy.py"), "--status"]
        threading.Thread(target=self._run_cmd, args=(cmd,), daemon=True).start()

    def _render_deploy(self):
        if not messagebox.askyesno(
            "Render 배포 확인",
            "Render API 서버(bridge-n7hk)를 재배포합니다.\n\n"
            "RENDER_API_KEY가 BX에 등록되어 있어야 합니다.\n계속할까요?",
            icon="warning"
        ):
            return
        self._log_write("Render 배포 시작 (약 3~5분 소요)...", "warn")
        cmd = [PYTHON_EXE, str(TOOLS_DIR / "render_deploy.py")]
        threading.Thread(target=self._run_cmd, args=(cmd,), daemon=True).start()

    def _local_backup(self):
        self._log_write("로컬 DB 백업 시작...", "warn")
        cmd = [PYTHON_EXE, str(TOOLS_DIR / "bridge_backup.py"),
               "backup", "수동백업", "--type", "manual"]
        threading.Thread(target=self._run_cmd, args=(cmd,), daemon=True).start()

    def _render_db_dump(self):
        self._log_write("Render DB SQL 덤프 시작...", "warn")
        cmd = [PYTHON_EXE, "-X", "utf8", str(TOOLS_DIR / "render_db_backup.py")]
        threading.Thread(target=self._run_cmd, args=(cmd,), daemon=True).start()

    def _open_admin(self):
        self._log_write("관리 대시보드 실행 중...", "warn")
        dash = TOOLS_DIR / "admin_dashboard.py"
        try:
            subprocess.Popen(
                ["streamlit", "run", str(dash),
                 "--server.port", "8501", "--server.headless", "true"],
                cwd=str(BASE_DIR),
            )
            import webbrowser
            self.after(2500, lambda: webbrowser.open("http://localhost:8501"))
            self._log_write("관리 대시보드 → http://localhost:8501", "ok")
        except FileNotFoundError:
            self._log_write("streamlit 명령을 찾을 수 없습니다. pip install streamlit 실행 필요", "err")

    def _open_hq(self):
        self._log_write("에이전트 HQ 실행 중...", "warn")
        hq = TOOLS_DIR / "agent_hq.py"
        try:
            subprocess.Popen(
                ["streamlit", "run", str(hq),
                 "--server.port", "8502", "--server.headless", "true"],
                cwd=str(BASE_DIR),
            )
            import webbrowser
            self.after(2500, lambda: webbrowser.open("http://localhost:8502"))
            self._log_write("에이전트 HQ → http://localhost:8502", "ok")
        except FileNotFoundError:
            self._log_write("streamlit 명령을 찾을 수 없습니다. pip install streamlit 실행 필요", "err")

    def _git_status(self):
        self._log_write("Git 상태 확인...", "warn")

        def _do():
            for subcmd in [["git", "status", "--short"], ["git", "log", "--oneline", "-5"]]:
                self._run_cmd(subcmd, cwd=str(BASE_DIR))

        threading.Thread(target=_do, daemon=True).start()

    def _git_commit(self):
        msg = simpledialog.askstring(
            "커밋 메시지",
            "커밋 메시지를 입력하세요:\n(예: fix: 버그 수정, feat: 기능 추가)",
            parent=self
        )
        if not msg or not msg.strip():
            return
        full_msg = (
            f"{msg.strip()}\n\n"
            "Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
        )
        if not messagebox.askyesno(
            "Git 커밋 & 푸시",
            f"커밋 메시지:\n  {msg.strip()}\n\n"
            "git add -A → commit → push origin HEAD:main\n계속할까요?"
        ):
            return

        def _do():
            self._run_cmd(["git", "add", "-A"], cwd=str(BASE_DIR))
            self._run_cmd(["git", "commit", "-m", full_msg], cwd=str(BASE_DIR))
            self._run_cmd(["git", "push", "origin", "HEAD:main"], cwd=str(BASE_DIR))

        threading.Thread(target=_do, daemon=True).start()

    def _bx_manage(self):
        """BX 키 관리 — 새 터미널에서 대화형으로 실행."""
        choices = [
            "ls       — 저장된 키 목록 확인",
            "verify   — 누락 키 확인",
            "set RENDER_API_KEY",
            "set ADMIN_API_KEY",
            "set BRIDGE_FIELD_KEY",
            "set TELEGRAM_BOT_TOKEN",
        ]
        sel = _pick_dialog(self, "BX 키 관리", "실행할 작업을 선택하세요:", choices)
        if sel is None:
            return
        arg = sel.split()[0]
        extra = sel.split()[1] if len(sel.split()) > 1 else ""
        bx_path = str(TOOLS_DIR / "bx.py")
        cmd_args = [arg] + ([extra] if extra else [])
        # 새 터미널 창에서 대화형 실행 (getpass 등 입력 필요)
        full_cmd = f'"{PYTHON_EXE}" "{bx_path}" {" ".join(cmd_args)}'
        subprocess.Popen(
            ["cmd", "/k", full_cmd],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        self._log_write(f"BX 터미널 실행: bx.py {' '.join(cmd_args)}", "warn")

    def _setup_scheduler(self):
        if not messagebox.askyesno(
            "Windows 작업 스케줄러",
            "자동화 작업을 Windows 작업 스케줄러에 등록합니다:\n\n"
            "  - BRIDGE-daily-backup:    매일 03:00 로컬 DB 백업\n"
            "  - BRIDGE-render-db-dump:  매주 월 04:00 Render DB 덤프\n\n"
            "관리자 권한이 필요할 수 있습니다. 계속할까요?"
        ):
            return
        cmd = [PYTHON_EXE, str(TOOLS_DIR / "setup_scheduler.py")]
        threading.Thread(target=self._run_cmd, args=(cmd,), daemon=True).start()


# ── 유틸: 선택 다이얼로그 ──────────────────────────────────────────────────────
def _pick_dialog(parent, title: str, prompt: str, options: list[str]) -> str | None:
    """단순 Listbox 선택 다이얼로그. 선택값 반환, 취소 시 None."""
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.configure(bg=BG)
    dlg.grab_set()
    dlg.resizable(False, False)

    tk.Label(dlg, text=prompt, bg=BG, fg=TEXT, font=FONT_UI,
             wraplength=360, justify="left").pack(padx=16, pady=(12, 4))

    lb = tk.Listbox(dlg, bg=BG2, fg=TEXT, selectbackground=ACCENT,
                    font=FONT_M, width=46, height=len(options),
                    relief="flat", bd=0)
    lb.pack(padx=16, pady=4)
    for opt in options:
        lb.insert("end", opt)
    lb.select_set(0)

    result = [None]

    def _ok():
        sel = lb.curselection()
        if sel:
            result[0] = options[sel[0]]
        dlg.destroy()

    def _cancel():
        dlg.destroy()

    btn_f = tk.Frame(dlg, bg=BG)
    btn_f.pack(pady=8)
    tk.Button(btn_f, text="확인", command=_ok,
              bg=ACCENT, fg="white", font=FONT_UI,
              relief="flat", padx=16, pady=4).pack(side="left", padx=4)
    tk.Button(btn_f, text="취소", command=_cancel,
              bg=BG3, fg=TEXT, font=FONT_UI,
              relief="flat", padx=16, pady=4).pack(side="left", padx=4)

    dlg.wait_window()
    return result[0]


if __name__ == "__main__":
    app = BridgeControl()
    app.mainloop()
