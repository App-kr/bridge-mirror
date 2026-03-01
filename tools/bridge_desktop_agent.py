"""
bridge_desktop_agent.py — BRIDGE Control Panel
================================================
Tkinter 기반 경량 관리자 GUI.

기능:
  - RPA 실행 (dry-run / generate / post) 원클릭
  - rpa_error.log / pipeline.log 실시간 모니터링
  - ad_posts 상태 (posted / draft / error) 실시간 집계
  - 보안 필터 상태 표시

실행:
  python bridge_desktop_agent.py
  또는 BRIDGE_Control_Panel.bat 더블클릭
"""

import sqlite3
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont
from tkinter import scrolledtext, ttk

# ── 경로 ──────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
DB_PATH    = BASE_DIR / "master.db"
LOG_RPA    = BASE_DIR / "logs" / "rpa_error.log"
LOG_PIPE   = BASE_DIR / "logs" / "pipeline.log"
PYTHON_EXE = sys.executable

# ── 색상 팔레트 ────────────────────────────────────────────────────────────────
BG        = "#0f172a"   # slate-900
BG2       = "#1e293b"   # slate-800
BG3       = "#334155"   # slate-700
ACCENT    = "#3b82f6"   # blue-500
GREEN     = "#22c55e"
RED       = "#ef4444"
YELLOW    = "#eab308"
TEXT      = "#f1f5f9"
TEXT_DIM  = "#94a3b8"
FONT_MONO = ("Consolas", 9)
FONT_UI   = ("Segoe UI", 10)
FONT_H    = ("Segoe UI", 11, "bold")

# ── 프로세스 관리 ──────────────────────────────────────────────────────────────
_rpa_proc: subprocess.Popen | None = None


def _run_rpa(args: list[str], log_widget: scrolledtext.ScrolledText):
    """RPA 스크립트를 서브프로세스로 실행하고 stdout → 로그 위젯에 실시간 출력."""
    global _rpa_proc
    cmd = [PYTHON_EXE, str(BASE_DIR / "craigslist_auto_rpa.py")] + args
    log_widget.insert(tk.END, f"\n$ {' '.join(cmd)}\n", "cmd")
    log_widget.see(tk.END)

    try:
        _rpa_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            cwd=str(BASE_DIR),
        )
        for line in _rpa_proc.stdout:
            log_widget.insert(tk.END, line)
            _tag_line(log_widget, line)
            log_widget.see(tk.END)
        _rpa_proc.wait()
        log_widget.insert(tk.END, f"[완료] exit code={_rpa_proc.returncode}\n", "done")
    except Exception as exc:
        log_widget.insert(tk.END, f"[ERROR] {exc}\n", "error")
    finally:
        _rpa_proc = None
    log_widget.see(tk.END)


def _tag_line(widget: scrolledtext.ScrolledText, line: str):
    """로그 라인에 색상 태그 적용."""
    last = widget.index("end-1c linestart")
    if any(k in line for k in ["✅", "완료", "OK", "SUCCESS", "posted"]):
        widget.tag_add("ok",    last, "end-1c")
    elif any(k in line for k in ["❌", "ERROR", "실패", "FAIL", "ABORT"]):
        widget.tag_add("error", last, "end-1c")
    elif any(k in line for k in ["⚠", "WARN", "REDACT", "보안"]):
        widget.tag_add("warn",  last, "end-1c")


# ── DB 조회 ───────────────────────────────────────────────────────────────────
def _get_stats() -> dict:
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur  = conn.cursor()
        cur.execute("SELECT status, COUNT(*) FROM ad_posts GROUP BY status")
        stats = {r[0]: r[1] for r in cur.fetchall()}
        stats.setdefault("posted", 0)
        stats.setdefault("draft",  0)
        stats.setdefault("error",  0)
        stats["total"] = sum(stats.values())
        conn.close()
        return stats
    except Exception:
        return {"posted": 0, "draft": 0, "error": 0, "total": 0}


def _get_recent_posts(n: int = 8) -> list[dict]:
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT job_code, status, posted_at, error_msg FROM ad_posts ORDER BY id DESC LIMIT ?",
            (n,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def _tail_log(path: Path, n: int = 120) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-n:])
    except Exception:
        return f"(로그 없음: {path})"


# ── 메인 GUI ──────────────────────────────────────────────────────────────────
class BridgeControlPanel(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BRIDGE Control Panel")
        self.geometry("900x680")
        self.configure(bg=BG)
        self.resizable(True, True)

        self._build_ui()
        self._start_refresh_loop()

    # ── UI 빌드 ────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # 헤더
        hdr = tk.Frame(self, bg=BG, pady=6)
        hdr.pack(fill=tk.X, padx=16)
        tk.Label(hdr, text="BRIDGE", font=("Segoe UI", 18, "bold"),
                 bg=BG, fg=ACCENT).pack(side=tk.LEFT)
        tk.Label(hdr, text="  Control Panel", font=("Segoe UI", 14),
                 bg=BG, fg=TEXT_DIM).pack(side=tk.LEFT)
        self._status_lbl = tk.Label(hdr, text="● 대기", font=FONT_UI,
                                    bg=BG, fg=GREEN)
        self._status_lbl.pack(side=tk.RIGHT)

        # 탭
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook",          background=BG,  borderwidth=0)
        style.configure("TNotebook.Tab",      background=BG2, foreground=TEXT_DIM,
                        padding=[12, 5], font=FONT_UI)
        style.map("TNotebook.Tab",
                  background=[("selected", BG3)],
                  foreground=[("selected", TEXT)])

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self._tab_rpa      = self._make_rpa_tab(nb)
        self._tab_status   = self._make_status_tab(nb)
        self._tab_log_rpa  = self._make_log_tab(nb, "RPA 에러 로그", LOG_RPA)
        self._tab_log_pipe = self._make_log_tab(nb, "Pipeline 로그", LOG_PIPE)

        nb.add(self._tab_rpa,      text="  RPA 실행  ")
        nb.add(self._tab_status,   text="  포스팅 현황  ")
        nb.add(self._tab_log_rpa,  text="  RPA 로그  ")
        nb.add(self._tab_log_pipe, text="  Pipeline 로그  ")

    # ── RPA 실행 탭 ─────────────────────────────────────────────────────────
    def _make_rpa_tab(self, parent) -> tk.Frame:
        f = tk.Frame(parent, bg=BG2)

        # 컨트롤 패널
        ctrl = tk.Frame(f, bg=BG2, pady=10)
        ctrl.pack(fill=tk.X, padx=16)

        tk.Label(ctrl, text="포스팅 건수:", font=FONT_UI,
                 bg=BG2, fg=TEXT_DIM).grid(row=0, column=0, sticky="w", padx=4)
        self._limit_var = tk.IntVar(value=3)
        tk.Spinbox(ctrl, from_=1, to=50, textvariable=self._limit_var,
                   width=5, font=FONT_UI, bg=BG3, fg=TEXT,
                   buttonbackground=BG3, relief="flat").grid(row=0, column=1, padx=4)

        tk.Label(ctrl, text="Job코드(선택):", font=FONT_UI,
                 bg=BG2, fg=TEXT_DIM).grid(row=0, column=2, sticky="w", padx=(16,4))
        self._jobcode_var = tk.StringVar()
        tk.Entry(ctrl, textvariable=self._jobcode_var, width=14,
                 font=FONT_UI, bg=BG3, fg=TEXT,
                 insertbackground=TEXT, relief="flat").grid(row=0, column=3, padx=4)

        # 버튼 행
        btn_frame = tk.Frame(f, bg=BG2, pady=6)
        btn_frame.pack(fill=tk.X, padx=16)

        def _btn(text, color, cmd):
            return tk.Button(btn_frame, text=text, command=cmd,
                             font=FONT_H, bg=color, fg="white",
                             activebackground=color, relief="flat",
                             cursor="hand2", padx=14, pady=8)

        _btn("▶ DRY-RUN",  "#334155", self._run_dry).pack(side=tk.LEFT, padx=4)
        _btn("⬇ GENERATE", "#1d4ed8", self._run_gen).pack(side=tk.LEFT, padx=4)
        _btn("🚀 POST",     "#15803d", self._run_post).pack(side=tk.LEFT, padx=4)
        _btn("⏹ 중지",      "#991b1b", self._stop_rpa).pack(side=tk.LEFT, padx=20)

        # 보안 상태 표시
        sec = tk.Frame(f, bg=BG3, pady=6, padx=12)
        sec.pack(fill=tk.X, padx=16, pady=(4, 0))
        tk.Label(sec, text="🔒 보안 필터 활성:", font=FONT_UI,
                 bg=BG3, fg=TEXT_DIM).pack(side=tk.LEFT)
        for label in ["전화번호", "이메일", "학원명", "사업자번호", "주소"]:
            tk.Label(sec, text=f"  ✓ {label}", font=("Segoe UI", 9),
                     bg=BG3, fg=GREEN).pack(side=tk.LEFT)

        # 실행 로그
        sep = tk.Frame(f, bg=BG3, height=1)
        sep.pack(fill=tk.X, padx=16, pady=6)

        tk.Label(f, text="실행 로그", font=FONT_H,
                 bg=BG2, fg=TEXT_DIM).pack(anchor="w", padx=16)

        self._run_log = scrolledtext.ScrolledText(
            f, font=FONT_MONO, bg="#020617", fg=TEXT,
            insertbackground=TEXT, relief="flat", pady=4,
        )
        self._run_log.pack(fill=tk.BOTH, expand=True, padx=16, pady=(4, 12))

        # 색상 태그
        self._run_log.tag_config("ok",    foreground=GREEN)
        self._run_log.tag_config("error", foreground=RED)
        self._run_log.tag_config("warn",  foreground=YELLOW)
        self._run_log.tag_config("cmd",   foreground=ACCENT)
        self._run_log.tag_config("done",  foreground=TEXT_DIM)

        return f

    # ── 상태 탭 ──────────────────────────────────────────────────────────────
    def _make_status_tab(self, parent) -> tk.Frame:
        f = tk.Frame(parent, bg=BG2)

        # 통계 카드
        cards = tk.Frame(f, bg=BG2)
        cards.pack(fill=tk.X, padx=16, pady=12)

        self._stat_labels: dict[str, tk.Label] = {}
        for col, (key, label, color) in enumerate([
            ("total",  "전체",     TEXT),
            ("posted", "게시완료", GREEN),
            ("draft",  "Draft",   YELLOW),
            ("error",  "오류",    RED),
        ]):
            card = tk.Frame(cards, bg=BG3, padx=20, pady=14)
            card.grid(row=0, column=col, padx=6)
            lbl_val = tk.Label(card, text="—", font=("Segoe UI", 24, "bold"),
                               bg=BG3, fg=color)
            lbl_val.pack()
            tk.Label(card, text=label, font=FONT_UI,
                     bg=BG3, fg=TEXT_DIM).pack()
            self._stat_labels[key] = lbl_val

        tk.Button(f, text="↻ 새로고침", command=self._refresh_status,
                  font=FONT_UI, bg=ACCENT, fg="white",
                  relief="flat", cursor="hand2", padx=10, pady=4).pack(pady=4)

        # 최근 포스팅 목록
        sep = tk.Frame(f, bg=BG3, height=1)
        sep.pack(fill=tk.X, padx=16, pady=6)
        tk.Label(f, text="최근 게시 내역", font=FONT_H,
                 bg=BG2, fg=TEXT_DIM).pack(anchor="w", padx=16)

        cols = ("job_code", "status", "posted_at", "error_msg")
        tree = ttk.Treeview(f, columns=cols, show="headings", height=14)
        style = ttk.Style()
        style.configure("Treeview",           background=BG3, foreground=TEXT,
                        fieldbackground=BG3,  rowheight=24,   font=FONT_UI)
        style.configure("Treeview.Heading",   background=BG,  foreground=TEXT_DIM,
                        font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", ACCENT)])

        for c, w, h in [("job_code",  100, "Job코드"),
                         ("status",    80,  "상태"),
                         ("posted_at", 160, "게시일시"),
                         ("error_msg", 400, "에러")]:
            tree.column(c, width=w, anchor="w")
            tree.heading(c, text=h)

        tree.pack(fill=tk.BOTH, expand=True, padx=16, pady=(4, 12))
        self._tree = tree

        return f

    # ── 로그 탭 ──────────────────────────────────────────────────────────────
    def _make_log_tab(self, parent, title: str, log_path: Path) -> tk.Frame:
        f = tk.Frame(parent, bg=BG2)

        hdr = tk.Frame(f, bg=BG2)
        hdr.pack(fill=tk.X, padx=16, pady=6)
        tk.Label(hdr, text=title, font=FONT_H, bg=BG2, fg=TEXT_DIM).pack(side=tk.LEFT)
        tk.Label(hdr, text=str(log_path), font=("Segoe UI", 8),
                 bg=BG2, fg=BG3).pack(side=tk.LEFT, padx=8)
        tk.Button(hdr, text="↻", command=lambda: self._reload_log(txt, log_path),
                  font=FONT_UI, bg=BG3, fg=TEXT, relief="flat",
                  cursor="hand2").pack(side=tk.RIGHT)

        txt = scrolledtext.ScrolledText(
            f, font=FONT_MONO, bg="#020617", fg=TEXT,
            insertbackground=TEXT, relief="flat",
        )
        txt.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))
        txt.tag_config("warn",  foreground=YELLOW)
        txt.tag_config("error", foreground=RED)
        txt.tag_config("ok",    foreground=GREEN)

        self._reload_log(txt, log_path)

        # 해당 로그의 txt widget 저장 (자동 갱신용)
        if "RPA" in title:
            self._log_rpa_widget  = txt
            self._log_rpa_path    = log_path
        else:
            self._log_pipe_widget = txt
            self._log_pipe_path   = log_path

        return f

    def _reload_log(self, widget: scrolledtext.ScrolledText, path: Path):
        widget.delete("1.0", tk.END)
        content = _tail_log(path)
        for line in content.splitlines():
            widget.insert(tk.END, line + "\n")
            if "ERROR" in line or "error" in line:
                widget.tag_add("error", "end-2l", "end-1c")
            elif "WARNING" in line or "WARN" in line or "REDACT" in line:
                widget.tag_add("warn", "end-2l", "end-1c")
            elif "OK" in line or "posted" in line or "completed" in line:
                widget.tag_add("ok", "end-2l", "end-1c")
        widget.see(tk.END)

    # ── RPA 액션 ────────────────────────────────────────────────────────────
    def _build_args(self) -> list[str]:
        args: list[str] = []
        jc = self._jobcode_var.get().strip()
        if jc:
            args += ["--job-code", jc]
        else:
            args += ["--limit", str(self._limit_var.get())]
        return args

    def _launch(self, extra_args: list[str]):
        global _rpa_proc
        if _rpa_proc is not None:
            self._run_log.insert(tk.END, "[이미 실행 중입니다]\n", "warn")
            return
        args = extra_args + self._build_args()
        self._status_lbl.config(text="● 실행 중", fg=YELLOW)
        t = threading.Thread(target=_run_rpa, args=(args, self._run_log), daemon=True)
        t.start()
        self.after(500, self._watch_process)

    def _watch_process(self):
        if _rpa_proc is None:
            self._status_lbl.config(text="● 대기", fg=GREEN)
            self._refresh_status()
        else:
            self.after(500, self._watch_process)

    def _run_dry(self):   self._launch(["--dry-run"])
    def _run_gen(self):   self._launch(["--generate"])
    def _run_post(self):  self._launch([])

    def _stop_rpa(self):
        global _rpa_proc
        if _rpa_proc:
            _rpa_proc.terminate()
            self._run_log.insert(tk.END, "[⏹ 수동 중지]\n", "warn")
            self._status_lbl.config(text="● 중지됨", fg=RED)

    # ── 상태 갱신 ────────────────────────────────────────────────────────────
    def _refresh_status(self):
        stats = _get_stats()
        for key, lbl in self._stat_labels.items():
            lbl.config(text=str(stats.get(key, 0)))

        self._tree.delete(*self._tree.get_children())
        for row in _get_recent_posts():
            tag = "ok" if row["status"] == "posted" else \
                  "err" if row["status"] == "error" else ""
            self._tree.insert("", tk.END, values=(
                row["job_code"],
                row["status"],
                (row["posted_at"] or "")[:16],
                (row["error_msg"] or "")[:80],
            ), tags=(tag,))

        self._tree.tag_configure("ok",  foreground=GREEN)
        self._tree.tag_configure("err", foreground=RED)

    def _start_refresh_loop(self):
        """5초마다 상태·로그 자동 갱신."""
        self._refresh_status()
        try:
            self._reload_log(self._log_rpa_widget,  self._log_rpa_path)
            self._reload_log(self._log_pipe_widget, self._log_pipe_path)
        except AttributeError:
            pass
        self.after(5000, self._start_refresh_loop)


# ── 진입점 ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = BridgeControlPanel()
    app.mainloop()
