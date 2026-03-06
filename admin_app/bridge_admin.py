"""
BRIDGE Admin Desktop App
=========================
관리자용 데스크톱 앱 — 인터뷰 스케줄링, 접수 관리, DB 백업
Python tkinter + API 연동

실행: python bridge_admin.py
빌드: pyinstaller --onefile --windowed --icon=bridge_icon.ico bridge_admin.py
"""

import os
import sys
import json
import shutil
import sqlite3
import logging
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import (
    Tk, Frame, Label, Entry, Button, Text, Scrollbar, StringVar,
    OptionMenu, messagebox, filedialog, ttk, END, BOTH, LEFT,
    RIGHT, TOP, BOTTOM, X, Y, W, E, N, S, WORD, VERTICAL,
    HORIZONTAL, DISABLED, NORMAL,
)

# ── 설정 ──────────────────────────────────────────────────────────────────────
APP_TITLE = "BRIDGE Admin"
APP_VERSION = "1.0.0"

# .env에서 환경변수 로드
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

API_BASE = os.getenv("BRIDGE_ADMIN_API_URL", "http://localhost:8000")
DB_PATH = os.getenv("BRIDGE_DB_PATH", str(Path(__file__).resolve().parent.parent / "master.db"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(Path(__file__).resolve().parent / "admin_app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("bridge.admin_app")


# ── HTTP 유틸 ─────────────────────────────────────────────────────────────────
try:
    import httpx
    _HTTP_OK = True
except ImportError:
    _HTTP_OK = False
    log.warning("httpx 미설치 — pip install httpx")


def api_call(method: str, path: str, admin_key: str, body: dict = None) -> dict:
    """API 호출 래퍼."""
    if not _HTTP_OK:
        return {"success": False, "error": "httpx 미설치"}
    url = f"{API_BASE}{path}"
    headers = {"Content-Type": "application/json", "x-admin-key": admin_key}
    try:
        with httpx.Client(timeout=15) as client:
            if method == "GET":
                r = client.get(url, headers=headers)
            elif method == "POST":
                r = client.post(url, headers=headers, json=body or {})
            elif method == "PATCH":
                r = client.patch(url, headers=headers, json=body or {})
            elif method == "DELETE":
                r = client.delete(url, headers=headers)
            else:
                return {"success": False, "error": f"Unknown method: {method}"}
            return r.json()
    except Exception as e:
        log.error("API 호출 실패: %s %s — %s", method, path, e)
        return {"success": False, "error": str(e)}


# ── 색상 팔레트 ──────────────────────────────────────────────────────────────
class Colors:
    BG = "#f8f9fa"
    CARD = "#ffffff"
    PRIMARY = "#1d1d1f"
    ACCENT = "#0071e3"
    SUCCESS = "#34c759"
    WARNING = "#ff9500"
    DANGER = "#ff3b30"
    GRAY = "#8e8e93"
    LIGHT_GRAY = "#f2f2f7"
    BORDER = "#e5e5ea"
    TEXT = "#1d1d1f"
    TEXT_SEC = "#6e6e73"


# ══════════════════════════════════════════════════════════════════════════════
# 메인 앱
# ══════════════════════════════════════════════════════════════════════════════

class BridgeAdminApp:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title(f"{APP_TITLE} v{APP_VERSION}")
        self.root.geometry("1100x750")
        self.root.configure(bg=Colors.BG)
        self.root.minsize(900, 600)

        self.admin_key = StringVar(value="")
        self.authed = False

        # 스타일
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Card.TFrame", background=Colors.CARD)
        style.configure("Accent.TButton", background=Colors.ACCENT, foreground="white")
        style.configure("Danger.TButton", background=Colors.DANGER, foreground="white")
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

        self._build_auth_screen()

    # ── Auth Screen ──────────────────────────────────────────────────────────
    def _build_auth_screen(self):
        self._clear()
        frame = Frame(self.root, bg=Colors.BG)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        Label(frame, text="BRIDGE", font=("Segoe UI", 32, "bold"),
              bg=Colors.BG, fg=Colors.PRIMARY).pack(pady=(0, 5))
        Label(frame, text="Admin Desktop", font=("Segoe UI", 14),
              bg=Colors.BG, fg=Colors.TEXT_SEC).pack(pady=(0, 30))

        Label(frame, text="Admin API Key", font=("Segoe UI", 10),
              bg=Colors.BG, fg=Colors.TEXT_SEC).pack()
        entry = Entry(frame, textvariable=self.admin_key, show="*",
                      font=("Segoe UI", 12), width=40, justify="center",
                      relief="solid", bd=1)
        entry.pack(pady=(5, 20))
        entry.bind("<Return>", lambda e: self._do_auth())

        Button(frame, text="Login", font=("Segoe UI", 11, "bold"),
               bg=Colors.PRIMARY, fg="white", relief="flat",
               padx=40, pady=8, cursor="hand2",
               command=self._do_auth).pack()

    def _do_auth(self):
        key = self.admin_key.get().strip()
        if not key:
            messagebox.showwarning("Error", "Admin key를 입력하세요.")
            return
        # 키 검증 — health check via API
        result = api_call("GET", "/api/admin/interviews", key)
        if result.get("success") is False and "401" in str(result.get("error", "")):
            messagebox.showerror("Auth Failed", "Admin key가 올바르지 않습니다.")
            return
        self.authed = True
        self._build_main()

    # ── Main Dashboard ───────────────────────────────────────────────────────
    def _build_main(self):
        self._clear()

        # 상단 바
        topbar = Frame(self.root, bg=Colors.PRIMARY, height=48)
        topbar.pack(fill=X)
        topbar.pack_propagate(False)

        Label(topbar, text=f"  BRIDGE Admin", font=("Segoe UI", 13, "bold"),
              bg=Colors.PRIMARY, fg="white").pack(side=LEFT, padx=10)
        Label(topbar, text=f"v{APP_VERSION}", font=("Segoe UI", 9),
              bg=Colors.PRIMARY, fg="#aaa").pack(side=LEFT)

        Button(topbar, text="Backup DB", font=("Segoe UI", 9),
               bg="#2c2c2e", fg="white", relief="flat", cursor="hand2",
               command=self._backup_db).pack(side=RIGHT, padx=5, pady=8)
        Button(topbar, text="Open Site", font=("Segoe UI", 9),
               bg="#2c2c2e", fg="white", relief="flat", cursor="hand2",
               command=lambda: webbrowser.open("https://bridgejob.co.kr")).pack(side=RIGHT, padx=5, pady=8)
        Button(topbar, text="🔑 Change PW", font=("Segoe UI", 9),
               bg="#3a3a3c", fg="#ff9f0a", relief="flat", cursor="hand2",
               command=self._change_password_dialog).pack(side=RIGHT, padx=5, pady=8)

        # 탭
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # Tab 1: 인터뷰
        self.interview_frame = Frame(notebook, bg=Colors.BG)
        notebook.add(self.interview_frame, text="  Interviews  ")
        self._build_interview_tab()

        # Tab 2: 접수 현황
        self.apps_frame = Frame(notebook, bg=Colors.BG)
        notebook.add(self.apps_frame, text="  Applications  ")
        self._build_applications_tab()

        # Tab 3: 게시판
        self.posts_frame = Frame(notebook, bg=Colors.BG)
        notebook.add(self.posts_frame, text="  Community  ")
        self._build_posts_tab()

        # Tab 4: 통계 & 백업
        self.stats_frame = Frame(notebook, bg=Colors.BG)
        notebook.add(self.stats_frame, text="  Stats & Backup  ")
        self._build_stats_tab()

    # ── Tab: Interviews ──────────────────────────────────────────────────────
    def _build_interview_tab(self):
        parent = self.interview_frame

        # 상단 컨트롤
        ctrl = Frame(parent, bg=Colors.BG)
        ctrl.pack(fill=X, pady=(10, 5), padx=10)

        Label(ctrl, text="Interview Management", font=("Segoe UI", 14, "bold"),
              bg=Colors.BG, fg=Colors.PRIMARY).pack(side=LEFT)
        Button(ctrl, text="+ New Interview", font=("Segoe UI", 9, "bold"),
               bg=Colors.ACCENT, fg="white", relief="flat", cursor="hand2",
               padx=12, pady=4,
               command=self._new_interview_dialog).pack(side=RIGHT, padx=5)
        Button(ctrl, text="Refresh", font=("Segoe UI", 9),
               bg=Colors.LIGHT_GRAY, fg=Colors.TEXT, relief="flat", cursor="hand2",
               padx=12, pady=4,
               command=self._load_interviews).pack(side=RIGHT)

        # 트리뷰
        cols = ("id", "date", "time", "candidate", "employer", "meet", "status", "email")
        tree_frame = Frame(parent, bg=Colors.BG)
        tree_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

        self.interview_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=15)
        for col, w, anchor in [
            ("id", 40, "center"), ("date", 100, W), ("time", 70, "center"),
            ("candidate", 150, W), ("employer", 150, W),
            ("meet", 180, W), ("status", 80, "center"), ("email", 60, "center"),
        ]:
            self.interview_tree.heading(col, text=col.title())
            self.interview_tree.column(col, width=w, anchor=anchor)

        vsb = Scrollbar(tree_frame, orient=VERTICAL, command=self.interview_tree.yview)
        self.interview_tree.configure(yscrollcommand=vsb.set)
        self.interview_tree.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=RIGHT, fill=Y)

        # 하단 액션
        action_bar = Frame(parent, bg=Colors.BG)
        action_bar.pack(fill=X, padx=10, pady=5)

        for text, status_val, color in [
            ("Mark Completed", "completed", Colors.SUCCESS),
            ("Mark No-Show", "no_show", Colors.WARNING),
            ("Cancel", "cancelled", Colors.DANGER),
        ]:
            Button(action_bar, text=text, font=("Segoe UI", 9),
                   bg=color, fg="white", relief="flat", cursor="hand2",
                   padx=10, pady=3,
                   command=lambda s=status_val: self._update_interview_status(s)).pack(side=LEFT, padx=3)

        Button(action_bar, text="Delete", font=("Segoe UI", 9),
               bg=Colors.DANGER, fg="white", relief="flat", cursor="hand2",
               padx=10, pady=3,
               command=self._delete_interview).pack(side=RIGHT, padx=3)

        self._load_interviews()

    def _load_interviews(self):
        """API에서 인터뷰 목록 로드."""
        def fetch():
            result = api_call("GET", "/api/admin/interviews", self.admin_key.get())
            self.root.after(0, lambda: self._populate_interviews(result))
        threading.Thread(target=fetch, daemon=True).start()

    def _populate_interviews(self, result: dict):
        tree = self.interview_tree
        for item in tree.get_children():
            tree.delete(item)
        if not result.get("success"):
            return
        for iv in (result.get("data") or []):
            email_status = ""
            if iv.get("email_sent_candidate"):
                email_status += "C"
            if iv.get("email_sent_employer"):
                email_status += "E"
            tree.insert("", END, values=(
                iv["id"], iv["interview_date"], iv["interview_time"],
                iv.get("candidate_name", ""), iv.get("employer_name", ""),
                iv.get("meet_link", "")[:40], iv["status"],
                email_status or "-",
            ))

    def _new_interview_dialog(self):
        """인터뷰 생성 다이얼로그."""
        dlg = _InterviewDialog(self.root, self.admin_key.get())
        self.root.wait_window(dlg.top)
        if dlg.result:
            self._load_interviews()

    def _update_interview_status(self, new_status: str):
        sel = self.interview_tree.selection()
        if not sel:
            messagebox.showinfo("Info", "인터뷰를 선택하세요.")
            return
        item = self.interview_tree.item(sel[0])
        iv_id = item["values"][0]
        result = api_call("PATCH", f"/api/admin/interviews/{iv_id}",
                          self.admin_key.get(), {"status": new_status})
        if result.get("success"):
            messagebox.showinfo("Success", f"Interview #{iv_id} → {new_status}")
            self._load_interviews()
        else:
            messagebox.showerror("Error", result.get("message", "Failed"))

    def _delete_interview(self):
        sel = self.interview_tree.selection()
        if not sel:
            return
        item = self.interview_tree.item(sel[0])
        iv_id = item["values"][0]
        if not messagebox.askyesno("Confirm", f"Interview #{iv_id}를 삭제하시겠습니까?"):
            return
        result = api_call("DELETE", f"/api/admin/interviews/{iv_id}", self.admin_key.get())
        if result.get("success"):
            self._load_interviews()

    # ── Tab: Applications ────────────────────────────────────────────────────
    def _build_applications_tab(self):
        parent = self.apps_frame

        ctrl = Frame(parent, bg=Colors.BG)
        ctrl.pack(fill=X, pady=(10, 5), padx=10)
        Label(ctrl, text="Applications", font=("Segoe UI", 14, "bold"),
              bg=Colors.BG, fg=Colors.PRIMARY).pack(side=LEFT)
        Button(ctrl, text="Refresh", font=("Segoe UI", 9),
               bg=Colors.LIGHT_GRAY, fg=Colors.TEXT, relief="flat", cursor="hand2",
               padx=12, pady=4,
               command=self._load_applications).pack(side=RIGHT)

        cols = ("id", "type", "name", "email", "status", "created")
        tree_frame = Frame(parent, bg=Colors.BG)
        tree_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

        self.apps_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=18)
        for col, w in [("id", 60), ("type", 80), ("name", 180), ("email", 200), ("status", 100), ("created", 160)]:
            self.apps_tree.heading(col, text=col.title())
            self.apps_tree.column(col, width=w)

        vsb = Scrollbar(tree_frame, orient=VERTICAL, command=self.apps_tree.yview)
        self.apps_tree.configure(yscrollcommand=vsb.set)
        self.apps_tree.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=RIGHT, fill=Y)

        self._load_applications()

    def _load_applications(self):
        def fetch():
            result = api_call("GET", "/api/admin/applications", self.admin_key.get())
            self.root.after(0, lambda: self._populate_apps(result))
        threading.Thread(target=fetch, daemon=True).start()

    def _populate_apps(self, result: dict):
        tree = self.apps_tree
        for item in tree.get_children():
            tree.delete(item)
        if not result.get("success"):
            return
        for a in (result.get("data") or []):
            tree.insert("", END, values=(
                a.get("id", "")[:8] if isinstance(a.get("id"), str) else a.get("id", ""),
                a.get("type", ""),
                a.get("name", ""),
                a.get("email", ""),
                a.get("status", ""),
                a.get("created_at", "")[:16],
            ))

    # ── Tab: Community Posts ─────────────────────────────────────────────────
    def _build_posts_tab(self):
        parent = self.posts_frame

        ctrl = Frame(parent, bg=Colors.BG)
        ctrl.pack(fill=X, pady=(10, 5), padx=10)
        Label(ctrl, text="Community Posts", font=("Segoe UI", 14, "bold"),
              bg=Colors.BG, fg=Colors.PRIMARY).pack(side=LEFT)
        Button(ctrl, text="Refresh", font=("Segoe UI", 9),
               bg=Colors.LIGHT_GRAY, fg=Colors.TEXT, relief="flat", cursor="hand2",
               padx=12, pady=4,
               command=self._load_posts).pack(side=RIGHT)

        # 보드별 게시물 수 표시
        self.posts_stats_label = Label(parent, text="Loading...",
                                       font=("Segoe UI", 10), bg=Colors.BG, fg=Colors.TEXT_SEC)
        self.posts_stats_label.pack(fill=X, padx=10, pady=5)

        cols = ("board", "count")
        tree_frame = Frame(parent, bg=Colors.BG)
        tree_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

        self.posts_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=10)
        self.posts_tree.heading("board", text="Board")
        self.posts_tree.heading("count", text="Posts")
        self.posts_tree.column("board", width=200)
        self.posts_tree.column("count", width=100, anchor="center")
        self.posts_tree.pack(fill=BOTH, expand=True)

        self._load_posts()

    def _load_posts(self):
        """직접 DB에서 보드별 통계 조회."""
        def fetch():
            try:
                conn = sqlite3.connect(DB_PATH)
                rows = conn.execute("""
                    SELECT board, COUNT(*) as cnt
                    FROM community_posts WHERE is_deleted=0
                    GROUP BY board ORDER BY cnt DESC
                """).fetchall()
                total = sum(r[1] for r in rows)
                conn.close()
                self.root.after(0, lambda: self._populate_posts(rows, total))
            except Exception as e:
                log.error("Posts 로드 실패: %s", e)

        threading.Thread(target=fetch, daemon=True).start()

    def _populate_posts(self, rows, total):
        tree = self.posts_tree
        for item in tree.get_children():
            tree.delete(item)
        for board, count in rows:
            tree.insert("", END, values=(board, count))
        self.posts_stats_label.config(text=f"Total: {total} posts across {len(rows)} boards")

    # ── Tab: Stats & Backup ──────────────────────────────────────────────────
    def _build_stats_tab(self):
        parent = self.stats_frame

        Label(parent, text="Database & Backup", font=("Segoe UI", 14, "bold"),
              bg=Colors.BG, fg=Colors.PRIMARY).pack(anchor=W, padx=10, pady=(10, 5))

        # DB 정보
        info_frame = Frame(parent, bg=Colors.CARD, relief="solid", bd=1)
        info_frame.pack(fill=X, padx=10, pady=5)

        db_size = Path(DB_PATH).stat().st_size / 1024 / 1024 if Path(DB_PATH).exists() else 0
        for label, value in [
            ("Database Path:", DB_PATH),
            ("Size:", f"{db_size:.1f} MB"),
            ("API Server:", API_BASE),
        ]:
            row = Frame(info_frame, bg=Colors.CARD)
            row.pack(fill=X, padx=15, pady=3)
            Label(row, text=label, font=("Segoe UI", 10, "bold"),
                  bg=Colors.CARD, fg=Colors.TEXT, width=15, anchor=W).pack(side=LEFT)
            Label(row, text=value, font=("Segoe UI", 10),
                  bg=Colors.CARD, fg=Colors.TEXT_SEC).pack(side=LEFT)

        # 백업 버튼
        btn_frame = Frame(parent, bg=Colors.BG)
        btn_frame.pack(fill=X, padx=10, pady=15)

        Button(btn_frame, text="Backup Database Now", font=("Segoe UI", 11, "bold"),
               bg=Colors.SUCCESS, fg="white", relief="flat", cursor="hand2",
               padx=20, pady=8,
               command=self._backup_db).pack(side=LEFT, padx=5)

        Button(btn_frame, text="Open Backup Folder", font=("Segoe UI", 11),
               bg=Colors.LIGHT_GRAY, fg=Colors.TEXT, relief="flat", cursor="hand2",
               padx=20, pady=8,
               command=self._open_backup_folder).pack(side=LEFT, padx=5)

        # 백업 히스토리
        Label(parent, text="Backup History", font=("Segoe UI", 12, "bold"),
              bg=Colors.BG, fg=Colors.PRIMARY).pack(anchor=W, padx=10, pady=(20, 5))

        self.backup_log = Text(parent, font=("Consolas", 9), height=10,
                               bg=Colors.CARD, fg=Colors.TEXT, relief="solid", bd=1,
                               state=DISABLED, wrap=WORD)
        self.backup_log.pack(fill=BOTH, expand=True, padx=10, pady=5)

        self._refresh_backup_log()

    def _backup_db(self):
        """master.db 백업."""
        if not Path(DB_PATH).exists():
            messagebox.showerror("Error", f"DB 파일을 찾을 수 없습니다: {DB_PATH}")
            return

        backup_dir = Path(DB_PATH).parent / "backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"master_backup_{timestamp}.db"

        try:
            # SQLite online backup (안전)
            src = sqlite3.connect(DB_PATH)
            dst = sqlite3.connect(str(backup_path))
            src.backup(dst)
            dst.close()
            src.close()

            size_mb = backup_path.stat().st_size / 1024 / 1024
            log.info("DB 백업 완료: %s (%.1f MB)", backup_path, size_mb)
            messagebox.showinfo("Backup Complete",
                                f"백업 완료!\n{backup_path}\n({size_mb:.1f} MB)")
            self._refresh_backup_log()

        except Exception as e:
            log.error("백업 실패: %s", e, exc_info=True)
            messagebox.showerror("Backup Failed", str(e))

    def _open_backup_folder(self):
        backup_dir = Path(DB_PATH).parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(backup_dir))
        else:
            webbrowser.open(str(backup_dir))

    def _refresh_backup_log(self):
        backup_dir = Path(DB_PATH).parent / "backups"
        self.backup_log.config(state=NORMAL)
        self.backup_log.delete("1.0", END)
        if backup_dir.exists():
            files = sorted(backup_dir.glob("*.db"), key=lambda f: f.stat().st_mtime, reverse=True)
            for f in files[:20]:
                size_mb = f.stat().st_size / 1024 / 1024
                mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                self.backup_log.insert(END, f"  {mtime}  {f.name}  ({size_mb:.1f} MB)\n")
        if not self.backup_log.get("1.0", END).strip():
            self.backup_log.insert(END, "  No backups yet. Click 'Backup Database Now' to create one.")
        self.backup_log.config(state=DISABLED)

    # ── 유틸 ─────────────────────────────────────────────────────────────────
    def _clear(self):
        for widget in self.root.winfo_children():
            widget.destroy()


# ══════════════════════════════════════════════════════════════════════════════
# Interview 생성 다이얼로그
# ══════════════════════════════════════════════════════════════════════════════

class _InterviewDialog:
    def __init__(self, parent, admin_key: str):
        self.admin_key = admin_key
        self.result = None

        self.top = top = tk_Toplevel(parent)
        top.title("Schedule Interview")
        top.geometry("500x520")
        top.resizable(False, False)
        top.configure(bg=Colors.BG)
        top.grab_set()

        Label(top, text="New Interview", font=("Segoe UI", 16, "bold"),
              bg=Colors.BG, fg=Colors.PRIMARY).pack(pady=(15, 10))

        form = Frame(top, bg=Colors.BG)
        form.pack(fill=X, padx=30)

        self.fields = {}
        for label, key, placeholder in [
            ("Candidate Name", "candidate_name", "e.g. Sarah Johnson"),
            ("Candidate Email", "candidate_email", "e.g. sarah@example.com"),
            ("Employer Name", "employer_name", "e.g. ABC Academy"),
            ("Employer Email", "employer_email", "e.g. admin@abcacademy.com"),
            ("Date (YYYY-MM-DD)", "interview_date", "e.g. 2026-03-15"),
            ("Time (HH:MM KST)", "interview_time", "e.g. 14:00"),
            ("Google Meet Link", "meet_link", "https://meet.google.com/xxx-xxxx-xxx"),
        ]:
            Label(form, text=label, font=("Segoe UI", 9),
                  bg=Colors.BG, fg=Colors.TEXT_SEC).pack(anchor=W, pady=(8, 2))
            e = Entry(form, font=("Segoe UI", 10), relief="solid", bd=1)
            e.insert(0, "")
            e.pack(fill=X)
            self.fields[key] = e

        # Notes
        Label(form, text="Notes", font=("Segoe UI", 9),
              bg=Colors.BG, fg=Colors.TEXT_SEC).pack(anchor=W, pady=(8, 2))
        self.notes_entry = Entry(form, font=("Segoe UI", 10), relief="solid", bd=1)
        self.notes_entry.pack(fill=X)

        # Buttons
        btn_frame = Frame(top, bg=Colors.BG)
        btn_frame.pack(fill=X, padx=30, pady=20)

        Button(btn_frame, text="Schedule & Send Email", font=("Segoe UI", 10, "bold"),
               bg=Colors.ACCENT, fg="white", relief="flat", cursor="hand2",
               padx=16, pady=6,
               command=self._submit).pack(side=RIGHT, padx=5)
        Button(btn_frame, text="Cancel", font=("Segoe UI", 10),
               bg=Colors.LIGHT_GRAY, fg=Colors.TEXT, relief="flat", cursor="hand2",
               padx=16, pady=6,
               command=top.destroy).pack(side=RIGHT)

    def _submit(self):
        data = {k: e.get().strip() for k, e in self.fields.items()}
        data["notes"] = self.notes_entry.get().strip()
        data["send_email"] = True

        if not data["interview_date"] or not data["interview_time"] or not data["meet_link"]:
            messagebox.showwarning("Missing Fields", "Date, Time, Meet Link는 필수입니다.")
            return

        result = api_call("POST", "/api/admin/interviews", self.admin_key, data)
        if result.get("success"):
            email_info = result.get("data", {}).get("email_sent", {})
            msg = f"Interview created! (ID: {result['data']['id']})"
            if email_info.get("candidate"):
                msg += "\nCandidate email sent."
            if email_info.get("employer"):
                msg += "\nEmployer email sent."
            messagebox.showinfo("Success", msg)
            self.result = result
            self.top.destroy()
        else:
            messagebox.showerror("Error", result.get("message", "Failed to create interview"))


    def _change_password_dialog(self):
        """관리자 비밀번호 변경 — 입력 글자 안 보임."""
        win = tk_Toplevel(self.root)
        win.title("비밀번호 변경")
        win.geometry("380x280")
        win.resizable(False, False)
        win.configure(bg=Colors.BG)
        win.grab_set()

        Label(win, text="관리자 비밀번호 변경", font=("Segoe UI", 14, "bold"),
              bg=Colors.BG, fg=Colors.PRIMARY).pack(pady=(24, 4))
        Label(win, text="입력 내용은 화면에 표시되지 않습니다", font=("Segoe UI", 9),
              bg=Colors.BG, fg=Colors.TEXT_SEC).pack(pady=(0, 18))

        frame = Frame(win, bg=Colors.BG)
        frame.pack(fill=X, padx=30)

        Label(frame, text="새 비밀번호", font=("Segoe UI", 10),
              bg=Colors.BG, fg=Colors.TEXT).pack(anchor=W)
        pw1_var = StringVar()
        Entry(frame, textvariable=pw1_var, show="●", font=("Segoe UI", 12),
              relief="solid", bd=1).pack(fill=X, pady=(3, 12))

        Label(frame, text="비밀번호 확인", font=("Segoe UI", 10),
              bg=Colors.BG, fg=Colors.TEXT).pack(anchor=W)
        pw2_var = StringVar()
        Entry(frame, textvariable=pw2_var, show="●", font=("Segoe UI", 12),
              relief="solid", bd=1).pack(fill=X, pady=(3, 18))

        def _submit():
            pw = pw1_var.get()
            if len(pw) < 8:
                messagebox.showwarning("오류", "비밀번호는 8자 이상이어야 합니다.", parent=win)
                return
            if pw != pw2_var.get():
                messagebox.showwarning("오류", "비밀번호가 일치하지 않습니다.", parent=win)
                return
            result = api_call("POST", "/api/admin/change-password",
                              self.admin_key.get(),
                              {"new_password": pw})
            if result.get("success"):
                messagebox.showinfo("완료",
                    "비밀번호 변경 완료!\n\n"
                    "⚠️ Render 대시보드에서도 ADMIN_PASSWORD를\n"
                    "업데이트한 후 서버를 재시작하세요.", parent=win)
                win.destroy()
            else:
                messagebox.showerror("실패", result.get("message", "변경 실패"), parent=win)

        Button(frame, text="변경", font=("Segoe UI", 11, "bold"),
               bg=Colors.ACCENT, fg="white", relief="flat", cursor="hand2",
               padx=30, pady=6, command=_submit).pack()


# tkinter.Toplevel alias
from tkinter import Toplevel as tk_Toplevel


# ── 실행 ─────────────────────────────────────────────────────────────────────
def main():
    root = Tk()

    # 아이콘 설정 (있으면)
    icon_path = Path(__file__).resolve().parent / "bridge_icon.ico"
    if icon_path.exists():
        try:
            root.iconbitmap(str(icon_path))
        except Exception:
            pass

    app = BridgeAdminApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
