"""
main_gui.py — BRIDGE Resume Converter GUI
Tkinter + TkinterDnD2

레이아웃: 좌측(상태 내비) / 가운데(편집) / 우측(미리보기) — NotebookLM 3패널
"""

from __future__ import annotations

import io
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _DND_AVAILABLE = True
except ImportError:
    _DND_AVAILABLE = False
    TkinterDnD = tk.Tk

from PIL import Image, ImageTk

# ── 경로 설정 ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
INBOX_DIR    = BASE_DIR / "inbox"
OUTPUT_DIR   = BASE_DIR / "output"
LOGS_DIR     = BASE_DIR / "logs"
CONFIG_PATH  = BASE_DIR / "config.json"

# ── 색상 팔레트 (NotebookLM 스타일) ─────────────────────────────────────
C_BG         = "#FFFFFF"
C_SIDEBAR    = "#F8F9FA"
C_BORDER     = "#E8EAED"
C_PRIMARY    = "#1D9E75"
C_WARN       = "#EF9F27"
C_DANGER     = "#E24B4A"
C_TEXT       = "#202124"
C_SUBTEXT    = "#5F6368"
C_HOVER      = "#E8F5F0"

# ── 로거 ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("main_gui")


class BridgeConverterApp:
    """메인 GUI 앱."""

    def __init__(self):
        # DnD 지원 여부에 따라 루트 선택
        if _DND_AVAILABLE:
            self.root = TkinterDnD.Tk()
        else:
            self.root = tk.Tk()

        self.root.title("BRIDGE Resume Converter")
        self.root.geometry("1400x860")
        self.root.minsize(1000, 680)
        self.root.configure(bg=C_BG)

        # 상태
        self._mode        = tk.StringVar(value="반자동")
        self._candidate_id = tk.StringVar()
        self._files: dict[str, Path] = {}
        self._pii_result  = None
        self._current_step = 0
        self._steps        = ["파일 추가", "얼굴 크롭", "PII 제거", "PDF 생성", "저장"]
        self._sheet_connected = False
        self._pipeline_thread: Optional[threading.Thread] = None

        self._build_ui()
        self._check_sheet_connection()

    # ── UI 빌드 ───────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── 상단 툴바 ──────────────────────────────────────────────────
        toolbar = tk.Frame(self.root, bg=C_SIDEBAR, height=48,
                           relief="flat", bd=0,
                           highlightbackground=C_BORDER, highlightthickness=1)
        toolbar.pack(fill="x", side="top")
        toolbar.pack_propagate(False)

        logo = tk.Label(toolbar, text="  BRIDGE Converter",
                        font=("Helvetica", 16, "bold"),
                        fg=C_PRIMARY, bg=C_SIDEBAR)
        logo.pack(side="left", padx=12, pady=8)

        # 모드 토글
        mode_frame = tk.Frame(toolbar, bg=C_SIDEBAR)
        mode_frame.pack(side="left", padx=20)
        for m in ["자동", "반자동"]:
            rb = tk.Radiobutton(
                mode_frame, text=m, variable=self._mode, value=m,
                bg=C_SIDEBAR, fg=C_TEXT, selectcolor=C_SIDEBAR,
                font=("Helvetica", 12), activebackground=C_HOVER,
            )
            rb.pack(side="left", padx=4)

        # 구글시트 상태
        self._sheet_label = tk.Label(
            toolbar, text="● 시트 연결 확인 중...",
            font=("Helvetica", 11), fg=C_SUBTEXT, bg=C_SIDEBAR
        )
        self._sheet_label.pack(side="right", padx=16)

        # ── 3패널 메인 ──────────────────────────────────────────────────
        main_frame = tk.Frame(self.root, bg=C_BG)
        main_frame.pack(fill="both", expand=True)

        # 좌측 패널
        self._left_panel = self._build_left_panel(main_frame)
        self._left_panel.pack(side="left", fill="y", padx=0, pady=0)

        sep1 = tk.Frame(main_frame, width=1, bg=C_BORDER)
        sep1.pack(side="left", fill="y")

        # 가운데+우측 — PanedWindow (드래그로 폭 조절 가능)
        paned = ttk.PanedWindow(main_frame, orient="horizontal")
        paned.pack(side="left", fill="both", expand=True)

        self._center_panel = self._build_center_panel(paned)
        paned.add(self._center_panel, weight=3)

        self._right_panel = self._build_right_panel(paned)
        paned.add(self._right_panel, weight=1)

    # ── 좌측 패널 ────────────────────────────────────────────────────────
    def _build_left_panel(self, parent) -> tk.Frame:
        panel = tk.Frame(parent, bg=C_SIDEBAR, width=240)
        panel.pack_propagate(False)

        # 강사 카드
        card = tk.LabelFrame(panel, text="강사 정보", font=("Helvetica", 12, "bold"),
                              bg=C_SIDEBAR, fg=C_TEXT, padx=8, pady=6,
                              relief="flat", bd=1,
                              highlightbackground=C_BORDER, highlightthickness=1)
        card.pack(fill="x", padx=12, pady=(16, 8))

        tk.Label(card, text="강사 번호:", bg=C_SIDEBAR, fg=C_SUBTEXT,
                 font=("Helvetica", 11)).grid(row=0, column=0, sticky="w")
        id_entry = tk.Entry(card, textvariable=self._candidate_id,
                            font=("Helvetica", 11, "bold"), width=10,
                            relief="flat", bd=1,
                            highlightbackground=C_BORDER, highlightthickness=1)
        id_entry.grid(row=1, column=0, sticky="ew", pady=2)
        card.columnconfigure(0, weight=1)

        # 시트 불러오기
        load_btn = tk.Button(
            card, text="시트에서 불러오기",
            command=self._load_from_sheet,
            bg=C_PRIMARY, fg="white",
            font=("Helvetica", 11), relief="flat", padx=6, pady=3,
            cursor="hand2",
        )
        load_btn.grid(row=2, column=0, sticky="ew", pady=(6, 2))

        self._meta_label = tk.Label(card, text="",
                                     bg=C_SIDEBAR, fg=C_SUBTEXT,
                                     font=("Helvetica", 12), wraplength=200,
                                     justify="left")
        self._meta_label.grid(row=3, column=0, sticky="w")

        # 처리 단계 목록
        steps_frame = tk.LabelFrame(panel, text="처리 단계", font=("Helvetica", 12, "bold"),
                                     bg=C_SIDEBAR, fg=C_TEXT, padx=8, pady=6,
                                     relief="flat", bd=1,
                                     highlightbackground=C_BORDER, highlightthickness=1)
        steps_frame.pack(fill="x", padx=12, pady=8)

        self._step_dots = []
        for i, step in enumerate(self._steps):
            row_f = tk.Frame(steps_frame, bg=C_SIDEBAR)
            row_f.pack(fill="x", pady=2)
            dot = tk.Label(row_f, text="○", fg=C_BORDER, bg=C_SIDEBAR,
                           font=("Helvetica", 12))
            dot.pack(side="left")
            tk.Label(row_f, text=step, bg=C_SIDEBAR, fg=C_TEXT,
                     font=("Helvetica", 11)).pack(side="left", padx=4)
            self._step_dots.append(dot)

        # 전체 진행 바
        tk.Label(panel, text="전체 진행:", bg=C_SIDEBAR, fg=C_SUBTEXT,
                 font=("Helvetica", 11)).pack(padx=12, anchor="w", pady=(8, 2))
        self._progress = ttk.Progressbar(panel, length=200, mode="determinate",
                                          maximum=len(self._steps))
        self._progress.pack(padx=12, fill="x")

        # 미처리 목록 드롭다운
        tk.Label(panel, text="미처리 목록:", bg=C_SIDEBAR, fg=C_SUBTEXT,
                 font=("Helvetica", 11)).pack(padx=12, anchor="w", pady=(12, 2))
        self._unprocessed_var = tk.StringVar()
        self._unprocessed_combo = ttk.Combobox(
            panel, textvariable=self._unprocessed_var,
            font=("Helvetica", 11), state="readonly",
        )
        self._unprocessed_combo.pack(padx=12, fill="x")
        self._unprocessed_combo.bind("<<ComboboxSelected>>", self._on_select_unprocessed)

        tk.Button(panel, text="목록 새로고침", command=self._refresh_unprocessed,
                  bg=C_BG, fg=C_TEXT, font=("Helvetica", 12), relief="flat",
                  cursor="hand2").pack(padx=12, pady=4, fill="x")

        return panel

    # ── 가운데 패널 ──────────────────────────────────────────────────────
    def _build_center_panel(self, parent) -> tk.Frame:
        panel = tk.Frame(parent, bg=C_BG)

        # 드롭 영역
        drop_zone = tk.Frame(panel, bg=C_HOVER, height=80,
                              relief="flat", bd=2,
                              highlightbackground=C_PRIMARY, highlightthickness=1,
                              cursor="hand2")
        drop_zone.pack(fill="x", padx=16, pady=(16, 8))
        drop_zone.pack_propagate(False)

        drop_lbl = tk.Label(drop_zone,
                            text="파일을 드래그하거나 클릭하여 추가\n(사진 / 이력서 / 커버레터 / 추천서)",
                            bg=C_HOVER, fg=C_PRIMARY,
                            font=("Helvetica", 12), justify="center")
        drop_lbl.pack(expand=True)
        drop_zone.bind("<Button-1>", self._browse_files)
        drop_lbl.bind("<Button-1>", self._browse_files)

        # DnD 설정
        if _DND_AVAILABLE:
            drop_zone.drop_target_register(DND_FILES)
            drop_zone.dnd_bind("<<Drop>>", self._on_drop)

        # 파일 목록
        list_frame = tk.LabelFrame(panel, text="파일 목록", font=("Helvetica", 12, "bold"),
                                    bg=C_BG, fg=C_TEXT, padx=8, pady=6,
                                    relief="flat", highlightbackground=C_BORDER,
                                    highlightthickness=1)
        list_frame.pack(fill="x", padx=16, pady=4)

        self._file_listbox = tk.Listbox(list_frame, height=5,
                                         font=("Helvetica", 11),
                                         selectbackground=C_HOVER,
                                         relief="flat", bd=0)
        self._file_listbox.pack(fill="x")

        # PII 결과 텍스트뷰
        pii_frame = tk.LabelFrame(panel, text="PII 탐지 결과", font=("Helvetica", 12, "bold"),
                                   bg=C_BG, fg=C_TEXT, padx=8, pady=6,
                                   relief="flat", highlightbackground=C_BORDER,
                                   highlightthickness=1)
        pii_frame.pack(fill="both", expand=True, padx=16, pady=4)

        self._pii_text = scrolledtext.ScrolledText(
            pii_frame, font=("Courier", 11), height=5,
            bg="#FAFAFA", relief="flat",
            selectbackground=C_HOVER,
        )
        self._pii_text.pack(fill="both", expand=True)
        self._pii_text.tag_config("red",    foreground=C_DANGER,  background="#FEF2F2")
        self._pii_text.tag_config("yellow", foreground=C_WARN,    background="#FFFBEB")
        self._pii_text.tag_config("green",  foreground=C_PRIMARY, background="#F0FDF4")

        # 집중 점검 버튼
        self._focus_btn = tk.Button(
            pii_frame, text="선택 영역 집중 점검",
            command=self._focus_check,
            bg=C_WARN, fg="white",
            font=("Helvetica", 11), relief="flat", padx=8, pady=3,
            cursor="hand2", state="disabled",
        )
        self._focus_btn.pack(anchor="e", pady=4)
        self._pii_text.bind("<<Selection>>", self._on_text_select)

        # 하단 버튼
        btn_frame = tk.Frame(panel, bg=C_BG)
        btn_frame.pack(fill="x", padx=16, pady=8)

        self._prev_btn = tk.Button(btn_frame, text="◀ 이전",
                                    command=self._prev_step,
                                    bg=C_BORDER, fg=C_TEXT,
                                    font=("Helvetica", 11), relief="flat",
                                    padx=10, pady=5, cursor="hand2")
        self._prev_btn.pack(side="left")

        tk.Button(btn_frame, text="⏭ 건너뜀",
                  command=self._skip_step,
                  bg=C_BORDER, fg=C_TEXT,
                  font=("Helvetica", 11), relief="flat",
                  padx=10, pady=5, cursor="hand2").pack(side="left", padx=4)

        self._pause_btn = tk.Button(btn_frame, text="⏸ 일시정지",
                                     command=self._toggle_pause,
                                     bg=C_BORDER, fg=C_TEXT,
                                     font=("Helvetica", 11), relief="flat",
                                     padx=10, pady=5, cursor="hand2")
        self._pause_btn.pack(side="left", padx=4)

        self._next_btn = tk.Button(btn_frame, text="다음 단계 ▶",
                                    command=self._next_step,
                                    bg=C_PRIMARY, fg="white",
                                    font=("Helvetica", 12, "bold"), relief="flat",
                                    padx=12, pady=6, cursor="hand2")
        self._next_btn.pack(side="right")

        return panel

    # ── 우측 패널 ────────────────────────────────────────────────────────
    def _build_right_panel(self, parent) -> tk.Frame:
        panel = tk.Frame(parent, bg=C_SIDEBAR, width=280)
        panel.pack_propagate(False)

        # PDF 썸네일
        preview_frame = tk.LabelFrame(panel, text="PDF 미리보기", font=("Helvetica", 12, "bold"),
                                       bg=C_SIDEBAR, fg=C_TEXT, padx=8, pady=6,
                                       relief="flat", highlightbackground=C_BORDER,
                                       highlightthickness=1)
        preview_frame.pack(fill="x", padx=12, pady=16)

        self._preview_label = tk.Label(preview_frame, bg="#E0E0E0",
                                        width=28, height=14,
                                        text="미리보기\n없음", fg=C_SUBTEXT,
                                        font=("Helvetica", 11))
        self._preview_label.pack()

        # 메타 정보
        meta_frame = tk.LabelFrame(panel, text="파일 정보", font=("Helvetica", 12, "bold"),
                                    bg=C_SIDEBAR, fg=C_TEXT, padx=8, pady=6,
                                    relief="flat", highlightbackground=C_BORDER,
                                    highlightthickness=1)
        meta_frame.pack(fill="x", padx=12, pady=4)

        self._meta_info_labels = {}
        for key, label in [("size", "용량"), ("pages", "페이지"), ("pii_count", "삭제 항목")]:
            row = tk.Frame(meta_frame, bg=C_SIDEBAR)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"{label}:", bg=C_SIDEBAR, fg=C_SUBTEXT,
                     font=("Helvetica", 11), width=8, anchor="w").pack(side="left")
            lbl = tk.Label(row, text="—", bg=C_SIDEBAR, fg=C_TEXT,
                           font=("Helvetica", 11, "bold"))
            lbl.pack(side="left")
            self._meta_info_labels[key] = lbl

        # 파일명 미리보기
        fname_frame = tk.Frame(panel, bg=C_SIDEBAR)
        fname_frame.pack(fill="x", padx=12, pady=4)
        tk.Label(fname_frame, text="파일명:", bg=C_SIDEBAR, fg=C_SUBTEXT,
                 font=("Helvetica", 11)).pack(anchor="w")
        self._fname_label = tk.Label(fname_frame, text="—", bg=C_SIDEBAR,
                                      fg=C_TEXT, font=("Helvetica", 11, "bold"),
                                      wraplength=250, justify="left")
        self._fname_label.pack(anchor="w")

        # 중복 감지 알림 (노란 카드)
        self._dup_card = tk.Frame(panel, bg="#FFF8E1",
                                   highlightbackground=C_WARN, highlightthickness=1)
        # 숨김 상태로 시작
        self._dup_title  = tk.Label(self._dup_card, text="⚠ 중복 제출 감지",
                                     bg="#FFF8E1", fg=C_WARN,
                                     font=("Helvetica", 11, "bold"))
        self._dup_body   = tk.Label(self._dup_card, text="", bg="#FFF8E1",
                                     fg=C_TEXT, font=("Helvetica", 12),
                                     wraplength=240, justify="left")
        self._dup_btn    = tk.Button(self._dup_card, text="비교",
                                      bg=C_WARN, fg="white", font=("Helvetica", 12),
                                      relief="flat", padx=6, cursor="hand2")

        # 재지원 알림 (빨간 카드)
        self._reapp_card = tk.Frame(panel, bg="#FEF2F2",
                                     highlightbackground=C_DANGER, highlightthickness=1)
        self._reapp_title = tk.Label(self._reapp_card, text="🔴 재지원 감지",
                                      bg="#FEF2F2", fg=C_DANGER,
                                      font=("Helvetica", 11, "bold"))
        self._reapp_body  = tk.Label(self._reapp_card, text="", bg="#FEF2F2",
                                      fg=C_TEXT, font=("Helvetica", 12),
                                      wraplength=240, justify="left")

        btn_row = tk.Frame(self._reapp_card, bg="#FEF2F2")
        self._reapp_view_btn = tk.Button(btn_row, text="이전 파일 보기",
                                          bg=C_BG, fg=C_DANGER, font=("Helvetica", 12),
                                          relief="flat", padx=4, cursor="hand2")
        self._reapp_del_btn  = tk.Button(btn_row, text="삭제",
                                          bg=C_DANGER, fg="white", font=("Helvetica", 12),
                                          relief="flat", padx=4, cursor="hand2")
        self._reapp_keep_btn = tk.Button(btn_row, text="유지",
                                          bg=C_BG, fg=C_TEXT, font=("Helvetica", 12),
                                          relief="flat", padx=4, cursor="hand2")
        for b in [self._reapp_view_btn, self._reapp_del_btn, self._reapp_keep_btn]:
            b.pack(side="left", padx=2)

        return panel

    # ── 이벤트 핸들러 ─────────────────────────────────────────────────────

    def _browse_files(self, event=None):
        paths = filedialog.askopenfilenames(
            title="파일 선택",
            filetypes=[
                ("지원 파일", "*.pdf *.docx *.doc *.jpg *.jpeg *.png *.webp"),
                ("모든 파일", "*.*"),
            ]
        )
        if paths:
            self._add_files([Path(p) for p in paths])

    def _on_drop(self, event):
        if _DND_AVAILABLE:
            paths = self.root.tk.splitlist(event.data)
            self._add_files([Path(p) for p in paths])

    def _add_files(self, paths: list[Path]):
        from .file_classifier import detect_file_type
        for p in paths:
            if not p.exists():
                continue
            ftype = detect_file_type(p)
            self._files[ftype] = p
            self._file_listbox.insert("end", f"[{ftype}] {p.name}")
        self._update_filename_preview()

    def _load_from_sheet(self):
        cid = self._candidate_id.get().strip()
        if not cid:
            messagebox.showwarning("입력 필요", "강사 번호를 입력하세요.")
            return
        try:
            from .sheets_connector import get_candidate_info
            info = get_candidate_info(cid)
            if info:
                self._meta_label.config(
                    text=f"국적: {info.get('nationality', '?')} | "
                         f"성별: {info.get('gender', '?')} | "
                         f"생년: {info.get('birth_year', '?')}"
                )
                self._update_filename_preview(info)
            else:
                self._meta_label.config(text="번호를 찾을 수 없음")
        except Exception as e:
            self._meta_label.config(text=f"조회 실패: {e}")

    def _on_select_unprocessed(self, event=None):
        val = self._unprocessed_var.get()
        if val:
            cid = val.split("|")[0].strip()
            self._candidate_id.set(cid)
            self._load_from_sheet()

    def _refresh_unprocessed(self):
        try:
            from .sheets_connector import get_unprocessed_rows
            rows = get_unprocessed_rows(20)
            values = [f"{r['id']} | {r['name']}" for r in rows]
            self._unprocessed_combo["values"] = values
        except Exception as e:
            log.warning(f"미처리 목록 갱신 실패: {e}")

    def _check_sheet_connection(self):
        def _check():
            try:
                from .sheets_connector import is_connected
                ok = is_connected()
            except Exception:
                ok = False
            color = C_PRIMARY if ok else C_DANGER
            text  = "● 시트 연결됨" if ok else "● 시트 미연결"
            self.root.after(0, lambda: self._sheet_label.config(text=text, fg=color))

        threading.Thread(target=_check, daemon=True).start()

    def _focus_check(self):
        sel_text = ""
        try:
            sel_text = self._pii_text.get("sel.first", "sel.last")
        except tk.TclError:
            pass
        if not sel_text.strip():
            messagebox.showinfo("집중 점검", "텍스트를 먼저 선택하세요.")
            return
        from .pii_engine import analyze_pii_focus, load_api_key
        api_key = load_api_key()
        if not api_key:
            messagebox.showwarning("API 키 없음", "Anthropic API 키가 필요합니다.")
            return
        result = analyze_pii_focus(sel_text, api_key)
        self._show_pii_result(result)

    def _on_text_select(self, event=None):
        try:
            sel = self._pii_text.get("sel.first", "sel.last")
            state = "normal" if sel.strip() else "disabled"
        except tk.TclError:
            state = "disabled"
        self._focus_btn.config(state=state)

    def _next_step(self):
        if self._current_step < len(self._steps) - 1:
            self._current_step += 1
            self._update_step_ui()
            self._run_current_step()
        else:
            self._finish()

    def _prev_step(self):
        if self._current_step > 0:
            self._current_step -= 1
            self._update_step_ui()

    def _skip_step(self):
        self._next_step()

    def _toggle_pause(self):
        pass  # 파이프라인 일시정지 — 추후 구현

    def _run_current_step(self):
        """현재 단계에 맞는 처리 실행."""
        step = self._current_step
        if step == 1:
            self._run_face_crop()
        elif step == 2:
            self._run_pii()
        elif step == 3:
            self._run_build_pdf()
        elif step == 4:
            self._run_save()

    def _run_face_crop(self):
        from .face_crop import crop_face, FaceNotFoundError
        photo = self._files.get("photo")
        if not photo:
            return
        try:
            data = crop_face(photo)
            img  = Image.open(io.BytesIO(data)).resize((150, 200), Image.LANCZOS)
            tk_img = ImageTk.PhotoImage(img)
            self._preview_label.configure(image=tk_img, text="")
            self._preview_label.image = tk_img
        except FaceNotFoundError:
            messagebox.showwarning("얼굴 미감지", "얼굴을 찾지 못했습니다. 수동 영역 선택이 필요합니다.")

    def _run_pii(self):
        from .pii_engine import analyze_pii, load_api_key
        api_key = load_api_key()
        all_text = ""
        for ftype in ["cover", "resume", "rec"]:
            p = self._files.get(ftype)
            if p:
                from .pipeline import _extract_text
                all_text += f"\n=== {ftype.upper()} ===\n{_extract_text(p)}\n"

        if not all_text.strip():
            return

        result = analyze_pii(all_text, api_key)
        self._pii_result = result
        self._show_pii_result(result)

    def _show_pii_result(self, result):
        self._pii_text.config(state="normal")
        self._pii_text.delete("1.0", "end")

        text = result.cleaned_text
        self._pii_text.insert("end", text)

        # 색상 하이라이트 (삭제된 자리에 태그 표시)
        for item in result.pii_found:
            tag = item.color
            placeholder = f"[{item.type.upper()}_REMOVED]"
            start = text.find(placeholder)
            if start >= 0:
                s = f"1.0+{start}c"
                e = f"1.0+{start + len(placeholder)}c"
                self._pii_text.tag_add(tag, s, e)

        # 불확실 항목 노란 표시
        for u in result.uncertain:
            ut = u.get("text", "")
            if ut in text:
                start = text.find(ut)
                s = f"1.0+{start}c"
                e = f"1.0+{start + len(ut)}c"
                self._pii_text.tag_add("yellow", s, e)

        self._pii_text.config(state="disabled")

        # 메타 업데이트
        self._meta_info_labels["pii_count"].config(text=str(len(result.pii_found)))

    def _run_build_pdf(self):
        cid = self._candidate_id.get().strip() or "0000"
        from .pdf_builder import build_pdf
        out, size = build_pdf(
            candidate_id = cid,
            photo_bytes  = None,
            cover_text   = self._pii_result.cleaned_text if self._pii_result else None,
            out_dir      = OUTPUT_DIR,
        )
        self._meta_info_labels["size"].config(text=f"{size//1024}KB")
        self._fname_label.config(text=out.name)

    def _run_save(self):
        messagebox.showinfo("저장 완료", "PDF 변환이 완료되었습니다.")

    def _finish(self):
        messagebox.showinfo("완료", "모든 단계가 완료되었습니다.")
        self._current_step = 0
        self._update_step_ui()

    def _update_step_ui(self):
        for i, dot in enumerate(self._step_dots):
            if i < self._current_step:
                dot.config(text="✓", fg=C_PRIMARY)
            elif i == self._current_step:
                dot.config(text="●", fg=C_WARN)
            else:
                dot.config(text="○", fg=C_BORDER)
        self._progress["value"] = self._current_step

    def _update_filename_preview(self, info: dict | None = None):
        cid = self._candidate_id.get().strip() or "?"
        nat = info.get("nationality", "") if info else ""
        gen = info.get("gender", "") if info else ""
        yr  = info.get("birth_year", "") if info else ""
        from .pdf_builder import build_filename
        self._fname_label.config(text=build_filename(cid, nat, gen, yr))

    def show_duplicate_alert(self, candidate_id: str, old_path: Path, new_path: Path):
        self._dup_body.config(text=f"이전: {old_path.name}\n{candidate_id}번 7일 내 재제출 감지")
        for w in [self._dup_title, self._dup_body, self._dup_btn]:
            w.pack(anchor="w", padx=8, pady=2)
        self._dup_card.pack(fill="x", padx=12, pady=4)

    def show_reapply_alert(self, candidate_id: str, old_path: Path):
        self._reapp_body.config(text=f"이전 지원: {old_path.name}")
        for w in [self._reapp_title, self._reapp_body]:
            w.pack(anchor="w", padx=8, pady=2)

        btn_row = self._reapp_view_btn.master
        btn_row.pack(anchor="w", padx=8, pady=4)

        self._reapp_view_btn.config(command=lambda: os.startfile(str(old_path.parent)))
        self._reapp_del_btn.config(
            command=lambda: self._confirm_delete_old(old_path)
        )
        self._reapp_keep_btn.config(command=lambda: self._reapp_card.pack_forget())
        self._reapp_card.pack(fill="x", padx=12, pady=4)

    def _confirm_delete_old(self, old_path: Path):
        ok = messagebox.askyesno(
            "이전 파일 삭제",
            f"이전 파일을 originals\\로 이동 후 삭제합니다.\n\n{old_path}\n\n복구 불가합니다. 계속하시겠습니까?",
        )
        if ok:
            from .security import secure_delete
            dest = BASE_DIR / "originals" / old_path.name
            dest.parent.mkdir(exist_ok=True)
            import shutil
            shutil.move(str(old_path), str(dest))
            from .security import encrypt_file
            encrypt_file(dest)
            secure_delete(dest)
            self._reapp_card.pack_forget()
            messagebox.showinfo("삭제 완료", "이전 파일이 삭제되었습니다.")

    def run(self):
        self.root.mainloop()


# ── 진입점 ────────────────────────────────────────────────────────────────
def main():
    app = BridgeConverterApp()
    app.run()

if __name__ == "__main__":
    main()
