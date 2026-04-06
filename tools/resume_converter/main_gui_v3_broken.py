"""
main_gui.py -- BRIDGE Resume Converter GUI  v3.0
Multi-Bundle: 여러 강사 동시 처리 + 드래그앤드롭 + 자동분류

[RULE-TKINTER] 위젯 텍스트에 이모지 사용 금지 (GDI deadlock)
"""

from __future__ import annotations

import logging
import os
import shutil
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _DND_AVAILABLE = True
except ImportError:
    _DND_AVAILABLE = False
    TkinterDnD = tk.Tk  # type: ignore[misc,assignment]

# -- Core engine imports (변경 금지) --
from .file_classifier import detect_file_type
from .pipeline import Pipeline, PipelineJob

# -- 경로 --
BASE_DIR   = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR   = BASE_DIR / "logs"
OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# -- 폰트 (맑은 고딕, Tkinter 안전 텍스트만) --
F  = "맑은 고딕"
FM = "Consolas"

# -- 색상 --
C_BG     = "#FFFFFF"
C_SIDE   = "#F8F9FA"
C_BORDER = "#E0E0E0"
C_PRI    = "#1D9E75"
C_WARN   = "#EF9F27"
C_DANGER = "#E24B4A"
C_TEXT   = "#202124"
C_SUB    = "#5F6368"
C_HOVER  = "#E8F5F0"

C_WAIT   = "#FFF9C4"
C_PROC   = "#BBDEFB"
C_DONE   = "#C8E6C9"
C_ERR    = "#FFCDD2"

FILE_TYPES = ["photo", "resume", "cover", "recommendation"]
FILE_TYPE_LABELS = {"photo": "사진", "resume": "이력서", "cover": "커버레터", "recommendation": "추천서"}

NATIONALITIES = [
    "", "미국", "영국", "캐나다", "호주", "뉴질랜드", "아일랜드", "남아공",
    "인도", "필리핀", "기타",
]
GENDERS = ["", "남성", "여성", "기타"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("main_gui")


# ============================================================
# Data classes
# ============================================================

@dataclass
class FileEntry:
    path: Path
    file_type: str  # photo/resume/cover/recommendation/unknown
    original_name: str = ""

    def __post_init__(self):
        self.original_name = self.path.name


@dataclass
class Bundle:
    """강사 1인 분량 파일 묶음."""
    bundle_id: int
    candidate_id: str = ""
    nationality: str = ""
    gender: str = ""
    birth_year: str = ""
    files: list[FileEntry] = field(default_factory=list)
    status: str = "대기"        # 대기 / 변환중 / 완료 / 오류
    progress: str = ""
    error: str = ""
    output_path: Optional[Path] = None


# ============================================================
# Bundle Card Widget
# ============================================================

class BundleCard(tk.Frame):
    """한 강사 묶음을 표시하는 카드 위젯."""

    def __init__(self, parent, bundle: Bundle, on_remove, on_add_files, **kw):
        super().__init__(parent, **kw)
        self.bundle = bundle
        self.on_remove = on_remove
        self.on_add_files = on_add_files
        self.configure(bg=C_BG, bd=1, relief="solid", highlightbackground=C_BORDER)

        self._build_ui()
        self._update_status_color()

    def _build_ui(self):
        b = self.bundle

        # -- Header row --
        hdr = tk.Frame(self, bg=C_BG)
        hdr.pack(fill="x", padx=8, pady=(6, 2))

        tk.Label(hdr, text=f"[{b.bundle_id}]", font=(F, 10, "bold"),
                 bg=C_BG, fg=C_PRI).pack(side="left")

        self.status_lbl = tk.Label(hdr, text=b.status, font=(F, 9),
                                   bg=C_BG, fg=C_SUB)
        self.status_lbl.pack(side="left", padx=(8, 0))

        tk.Button(hdr, text="X", font=(FM, 9, "bold"), fg=C_DANGER,
                  bg=C_BG, bd=0, cursor="hand2",
                  command=lambda: self.on_remove(b.bundle_id)).pack(side="right")

        # -- Info row --
        info = tk.Frame(self, bg=C_BG)
        info.pack(fill="x", padx=8, pady=2)

        tk.Label(info, text="번호:", font=(F, 9), bg=C_BG).grid(row=0, column=0, sticky="e")
        self.id_var = tk.StringVar(value=b.candidate_id)
        tk.Entry(info, textvariable=self.id_var, width=8, font=(FM, 9)).grid(row=0, column=1, padx=2)

        tk.Label(info, text="국적:", font=(F, 9), bg=C_BG).grid(row=0, column=2, sticky="e", padx=(6, 0))
        self.nat_var = tk.StringVar(value=b.nationality)
        ttk.Combobox(info, textvariable=self.nat_var, values=NATIONALITIES,
                     width=6, font=(F, 9), state="readonly").grid(row=0, column=3, padx=2)

        tk.Label(info, text="성별:", font=(F, 9), bg=C_BG).grid(row=0, column=4, sticky="e", padx=(6, 0))
        self.gen_var = tk.StringVar(value=b.gender)
        ttk.Combobox(info, textvariable=self.gen_var, values=GENDERS,
                     width=4, font=(F, 9), state="readonly").grid(row=0, column=5, padx=2)

        tk.Label(info, text="출생:", font=(F, 9), bg=C_BG).grid(row=0, column=6, sticky="e", padx=(6, 0))
        self.birth_var = tk.StringVar(value=b.birth_year)
        tk.Entry(info, textvariable=self.birth_var, width=4, font=(FM, 9)).grid(row=0, column=7, padx=2)

        # -- File list --
        file_frame = tk.Frame(self, bg=C_BG)
        file_frame.pack(fill="x", padx=8, pady=2)

        self.file_widgets: list[dict] = []
        self._rebuild_file_list(file_frame)

        # -- Drop zone / Add button --
        btn_frame = tk.Frame(self, bg=C_BG)
        btn_frame.pack(fill="x", padx=8, pady=(2, 6))

        self.drop_label = tk.Label(
            btn_frame, text="-- 여기에 파일 드래그 또는 [파일 추가] 클릭 --",
            font=(F, 8), fg=C_SUB, bg="#F5F5F5", relief="groove", height=1,
            cursor="hand2",
        )
        self.drop_label.pack(fill="x", pady=2)
        self.drop_label.bind("<Button-1>", lambda e: self.on_add_files(b.bundle_id))

        # Enable DnD on the drop label
        if _DND_AVAILABLE:
            try:
                self.drop_label.drop_target_register(DND_FILES)
                self.drop_label.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                pass

        # -- Progress --
        self.progress_lbl = tk.Label(self, text="", font=(F, 8), bg=C_BG, fg=C_SUB)
        self.progress_lbl.pack(fill="x", padx=8)

    def _rebuild_file_list(self, parent=None):
        if parent is None:
            parent = self.file_widgets[0]["frame"].master if self.file_widgets else self
        # Clear old
        for w in self.file_widgets:
            w["frame"].destroy()
        self.file_widgets.clear()

        for i, fe in enumerate(self.bundle.files):
            row = tk.Frame(parent, bg=C_BG)
            row.pack(fill="x", pady=1)

            type_var = tk.StringVar(value=fe.file_type)
            cb = ttk.Combobox(row, textvariable=type_var, values=FILE_TYPES,
                              width=10, font=(F, 8), state="readonly")
            cb.pack(side="left", padx=(0, 4))
            cb.bind("<<ComboboxSelected>>", lambda e, idx=i, v=type_var: self._change_type(idx, v.get()))

            lbl = tk.Label(row, text=fe.original_name, font=(F, 8), bg=C_BG,
                           fg=C_TEXT, anchor="w")
            lbl.pack(side="left", fill="x", expand=True)

            tk.Button(row, text="Del", font=(FM, 7), fg=C_DANGER, bg=C_BG, bd=0,
                      command=lambda idx=i: self._remove_file(idx)).pack(side="right")

            self.file_widgets.append({"frame": row, "type_var": type_var, "label": lbl})

    def _change_type(self, idx: int, new_type: str):
        if idx < len(self.bundle.files):
            self.bundle.files[idx].file_type = new_type

    def _remove_file(self, idx: int):
        if idx < len(self.bundle.files):
            self.bundle.files.pop(idx)
            parent = self.file_widgets[0]["frame"].master if self.file_widgets else None
            if parent:
                self._rebuild_file_list(parent)

    def _on_drop(self, event):
        """DnD drop handler."""
        raw = event.data
        # Parse TkDnD file list (handles {braces} for paths with spaces)
        paths = []
        in_brace = False
        current = []
        for ch in raw:
            if ch == '{':
                in_brace = True
                continue
            if ch == '}':
                in_brace = False
                paths.append("".join(current))
                current = []
                continue
            if ch == ' ' and not in_brace:
                if current:
                    paths.append("".join(current))
                    current = []
                continue
            current.append(ch)
        if current:
            paths.append("".join(current))

        for p_str in paths:
            p = Path(p_str)
            if p.is_file():
                ftype = detect_file_type(p)
                self.bundle.files.append(FileEntry(path=p, file_type=ftype))

        parent = self.file_widgets[0]["frame"].master if self.file_widgets else None
        if parent:
            self._rebuild_file_list(parent)

    def sync_to_bundle(self):
        """UI 입력값을 Bundle 객체에 반영."""
        self.bundle.candidate_id = self.id_var.get().strip()
        self.bundle.nationality = self.nat_var.get().strip()
        self.bundle.gender = self.gen_var.get().strip()
        self.bundle.birth_year = self.birth_var.get().strip()

    def update_display(self):
        """Bundle 상태를 UI에 반영."""
        self.status_lbl.config(text=self.bundle.status)
        self.progress_lbl.config(text=self.bundle.progress)
        self._update_status_color()

    def _update_status_color(self):
        colors = {"대기": C_WAIT, "변환중": C_PROC, "완료": C_DONE, "오류": C_ERR}
        c = colors.get(self.bundle.status, C_BG)
        self.configure(highlightbackground=c)


# ============================================================
# Main Application
# ============================================================

class BridgeConverterApp:
    """BRIDGE Resume Converter v3.0 -- Multi-Bundle GUI."""

    def __init__(self):
        if _DND_AVAILABLE:
            self.root = TkinterDnD.Tk()
        else:
            self.root = tk.Tk()

        self.root.title("BRIDGE Resume Converter v3.0")
        self.root.geometry("900x700")
        self.root.configure(bg=C_BG)
        self.root.minsize(700, 500)

        self.bundles: list[Bundle] = []
        self.cards: dict[int, BundleCard] = {}
        self._next_id = 1
        self._running = False

        self._build_ui()
        self._log("BRIDGE Resume Converter v3.0 시작")
        if not _DND_AVAILABLE:
            self._log("[주의] tkinterdnd2 미설치 -- 드래그앤드롭 비활성")

    def _build_ui(self):
        # -- Top toolbar --
        toolbar = tk.Frame(self.root, bg=C_SIDE, height=42)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text="BRIDGE Converter", font=(F, 12, "bold"),
                 bg=C_SIDE, fg=C_PRI).pack(side="left", padx=12)

        tk.Button(toolbar, text="[+ 묶음 추가]", font=(F, 10, "bold"),
                  bg=C_PRI, fg="white", bd=0, padx=12, pady=4,
                  cursor="hand2", command=self._add_bundle).pack(side="left", padx=8)

        self.run_btn = tk.Button(toolbar, text="[전체 변환]", font=(F, 10, "bold"),
                                 bg="#1976D2", fg="white", bd=0, padx=12, pady=4,
                                 cursor="hand2", command=self._start_all)
        self.run_btn.pack(side="left", padx=4)

        tk.Button(toolbar, text="[출력 폴더]", font=(F, 9),
                  bg=C_SIDE, fg=C_TEXT, bd=1, padx=8,
                  command=lambda: os.startfile(str(OUTPUT_DIR))).pack(side="right", padx=8)

        # -- Main paned --
        paned = tk.PanedWindow(self.root, orient="vertical", bg=C_BORDER, sashwidth=4)
        paned.pack(fill="both", expand=True, padx=8, pady=4)

        # -- Bundle area (scrollable) --
        bundle_container = tk.Frame(paned, bg=C_BG)
        paned.add(bundle_container, minsize=200)

        canvas = tk.Canvas(bundle_container, bg=C_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(bundle_container, orient="vertical", command=canvas.yview)
        self.bundle_frame = tk.Frame(canvas, bg=C_BG)

        self.bundle_frame.bind("<Configure>",
                               lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.bundle_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # Mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # -- Log area --
        log_frame = tk.Frame(paned, bg=C_BG)
        paned.add(log_frame, minsize=100)

        tk.Label(log_frame, text="-- 로그 --", font=(F, 9, "bold"),
                 bg=C_BG, fg=C_SUB, anchor="w").pack(fill="x", padx=4)
        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=8, font=(FM, 9), bg="#FAFAFA",
            fg=C_TEXT, wrap="word", state="disabled",
        )
        self.log_text.pack(fill="both", expand=True, padx=4, pady=2)

    # -- Bundle management --

    def _add_bundle(self):
        bid = self._next_id
        self._next_id += 1
        bundle = Bundle(bundle_id=bid)
        self.bundles.append(bundle)

        card = BundleCard(
            self.bundle_frame, bundle,
            on_remove=self._remove_bundle,
            on_add_files=self._browse_for_bundle,
        )
        card.pack(fill="x", padx=4, pady=4)
        self.cards[bid] = card

        self._log(f"묶음 #{bid} 추가됨")

    def _remove_bundle(self, bundle_id: int):
        if self._running:
            messagebox.showwarning("경고", "변환 중에는 삭제할 수 없습니다")
            return
        self.bundles = [b for b in self.bundles if b.bundle_id != bundle_id]
        card = self.cards.pop(bundle_id, None)
        if card:
            card.destroy()
        self._log(f"묶음 #{bundle_id} 제거됨")

    def _browse_for_bundle(self, bundle_id: int):
        paths = filedialog.askopenfilenames(
            title=f"묶음 #{bundle_id}에 파일 추가",
            filetypes=[
                ("모든 파일", "*.*"),
                ("이미지", "*.jpg *.jpeg *.png *.webp *.heic *.bmp"),
                ("문서", "*.pdf *.docx *.doc"),
            ],
        )
        if not paths:
            return

        bundle = next((b for b in self.bundles if b.bundle_id == bundle_id), None)
        if not bundle:
            return

        for p_str in paths:
            p = Path(p_str)
            if p.is_file():
                ftype = detect_file_type(p)
                bundle.files.append(FileEntry(path=p, file_type=ftype))
                self._log(f"  #{bundle_id}: {p.name} -> {ftype}")

        card = self.cards.get(bundle_id)
        if card:
            parent = card.file_widgets[0]["frame"].master if card.file_widgets else None
            if parent:
                card._rebuild_file_list(parent)

    # -- Conversion --

    def _start_all(self):
        if self._running:
            messagebox.showinfo("안내", "이미 변환 중입니다")
            return
        if not self.bundles:
            messagebox.showwarning("경고", "묶음이 없습니다. [+ 묶음 추가]를 클릭하세요")
            return

        # Sync all cards
        for card in self.cards.values():
            card.sync_to_bundle()

        # Validate
        for b in self.bundles:
            if not b.candidate_id:
                messagebox.showwarning("경고", f"묶음 #{b.bundle_id}: 강사 번호를 입력하세요")
                return
            if not b.files:
                messagebox.showwarning("경고", f"묶음 #{b.bundle_id}: 파일이 없습니다")
                return

        self._running = True
        self.run_btn.config(state="disabled", text="[변환중...]")
        threading.Thread(target=self._run_all, daemon=True).start()

    def _run_all(self):
        """모든 묶음을 순차 변환 (백그라운드 스레드)."""
        for bundle in self.bundles:
            if bundle.status == "완료":
                continue
            self._run_one(bundle)

        self._running = False
        self.root.after(0, lambda: self.run_btn.config(state="normal", text="[전체 변환]"))
        self._log("=" * 40)
        done = sum(1 for b in self.bundles if b.status == "완료")
        errs = sum(1 for b in self.bundles if b.status == "오류")
        self._log(f"전체 완료: {done}건 성공, {errs}건 오류")

    def _run_one(self, bundle: Bundle):
        """단일 묶음 변환."""
        bundle.status = "변환중"
        bundle.progress = "준비 중..."
        self._update_card(bundle.bundle_id)
        self._log(f"--- 묶음 #{bundle.bundle_id} ({bundle.candidate_id}) 시작 ---")

        try:
            import tempfile

            with tempfile.TemporaryDirectory(prefix=f"brconv_{bundle.candidate_id}_") as tmpdir:
                tmpdir_path = Path(tmpdir)
                pipe_folder = tmpdir_path / "input"
                pipe_folder.mkdir()

                # Copy files to temp folder
                for fe in bundle.files:
                    dst = pipe_folder / fe.path.name
                    shutil.copy2(str(fe.path), str(dst))

                # Pipeline
                def on_progress(msg: str):
                    bundle.progress = msg
                    self._update_card(bundle.bundle_id)
                    self._log(f"  #{bundle.bundle_id}: {msg}")

                pipe = Pipeline(
                    auto_mode=True,
                    on_progress=on_progress,
                )

                job: PipelineJob = pipe.run(bundle.candidate_id, pipe_folder)

                # Check result
                if job.errors:
                    bundle.status = "오류"
                    bundle.error = "; ".join(job.errors)
                    bundle.progress = f"오류: {bundle.error}"
                    self._log(f"  #{bundle.bundle_id} 오류: {bundle.error}")
                elif job.output_path and job.output_path.exists():
                    # Copy to output dir
                    final_name = job.output_path.name
                    final_dst = OUTPUT_DIR / final_name
                    shutil.copy2(str(job.output_path), str(final_dst))
                    bundle.output_path = final_dst
                    bundle.status = "완료"
                    bundle.progress = f"완료: {final_name} ({final_dst.stat().st_size // 1024}KB)"
                    self._log(f"  #{bundle.bundle_id} 완료: {final_dst}")
                else:
                    bundle.status = "오류"
                    bundle.progress = "출력 파일 없음"
                    self._log(f"  #{bundle.bundle_id} 출력 파일 없음")

        except Exception as e:
            bundle.status = "오류"
            bundle.error = str(e)
            bundle.progress = f"오류: {e}"
            self._log(f"  #{bundle.bundle_id} 예외: {e}")
            log.exception(f"Bundle #{bundle.bundle_id} failed")

        self._update_card(bundle.bundle_id)

    # -- UI helpers --

    def _update_card(self, bundle_id: int):
        card = self.cards.get(bundle_id)
        if card:
            self.root.after(0, card.update_display)

    def _log(self, msg: str):
        def _append():
            self.log_text.config(state="normal")
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.root.after(0, _append)

    def run(self):
        self.root.mainloop()


# ============================================================
# Entry point
# ============================================================

def main():
    app = BridgeConverterApp()
    app.run()


if __name__ == "__main__":
    main()
