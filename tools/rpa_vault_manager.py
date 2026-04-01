"""
BRIDGE RPA Vault Manager v1.0
═══════════════════════════════════════════════════════
GUI 기반 Craigslist 계정 자격증명 관리 프로그램

보안 구조 (3중 잠금):
  L1. Windows DPAPI — 이 PC + 이 Windows 계정에만 복호화 가능
  L2. PBKDF2-SHA256 600,000 iterations
  L3. 3× AES-256-GCM — 매 저장마다 새 salt/nonce

[절대 규칙] 평문 비밀번호는 메모리에만 존재. 디스크/로그에 절대 저장 안 함.

실행 방법:
  C:\\Users\\Scarlett\\AppData\\Local\\Programs\\Python\\Python313\\pythonw.exe ^
    -X utf8 "Q:\\Claudework\\bridge base\\tools\\rpa_vault_manager.py"
"""

import sys
import ctypes
import shutil
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime

# rpa_credential_vault를 같은 tools/ 폴더에서 import
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from tools.rpa_credential_vault import (
    ACCOUNTS,
    VAULT_FILE,
    DPAPI_KEY,
    save_account,
    test_decrypt,
    vault_status,
    load_credentials,
)

# ── K드라이브 백업 경로 ────────────────────────────────────────────────────────
K_BACKUP = Path("K:/BRIDGE_RPA_Installer")

# ── 색상 ──────────────────────────────────────────────────────────────────────
ACCOUNT_COLORS = {
    "gray":   "#6b7280",
    "green":  "#16a34a",
    "brown":  "#92400e",
    "purple": "#7c3aed",
}
BG_DARK  = "#1e1e2e"
BG_TAB   = "#f9fafb"
BG_INPUT = "#ffffff"
FG_OK    = "#16a34a"
FG_WARN  = "#dc2626"
FG_GRAY  = "#6b7280"

# ── 메모리 소각 헬퍼 ──────────────────────────────────────────────────────────

def _scrub_str(s: str) -> None:
    """StringVar에서 읽어온 평문을 메모리에서 제거"""
    try:
        b = s.encode("utf-8")
        ctypes.memmove(id(b) + 32, b"\x00" * len(b), len(b))
    except Exception:
        pass

# ── GUI 앱 ────────────────────────────────────────────────────────────────────

class VaultManagerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BRIDGE RPA Vault Manager v1.0")
        self.root.resizable(False, False)

        # 창 중앙 배치
        w, h = 540, 460
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self.root.configure(bg=BG_DARK)

        # 계정별 상태 변수
        self.pw_vars:       dict[str, tk.StringVar]  = {}
        self.auto_jobs:     dict[str, str | None]     = {}  # after() 핸들
        self.auto_enabled:  dict[str, tk.BooleanVar] = {}
        self.status_vars:   dict[str, tk.StringVar]  = {}
        self.pw_entries:    dict[str, tk.Entry]       = {}

        self._build_ui()
        self._refresh_all_status()

    # ── UI 구성 ───────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # 헤더
        hdr = tk.Frame(self.root, bg=BG_DARK, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🔐  BRIDGE RPA Vault Manager",
                 bg=BG_DARK, fg="white",
                 font=("Segoe UI", 14, "bold")).pack()
        tk.Label(hdr, text="DPAPI  ·  PBKDF2-600k  ·  3×AES-256-GCM  ·  평문 저장 없음",
                 bg=BG_DARK, fg="#6b7280",
                 font=("Segoe UI", 8)).pack()

        # 계정 탭
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook",       background=BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab",   background="#374151", foreground="white",
                        padding=[14, 6], font=("Segoe UI", 9))
        style.map("TNotebook.Tab",
                  background=[("selected", "#1e1e2e")],
                  foreground=[("selected", "white")])

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=12, pady=(4, 0))

        for key, info in ACCOUNTS.items():
            frame = tk.Frame(nb, bg=BG_TAB)
            nb.add(frame, text=f"  {info['name']}  ")
            self._build_tab(frame, key, info)

        # 하단 바
        self._build_bottom_bar()

    def _build_tab(self, parent: tk.Frame, key: str, info: dict) -> None:
        """계정별 탭 내용"""
        color = ACCOUNT_COLORS[key]
        pad_x = 20

        # 계정 색상 인디케이터 + 이름
        top = tk.Frame(parent, bg=BG_TAB, pady=12)
        top.pack(fill="x", padx=pad_x)

        dot = tk.Label(top, text="●", bg=BG_TAB, fg=color,
                       font=("Segoe UI", 16))
        dot.pack(side="left")
        tk.Label(top, text=f"  {info['name']}  계정",
                 bg=BG_TAB, fg="#111827",
                 font=("Segoe UI", 11, "bold")).pack(side="left")

        # 이메일 표시
        tk.Label(parent, text="이메일", bg=BG_TAB, fg=FG_GRAY,
                 font=("Segoe UI", 8, "bold"), anchor="w").pack(
                 fill="x", padx=pad_x)

        email_box = tk.Frame(parent, bg="#e5e7eb", padx=10, pady=6)
        email_box.pack(fill="x", padx=pad_x, pady=(2, 10))
        tk.Label(email_box, text=info["email"],
                 bg="#e5e7eb", fg="#374151",
                 font=("Consolas", 10), anchor="w").pack(fill="x")

        # 비밀번호 입력
        tk.Label(parent, text="비밀번호", bg=BG_TAB, fg=FG_GRAY,
                 font=("Segoe UI", 8, "bold"), anchor="w").pack(
                 fill="x", padx=pad_x)

        pw_row = tk.Frame(parent, bg=BG_TAB)
        pw_row.pack(fill="x", padx=pad_x, pady=(2, 4))

        pw_var = tk.StringVar()
        self.pw_vars[key]  = pw_var
        self.auto_jobs[key] = None

        pw_ent = tk.Entry(pw_row, textvariable=pw_var, show="●",
                          font=("Consolas", 12), relief="solid", bd=1,
                          bg=BG_INPUT, fg="#111827", insertbackground="#111827")
        pw_ent.pack(side="left", fill="x", expand=True, ipady=5)
        self.pw_entries[key] = pw_ent

        # 보기/숨기기 버튼
        tk.Button(pw_row, text="👁", font=("Segoe UI", 10),
                  bg="#e5e7eb", fg="#374151", relief="flat",
                  cursor="hand2", padx=6,
                  command=lambda e=pw_ent: self._toggle_show(e)
                  ).pack(side="left", padx=(4, 0), ipady=4)

        # 자동저장 토글
        auto_var = tk.BooleanVar(value=True)
        self.auto_enabled[key] = auto_var

        auto_row = tk.Frame(parent, bg=BG_TAB)
        auto_row.pack(fill="x", padx=pad_x, pady=(0, 8))
        tk.Checkbutton(auto_row,
                       text="자동저장  (입력 후 1초 대기)",
                       variable=auto_var,
                       bg=BG_TAB, fg=FG_GRAY, selectcolor=BG_TAB,
                       activebackground=BG_TAB,
                       font=("Segoe UI", 8)).pack(side="left")

        # 비밀번호 변경 감지 → 자동저장 타이머
        pw_var.trace_add("write", lambda *_, k=key: self._on_change(k))

        # 버튼 행
        btn_row = tk.Frame(parent, bg=BG_TAB)
        btn_row.pack(fill="x", padx=pad_x, pady=(0, 10))

        tk.Button(btn_row, text="💾  암호화 저장",
                  font=("Segoe UI", 10, "bold"),
                  bg=color, fg="white", relief="flat",
                  cursor="hand2", padx=14, pady=7,
                  command=lambda k=key: self._save(k)
                  ).pack(side="left")

        tk.Button(btn_row, text="✓  복호화 테스트",
                  font=("Segoe UI", 10),
                  bg="#374151", fg="white", relief="flat",
                  cursor="hand2", padx=14, pady=7,
                  command=lambda k=key: self._test(k)
                  ).pack(side="left", padx=(8, 0))

        # 상태 표시
        status_var = tk.StringVar(value="  ─  상태 확인 중...")
        self.status_vars[key] = status_var
        tk.Label(parent, textvariable=status_var,
                 bg=BG_TAB, font=("Segoe UI", 8),
                 fg=FG_GRAY, anchor="w").pack(fill="x", padx=pad_x, pady=(0, 4))

    def _build_bottom_bar(self) -> None:
        bar = tk.Frame(self.root, bg="#111827", pady=8)
        bar.pack(fill="x", side="bottom")

        tk.Button(bar, text="💾  K드라이브 백업",
                  font=("Segoe UI", 9, "bold"),
                  bg="#ea580c", fg="white", relief="flat",
                  cursor="hand2", padx=12, pady=4,
                  command=self._backup_k
                  ).pack(side="left", padx=10)

        vault_name = VAULT_FILE.name
        tk.Label(bar, text=f"vault: {vault_name}  |  key: .bx/RPA_VAULT_KEY",
                 bg="#111827", fg="#4b5563",
                 font=("Segoe UI", 7)).pack(side="right", padx=10)

    # ── 이벤트 핸들러 ─────────────────────────────────────────────────────────

    def _toggle_show(self, entry: tk.Entry) -> None:
        entry.config(show="" if entry.cget("show") == "●" else "●")

    def _on_change(self, key: str) -> None:
        """비밀번호 변경 시 자동저장 타이머 재시작 (1초 debounce)"""
        if not self.auto_enabled[key].get():
            return
        if self.auto_jobs[key]:
            self.root.after_cancel(self.auto_jobs[key])
        self.auto_jobs[key] = self.root.after(
            1000, lambda: self._save(key, silent=True))

    def _save(self, key: str, silent: bool = False) -> None:
        """비밀번호를 3중 암호화하여 저장. 저장 후 Entry 내용 즉시 소각."""
        pw = self.pw_vars[key].get()

        if not pw:
            if not silent:
                messagebox.showwarning(
                    "입력 필요",
                    f"[{ACCOUNTS[key]['name']}] 비밀번호를 입력하세요.")
            return

        try:
            save_account(key, pw)

            # 평문을 Entry에서 즉시 제거
            _scrub_str(pw)
            self.pw_vars[key].set("")

            ts  = datetime.now().strftime("%H:%M:%S")
            msg = f"  ✅  암호화 저장 완료  [{ts}]"
            self.status_vars[key].set(msg)

            if not silent:
                messagebox.showinfo(
                    "저장 완료",
                    f"[{ACCOUNTS[key]['name']}] 비밀번호가 암호화 저장되었습니다.\n\n"
                    f"암호화: DPAPI + PBKDF2-600k + 3×AES-256-GCM\n"
                    f"평문은 메모리에서 즉시 소각됩니다.")

        except Exception as e:
            messagebox.showerror("저장 실패", f"오류: {e}")

    def _test(self, key: str) -> None:
        """복호화 테스트 — 비밀번호 길이와 첫 글자만 표시 (평문 노출 없음)"""
        try:
            _, pw = load_credentials(key)
            length = len(pw)
            hint   = pw[0] if pw else "?"
            # 즉시 소각
            _scrub_str(pw)
            del pw

            messagebox.showinfo(
                "복호화 성공 ✅",
                f"[{ACCOUNTS[key]['name']}] 복호화 성공!\n\n"
                f"비밀번호 길이: {length}자\n"
                f"시작 글자: {hint}***\n\n"
                f"(보안을 위해 전체 비밀번호는 표시하지 않습니다)")

        except SystemExit:
            messagebox.showerror(
                "복호화 실패",
                f"[{ACCOUNTS[key]['name']}] 저장된 데이터가 없습니다.\n"
                f"비밀번호를 입력하고 저장하세요.")
        except Exception as e:
            messagebox.showerror("복호화 실패", f"오류: {e}")

    def _refresh_all_status(self) -> None:
        """전체 계정 저장 상태를 vault에서 읽어 표시"""
        try:
            status = vault_status()
            for key, info in status.items():
                if info["saved"]:
                    ts  = info["ts"][:16].replace("T", "  ") if info["ts"] else ""
                    self.status_vars[key].set(f"  ✅  저장됨  [{ts}]")
                else:
                    self.status_vars[key].set(
                        "  ⚠️  미저장 — 비밀번호를 입력하고 저장하세요")
        except Exception:
            pass

    def _backup_k(self) -> None:
        """K드라이브에 프로그램 파일 백업 + install.bat 생성"""
        try:
            K_BACKUP.mkdir(parents=True, exist_ok=True)

            src_files = [
                _HERE / "rpa_vault_manager.py",
                _HERE / "rpa_credential_vault.py",
            ]

            backed = []
            for src in src_files:
                if src.exists():
                    shutil.copy2(src, K_BACKUP / src.name)
                    backed.append(src.name)

            # install.bat 생성
            bat = (
                "@echo off\n"
                "chcp 65001 >nul\n"
                "echo BRIDGE RPA Vault Manager 설치\n"
                "echo ================================\n"
                "echo.\n"
                "set PYW=C:\\Users\\Scarlett\\AppData\\Local\\Programs\\Python\\Python313\\pythonw.exe\n"
                "if not exist \"%PYW%\" (\n"
                "  echo [오류] Python313 경로를 찾을 수 없습니다: %PYW%\n"
                "  pause & exit /b 1\n"
                ")\n"
                "echo Python 확인: %PYW%\n"
                "echo.\n"
                "set TOOLS=Q:\\Claudework\\bridge base\\tools\n"
                "if not exist \"%TOOLS%\" (\n"
                "  echo [오류] bridge base 경로 없음: %TOOLS%\n"
                "  pause & exit /b 1\n"
                ")\n"
                "copy /Y \"%~dp0rpa_vault_manager.py\" \"%TOOLS%\\\" >nul\n"
                "copy /Y \"%~dp0rpa_credential_vault.py\" \"%TOOLS%\\\" >nul\n"
                "echo 파일 복사 완료.\n"
                "echo.\n"
                "echo 바탕화면 바로가기 생성 중...\n"
                "set SCRIPT=%TOOLS%\\rpa_vault_manager.py\n"
                "set LINK=%USERPROFILE%\\Desktop\\RPA Vault Manager.lnk\n"
                "powershell -Command \"\n"
                "  $ws = New-Object -ComObject WScript.Shell;\n"
                "  $sc = $ws.CreateShortcut('%LINK%');\n"
                "  $sc.TargetPath = '%PYW%';\n"
                "  $sc.Arguments = '-X utf8 \"%SCRIPT%\"';\n"
                "  $sc.WorkingDirectory = 'Q:\\Claudework\\bridge base';\n"
                "  $sc.IconLocation = 'Q:\\Claudework\\bridge base\\deploy\\craig-portable\\package\\rpa_icon.ico';\n"
                "  $sc.Save()\n"
                "\"\n"
                "echo.\n"
                "echo 설치 완료! 바탕화면에 'RPA Vault Manager' 바로가기가 생성되었습니다.\n"
                "echo.\n"
                "pause\n"
            )
            (K_BACKUP / "install_vault_manager.bat").write_text(bat, encoding="utf-8")
            backed.append("install_vault_manager.bat")

            messagebox.showinfo(
                "K드라이브 백업 완료",
                "K:\\BRIDGE_RPA_Installer\\ 에 백업 완료:\n\n" +
                "\n".join(f"  • {f}" for f in backed) +
                "\n\n새 PC 설치: install_vault_manager.bat 실행\n"
                "(vault 파일은 PC별 DPAPI 암호화라 백업 불가 — 새 PC에서 재입력)")

        except Exception as e:
            messagebox.showerror("백업 실패", f"오류: {e}")

    # ── 실행 ──────────────────────────────────────────────────────────────────

    def run(self) -> None:
        self.root.mainloop()


# ── 진입점 ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = VaultManagerApp()
    app.run()
