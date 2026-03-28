"""
main_gui.py — BRIDGE Resume Converter GUI  v2.0
Tkinter + TkinterDnD2

레이아웃: 좌측(대기열+내비) / 가운데(편집+파일목록) / 우측(미리보기)
"""

from __future__ import annotations

import io
import logging
import os
import threading
import time
import webbrowser
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
    TkinterDnD = tk.Tk

from PIL import Image, ImageTk

# ── 경로 설정 ─────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
INBOX_DIR  = BASE_DIR / "inbox"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR   = BASE_DIR / "logs"
CONFIG_PATH= BASE_DIR / "config.json"

# ── 폰트 (맑은 고딕 — Windows Korean 시스템 폰트) ─────────────────────────
F  = "맑은 고딕"   # Malgun Gothic
FM = "Consolas"    # monospace

# ── 색상 팔레트 ───────────────────────────────────────────────────────────
C_BG     = "#FFFFFF"
C_SIDE   = "#F8F9FA"
C_BORDER = "#E8EAED"
C_PRI    = "#1D9E75"
C_WARN   = "#EF9F27"
C_DANGER = "#E24B4A"
C_TEXT   = "#202124"
C_SUB    = "#5F6368"
C_HOVER  = "#E8F5F0"
C_PAUSE  = "#FFCDD2"   # 옅은 붉은 (일시정지)
C_STOP   = "#E53935"   # 강제중지

# 대기열 행 색
C_QWAIT  = "#FFF9C4"
C_QACT   = "#E8F5E9"
C_QDONE  = "#F1F8E9"
C_QERR   = "#FFEBEE"

# ── 단계 정의 ─────────────────────────────────────────────────────────────
STEPS = ["파일 확인", "사진 크롭", "PII 제거", "PDF 생성", "저장"]
STEP_ACTIONS = [
    "파일 목록 확인 중",
    "얼굴 감지 & 크롭 중",
    "개인정보 탐지 & 제거 중",
    "이력서 PDF 합치는 중",
    "파일 저장 중",
]

QUEUE_MAX = 5
HOMEPAGE  = "https://www.bridgejob.co.kr"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("main_gui")


@dataclass
class QueueItem:
    """대기열 항목 — 강사 1인 분량의 파일 묶음."""
    queue_id:    str
    candidate_id: str = ""
    files:       dict = field(default_factory=dict)
    status:      str  = "대기"     # 대기 | 처리중 | 완료 | 오류
    error:       str  = ""
    info:        dict = field(default_factory=dict)


class BridgeConverterApp:
    """메인 GUI 앱 v2.0."""

    def __init__(self):
        if _DND_AVAILABLE:
            self.root = TkinterDnD.Tk()
        else:
            self.root = tk.Tk()

        self.root.title("BRIDGE Converter")
        self.root.geometry("1440x900")
        self.root.minsize(1100, 700)
        self.root.configure(bg=C_BG)

        # ── 상태 ─────────────────────────────────────────────────────
        self._mode          = tk.StringVar(value="반자동")
        self._candidate_id  = tk.StringVar()
        self._files: dict[str, Path] = {}
        self._pii_result    = None
        self._current_step  = 0
        self._paused        = False
        self._stopped       = False
        self._pipeline_thread: Optional[threading.Thread] = None
        self._sheet_connected = False

        # 대기열
        self._queue: list[QueueItem] = []
        self._active_queue_id: Optional[str] = None
        self._queue_counter = 0

        # 애니메이션
        self._blink_base   = ""
        self._blink_dots   = 0
        self._blink_after: Optional[str] = None
        self._blink_error  = False   # True → 빨간 깜박

        # PII 패널 펼침 상태
        self._pii_expanded = False

        # 단계 실행 중 중복 방지
        self._step_running = False

        # 사진 크롭 결과 (bytes) — 단계 간 전달
        self._photo_bytes: Optional[bytes] = None

        # 파일목록 5개 고정 슬롯 (ftype → Treeview iid)
        self._file_slot_ids: dict[str, str] = {}

        self._build_ui()
        self._configure_styles()
        self._check_sheet_connection()

    # ══════════════════════════════════════════════════════════════════
    # UI 빌드
    # ══════════════════════════════════════════════════════════════════

    def _build_ui(self):
        # ── 툴바 ──────────────────────────────────────────────────
        bar = tk.Frame(self.root, bg=C_SIDE, height=52,
                       highlightbackground=C_BORDER, highlightthickness=1)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        tk.Label(bar, text="  BRIDGE Converter",
                 font=(F, 15, "bold"), fg=C_PRI, bg=C_SIDE
                 ).pack(side="left", padx=14, pady=10)

        # ── 모드 토글 (pill 버튼) ──────────────────────────────
        self._mode_btns: dict[str, tk.Button] = {}
        pill = tk.Frame(bar, bg=C_BORDER, highlightbackground=C_PRI, highlightthickness=1)
        pill.pack(side="left", padx=18, pady=13)
        for m in ["자동", "반자동"]:
            b = tk.Button(pill, text=m, font=(F, 11),
                          relief="flat", bd=0, padx=16, pady=3,
                          cursor="hand2", command=lambda x=m: self._set_mode(x))
            b.pack(side="left")
            self._mode_btns[m] = b
        self._update_mode_btns()

        # 홈페이지 버튼
        tk.Button(bar, text="홈페이지",
                  command=lambda: webbrowser.open(HOMEPAGE),
                  bg=C_SIDE, fg=C_PRI, font=(F, 11),
                  relief="flat", padx=8, cursor="hand2"
                  ).pack(side="left", padx=4)

        # 시트 상태 (우측)
        self._sheet_label = tk.Label(
            bar, text="● 시트 미연결",
            font=(F, 11), fg=C_DANGER, bg=C_SIDE)
        self._sheet_label.pack(side="right", padx=14)

        # ── 3패널 메인 ────────────────────────────────────────
        main = tk.Frame(self.root, bg=C_BG)
        main.pack(fill="both", expand=True)

        self._left_panel = self._build_left(main)
        self._left_panel.pack(side="left", fill="y")

        tk.Frame(main, width=1, bg=C_BORDER).pack(side="left", fill="y")

        paned = ttk.PanedWindow(main, orient="horizontal")
        paned.pack(side="left", fill="both", expand=True)

        self._center_panel = self._build_center(paned)
        paned.add(self._center_panel, weight=3)

        self._right_panel = self._build_right(paned)
        paned.add(self._right_panel, weight=1)

    # ── 좌측 패널 ─────────────────────────────────────────────────────
    def _build_left(self, parent) -> tk.Frame:
        panel = tk.Frame(parent, bg=C_SIDE, width=270)
        panel.pack_propagate(False)

        # 시트 연결하기
        tk.Button(panel, text="  시트 연결하기",
                  command=self._open_sheet_settings,
                  bg=C_PRI, fg="white",
                  font=(F, 11, "bold"), relief="flat",
                  padx=10, pady=5, cursor="hand2"
                  ).pack(fill="x", padx=12, pady=(12, 4))

        # ── 강사 카드 ──────────────────────────────────────────
        card = tk.LabelFrame(panel, text="강사 정보", font=(F, 11, "bold"),
                              bg=C_SIDE, fg=C_TEXT, padx=8, pady=6,
                              relief="flat",
                              highlightbackground=C_BORDER, highlightthickness=1)
        card.pack(fill="x", padx=12, pady=(0, 6))

        tk.Label(card, text="강사 번호:", bg=C_SIDE, fg=C_SUB,
                 font=(F, 10)).grid(row=0, column=0, sticky="w")

        vcmd = (panel.register(self._validate_id), "%P")
        self._id_entry = tk.Entry(
            card, textvariable=self._candidate_id,
            font=(F, 12, "bold"), width=10,
            validate="key", validatecommand=vcmd,
            relief="flat", bd=1,
            highlightbackground=C_BORDER, highlightthickness=1)
        self._id_entry.grid(row=1, column=0, sticky="ew", pady=2)
        card.columnconfigure(0, weight=1)

        tk.Button(card, text="시트에서 불러오기",
                  command=self._load_from_sheet,
                  bg=C_HOVER, fg=C_PRI,
                  font=(F, 10), relief="flat",
                  padx=6, pady=2, cursor="hand2"
                  ).grid(row=2, column=0, sticky="ew", pady=(4, 2))

        self._meta_label = tk.Label(
            card, text="", bg=C_SIDE, fg=C_SUB,
            font=(F, 10), wraplength=220, justify="left")
        self._meta_label.grid(row=3, column=0, sticky="w")

        # ── 대기열 ─────────────────────────────────────────────
        qf = tk.LabelFrame(panel, text=f"처리 대기열  (최대 {QUEUE_MAX}명)",
                            font=(F, 11, "bold"),
                            bg=C_SIDE, fg=C_TEXT, padx=6, pady=4,
                            relief="flat",
                            highlightbackground=C_BORDER, highlightthickness=1)
        qf.pack(fill="x", padx=12, pady=4)

        q_cols = ("번호", "강사ID", "파일", "상태")
        self._queue_tv = ttk.Treeview(qf, columns=q_cols,
                                       show="headings", height=5,
                                       selectmode="browse")
        self._queue_tv.heading("번호",   text="#")
        self._queue_tv.heading("강사ID", text="강사번호")
        self._queue_tv.heading("파일",   text="파일")
        self._queue_tv.heading("상태",   text="상태")
        self._queue_tv.column("번호",   width=28,  minwidth=26, anchor="center")
        self._queue_tv.column("강사ID", width=70,  minwidth=60, anchor="center")
        self._queue_tv.column("파일",   width=36,  minwidth=30, anchor="center")
        self._queue_tv.column("상태",   width=76,  minwidth=60, anchor="center")
        self._queue_tv.tag_configure("wait",   background=C_QWAIT)
        self._queue_tv.tag_configure("active", background=C_QACT)
        self._queue_tv.tag_configure("done",   background=C_QDONE)
        self._queue_tv.tag_configure("error",  background=C_QERR)
        self._queue_tv.pack(fill="x")

        qbr = tk.Frame(qf, bg=C_SIDE)
        qbr.pack(fill="x", pady=(4, 0))
        tk.Button(qbr, text="+ 추가",
                  command=self._queue_add,
                  bg=C_PRI, fg="white",
                  font=(F, 10), relief="flat",
                  padx=8, pady=2, cursor="hand2").pack(side="left")
        tk.Button(qbr, text="× 제거",
                  command=self._queue_remove,
                  bg=C_PAUSE, fg=C_DANGER,
                  font=(F, 10), relief="flat",
                  padx=8, pady=2, cursor="hand2").pack(side="left", padx=4)
        tk.Button(qbr, text="전체 시작",
                  command=self._queue_start,
                  bg=C_PRI, fg="white",
                  font=(F, 10, "bold"), relief="flat",
                  padx=8, pady=2, cursor="hand2").pack(side="right")

        # ── 처리 단계 ──────────────────────────────────────────
        sf = tk.LabelFrame(panel, text="처리 단계", font=(F, 11, "bold"),
                            bg=C_SIDE, fg=C_TEXT, padx=8, pady=4,
                            relief="flat",
                            highlightbackground=C_BORDER, highlightthickness=1)
        sf.pack(fill="x", padx=12, pady=4)

        self._step_rows: list[tuple[tk.Label, tk.Label]] = []
        for step in STEPS:
            rf = tk.Frame(sf, bg=C_SIDE)
            rf.pack(fill="x", pady=1)
            dot = tk.Label(rf, text="○", fg=C_BORDER, bg=C_SIDE, font=(F, 13))
            dot.pack(side="left")
            lbl = tk.Label(rf, text=step, bg=C_SIDE, fg=C_TEXT, font=(F, 11))
            lbl.pack(side="left", padx=4)
            self._step_rows.append((dot, lbl))

        # 현재 작업 깜박 표시
        self._status_var = tk.StringVar(value="")
        self._status_lbl = tk.Label(
            sf, textvariable=self._status_var,
            bg=C_SIDE, fg=C_WARN,
            font=(F, 10, "bold"), anchor="w", wraplength=220)
        self._status_lbl.pack(fill="x", pady=(4, 0))

        # 전체 진행 바
        tk.Label(panel, text="전체 진행:", bg=C_SIDE, fg=C_SUB,
                 font=(F, 10)).pack(padx=12, anchor="w", pady=(6, 1))
        self._progress = ttk.Progressbar(panel, mode="determinate",
                                          maximum=len(STEPS))
        self._progress.pack(padx=12, fill="x")

        # ── 미처리 목록 (에러 펼치기) ───────────────────────
        self._build_unproc(panel)

        return panel

    def _build_unproc(self, parent):
        uf = tk.LabelFrame(parent, text="미처리 목록", font=(F, 11, "bold"),
                            bg=C_SIDE, fg=C_TEXT, padx=6, pady=4,
                            relief="flat",
                            highlightbackground=C_BORDER, highlightthickness=1)
        uf.pack(fill="x", padx=12, pady=6)

        u_cols = ("ID", "이름", "오류")
        self._unproc_tv = ttk.Treeview(
            uf, columns=u_cols, show="tree headings",
            height=4, selectmode="browse")
        self._unproc_tv.heading("ID",   text="ID")
        self._unproc_tv.heading("이름", text="이름")
        self._unproc_tv.heading("오류", text="오류 내용")
        self._unproc_tv.column("#0",   width=18, minwidth=18, stretch=False)
        self._unproc_tv.column("ID",   width=42, minwidth=38, anchor="center")
        self._unproc_tv.column("이름", width=68, minwidth=60)
        self._unproc_tv.column("오류", width=116, minwidth=80)
        self._unproc_tv.tag_configure("detail",
                                       foreground=C_DANGER,
                                       background="#FFF3F3",
                                       font=(FM, 9))
        self._unproc_tv.pack(fill="x")
        self._unproc_tv.bind("<<TreeviewOpen>>",  self._unproc_expand)
        self._unproc_tv.bind("<<TreeviewClose>>", self._unproc_collapse)

        ubr = tk.Frame(uf, bg=C_SIDE)
        ubr.pack(fill="x", pady=(4, 0))
        tk.Button(ubr, text="새로고침",
                  command=self._refresh_unproc,
                  bg=C_BG, fg=C_TEXT, font=(F, 10),
                  relief="flat", cursor="hand2").pack(side="left")
        tk.Button(ubr, text="선택 불러오기",
                  command=self._load_selected_unproc,
                  bg=C_HOVER, fg=C_PRI, font=(F, 10),
                  relief="flat", cursor="hand2").pack(side="left", padx=4)

    # ── 가운데 패널 ────────────────────────────────────────────────────
    def _build_center(self, parent) -> tk.Frame:
        panel = tk.Frame(parent, bg=C_BG)

        # 드롭 영역 (고정 높이 — 드래그 대상 아님)
        dz = tk.Frame(panel, bg=C_HOVER, height=100,
                       highlightbackground=C_PRI, highlightthickness=2,
                       cursor="hand2")
        dz.pack(fill="x", padx=14, pady=(14, 6))
        dz.pack_propagate(False)
        dl = tk.Label(dz,
                      text="파일을 드래그하거나 클릭하여 추가  ·  사진 / 이력서 / 커버레터 / 추천서",
                      bg=C_HOVER, fg=C_PRI, font=(F, 12), justify="center")
        dl.pack(expand=True)
        dz.bind("<Button-1>", self._browse_files)
        dl.bind("<Button-1>", self._browse_files)
        if _DND_AVAILABLE:
            dz.drop_target_register(DND_FILES)
            dz.dnd_bind("<<Drop>>", self._on_drop)

        # 하단 버튼 (항상 고정)
        btf = tk.Frame(panel, bg=C_BG,
                        highlightbackground=C_BORDER, highlightthickness=1)
        btf.pack(fill="x", padx=14, pady=8, side="bottom")

        self._prev_btn = tk.Button(btf, text="◀ 이전",
                                    command=self._prev_step,
                                    bg=C_BORDER, fg=C_TEXT,
                                    font=(F, 11), relief="flat",
                                    padx=10, pady=6, cursor="hand2")
        self._prev_btn.pack(side="left", padx=(8, 2), pady=6)

        tk.Button(btf, text="건너뜀",
                  command=self._skip_step,
                  bg=C_BORDER, fg=C_TEXT,
                  font=(F, 11), relief="flat",
                  padx=10, pady=6, cursor="hand2"
                  ).pack(side="left", padx=2, pady=6)

        self._pause_btn = tk.Button(btf, text="일시정지",
                                     command=self._toggle_pause,
                                     bg=C_PAUSE, fg=C_DANGER,
                                     font=(F, 11, "bold"), relief="flat",
                                     padx=10, pady=6, cursor="hand2")
        self._pause_btn.pack(side="left", padx=2, pady=6)

        self._stop_btn = tk.Button(btf, text="중단하기",
                                    command=self._force_stop,
                                    bg=C_STOP, fg="white",
                                    font=(F, 11, "bold"), relief="flat",
                                    padx=10, pady=6, cursor="hand2")
        self._stop_btn.pack(side="left", padx=2, pady=6)

        self._next_btn = tk.Button(btf, text="다음 단계  ▶",
                                    command=self._next_step,
                                    bg=C_PRI, fg="white",
                                    font=(F, 12, "bold"), relief="flat",
                                    padx=14, pady=6, cursor="hand2")
        self._next_btn.pack(side="right", padx=8, pady=6)

        # ── 세로 PanedWindow: 파일목록 ↕ PII영역 (드래그 자유) ──
        vpaned = ttk.PanedWindow(panel, orient="vertical")
        vpaned.pack(fill="both", expand=True, padx=14, pady=(0, 4))

        # 상단: 파일 목록 (드래그로 크기 조절)
        top_pane = tk.Frame(vpaned, bg=C_BG)
        vpaned.add(top_pane, weight=3)

        flf = tk.LabelFrame(top_pane, text="파일 목록", font=(F, 11, "bold"),
                             bg=C_BG, fg=C_TEXT, padx=6, pady=4,
                             relief="flat",
                             highlightbackground=C_BORDER, highlightthickness=1)
        flf.pack(fill="both", expand=True)

        # ── 5개 고정 슬롯 (한 사람 = 사진+이력서+커버레터+추천서+기타) ──
        f_cols = ("구분", "파일명", "크기", "상태")
        self._file_tv = ttk.Treeview(flf, columns=f_cols,
                                      show="headings",
                                      selectmode="browse",
                                      height=5)
        self._file_tv.heading("구분",   text="구분")
        self._file_tv.heading("파일명", text="파일명")
        self._file_tv.heading("크기",   text="크기")
        self._file_tv.heading("상태",   text="상태")
        self._file_tv.column("구분",   width=80,  minwidth=72,  anchor="center")
        self._file_tv.column("파일명", width=260, minwidth=140)
        self._file_tv.column("크기",   width=68,  minwidth=56,  anchor="center")
        self._file_tv.column("상태",   width=80,  minwidth=64,  anchor="center")
        # 슬롯별 배경색
        self._file_tv.tag_configure("photo",  background="#FFF8E1")
        self._file_tv.tag_configure("resume", background="#E8F5E9")
        self._file_tv.tag_configure("cover",  background="#E3F2FD")
        self._file_tv.tag_configure("rec",    background="#FCE4EC")
        self._file_tv.tag_configure("unknown",background="#F5F5F5")
        # 상태별 글자색
        self._file_tv.tag_configure("st_done",    foreground="#1D9E75")
        self._file_tv.tag_configure("st_err",     foreground="#E24B4A")
        self._file_tv.tag_configure("st_working", foreground="#EF9F27")
        self._file_tv.bind("<Delete>", self._delete_selected_file)

        self._file_tv.pack(fill="both", expand=True)

        # 5개 슬롯 미리 생성
        _slots = [
            ("photo",   "📷 사진"),
            ("resume",  "📄 이력서"),
            ("cover",   "📝 커버레터"),
            ("rec",     "📋 추천서"),
            ("unknown", "📎 기타"),
        ]
        for ftype, label in _slots:
            iid = self._file_tv.insert("", "end",
                                        values=(label, "(없음)", "—", "—"),
                                        tags=(ftype,))
            self._file_slot_ids[ftype] = iid

        tk.Button(flf, text="선택 슬롯 초기화 (Del)",
                  command=self._delete_selected_file,
                  bg=C_BG, fg=C_SUB, font=(F, 11),
                  relief="flat", cursor="hand2").pack(anchor="e", pady=(2, 0))

        # 하단: PII 탐지 결과 (드래그로 크기 조절)
        bot_pane = tk.Frame(vpaned, bg=C_BG)
        vpaned.add(bot_pane, weight=1)

        pii_hdr = tk.Frame(bot_pane, bg=C_BG)
        pii_hdr.pack(fill="x", pady=(4, 0))

        self._pii_toggle_btn = tk.Button(
            pii_hdr, text="  PII 탐지 결과 보기",
            command=self._toggle_pii,
            bg=C_BG, fg=C_SUB, font=(F, 10),
            relief="flat", cursor="hand2", anchor="w")
        self._pii_toggle_btn.pack(side="left", fill="x", expand=True)

        self._focus_btn = tk.Button(
            pii_hdr, text="집중 점검",
            command=self._focus_check,
            bg=C_WARN, fg="white", font=(F, 10),
            relief="flat", padx=6, pady=1,
            cursor="hand2", state="disabled")
        self._focus_btn.pack(side="right")

        self._pii_container = tk.Frame(bot_pane, bg=C_BG)
        # 기본 숨김

        self._pii_text = scrolledtext.ScrolledText(
            self._pii_container, font=(FM, 11),
            bg="#FAFAFA", relief="flat", selectbackground=C_HOVER)
        self._pii_text.pack(fill="both", expand=True, pady=(0, 4))
        self._pii_text.tag_config("red",    foreground=C_DANGER, background="#FEF2F2")
        self._pii_text.tag_config("yellow", foreground=C_WARN,   background="#FFFBEB")
        self._pii_text.tag_config("green",  foreground=C_PRI,    background="#F0FDF4")
        self._pii_text.bind("<<Selection>>", self._on_pii_select)

        return panel

    # ── 우측 패널 ──────────────────────────────────────────────────────
    def _build_right(self, parent) -> tk.Frame:
        panel = tk.Frame(parent, bg=C_SIDE, width=340)
        panel.pack_propagate(False)

        prf = tk.LabelFrame(panel, text="PDF 미리보기", font=(F, 11, "bold"),
                             bg=C_SIDE, fg=C_TEXT, padx=8, pady=6,
                             relief="flat",
                             highlightbackground=C_BORDER, highlightthickness=1)
        prf.pack(fill="x", padx=12, pady=14)

        self._preview_lbl = tk.Label(prf, bg="#E0E0E0",
                                      width=34, height=20,
                                      text="미리보기\n없음",
                                      fg=C_SUB, font=(F, 11))
        self._preview_lbl.pack()

        mf = tk.LabelFrame(panel, text="파일 정보", font=(F, 11, "bold"),
                            bg=C_SIDE, fg=C_TEXT, padx=8, pady=6,
                            relief="flat",
                            highlightbackground=C_BORDER, highlightthickness=1)
        mf.pack(fill="x", padx=12, pady=4)

        self._meta_info_labels = {}
        for key, label in [("size", "용량"), ("pages", "페이지"), ("pii_count", "삭제 항목")]:
            row = tk.Frame(mf, bg=C_SIDE)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"{label}:", bg=C_SIDE, fg=C_SUB,
                     font=(F, 11), width=8, anchor="w").pack(side="left")
            lbl = tk.Label(row, text="—", bg=C_SIDE, fg=C_TEXT,
                           font=(F, 11, "bold"))
            lbl.pack(side="left")
            self._meta_info_labels[key] = lbl

        fnf = tk.Frame(panel, bg=C_SIDE)
        fnf.pack(fill="x", padx=12, pady=4)
        tk.Label(fnf, text="파일명:", bg=C_SIDE, fg=C_SUB,
                 font=(F, 11)).pack(anchor="w")
        self._fname_lbl = tk.Label(fnf, text="—", bg=C_SIDE,
                                    fg=C_TEXT, font=(F, 11, "bold"),
                                    wraplength=250, justify="left")
        self._fname_lbl.pack(anchor="w")

        # 중복 감지 카드
        self._dup_card  = tk.Frame(panel, bg="#FFF8E1",
                                    highlightbackground=C_WARN, highlightthickness=1)
        self._dup_title = tk.Label(self._dup_card, text="⚠ 중복 제출 감지",
                                    bg="#FFF8E1", fg=C_WARN, font=(F, 11, "bold"))
        self._dup_body  = tk.Label(self._dup_card, text="", bg="#FFF8E1",
                                    fg=C_TEXT, font=(F, 11),
                                    wraplength=240, justify="left")
        self._dup_btn   = tk.Button(self._dup_card, text="비교",
                                     bg=C_WARN, fg="white", font=(F, 11),
                                     relief="flat", padx=6, cursor="hand2")

        # 재지원 카드
        self._reapp_card  = tk.Frame(panel, bg="#FEF2F2",
                                      highlightbackground=C_DANGER, highlightthickness=1)
        self._reapp_title = tk.Label(self._reapp_card, text="재지원 감지",
                                      bg="#FEF2F2", fg=C_DANGER,
                                      font=(F, 11, "bold"))
        self._reapp_body  = tk.Label(self._reapp_card, text="", bg="#FEF2F2",
                                      fg=C_TEXT, font=(F, 11),
                                      wraplength=240, justify="left")
        btn_row = tk.Frame(self._reapp_card, bg="#FEF2F2")
        self._reapp_view_btn = tk.Button(btn_row, text="이전 파일 보기",
                                          bg=C_BG, fg=C_DANGER, font=(F, 11),
                                          relief="flat", padx=4, cursor="hand2")
        self._reapp_del_btn  = tk.Button(btn_row, text="삭제",
                                          bg=C_DANGER, fg="white", font=(F, 11),
                                          relief="flat", padx=4, cursor="hand2")
        self._reapp_keep_btn = tk.Button(btn_row, text="유지",
                                          bg=C_BG, fg=C_TEXT, font=(F, 11),
                                          relief="flat", padx=4, cursor="hand2")
        for b in [self._reapp_view_btn, self._reapp_del_btn, self._reapp_keep_btn]:
            b.pack(side="left", padx=2)

        return panel

    # ══════════════════════════════════════════════════════════════════
    # 모드 토글
    # ══════════════════════════════════════════════════════════════════

    def _set_mode(self, mode: str):
        self._mode.set(mode)
        self._update_mode_btns()

    def _update_mode_btns(self):
        sel = self._mode.get()
        for m, btn in self._mode_btns.items():
            if m == sel:
                btn.config(bg=C_PRI, fg="white")
            else:
                btn.config(bg=C_SIDE, fg=C_PRI)

    # ══════════════════════════════════════════════════════════════════
    # 보안: candidate_id 검증 — 숫자만 / 최대 8자리
    # ══════════════════════════════════════════════════════════════════

    def _validate_id(self, value: str) -> bool:
        return value == "" or (value.isdigit() and len(value) <= 8)

    # ══════════════════════════════════════════════════════════════════
    # 파일 핸들러
    # ══════════════════════════════════════════════════════════════════

    def _browse_files(self, event=None):
        paths = filedialog.askopenfilenames(
            title="파일 선택",
            filetypes=[("지원 파일", "*.pdf *.docx *.doc *.jpg *.jpeg *.png *.webp"),
                       ("모든 파일", "*.*")])
        if paths:
            self._add_files([Path(p) for p in paths])

    def _on_drop(self, event):
        if _DND_AVAILABLE:
            self._add_files([Path(p) for p in self.root.tk.splitlist(event.data)])

    def _add_files(self, paths: list):
        from .file_classifier import detect_file_type
        icons = {"photo": "사진", "resume": "이력서", "cover": "커버레터", "rec": "추천서"}
        for p in paths:
            if not p.exists():
                continue
            ftype  = detect_file_type(p)
            self._files[ftype] = p
            size_kb = p.stat().st_size // 1024
            label   = icons.get(ftype, ftype)
            self._file_tv.insert("", "end",
                                  values=(label, p.name, f"{size_kb}KB", "대기"),
                                  tags=(ftype,))
        self._update_fname_preview()

    def _delete_selected_file(self, event=None):
        sel = self._file_tv.selection()
        if not sel:
            return
        item = sel[0]
        vals = self._file_tv.item(item, "values")
        rev  = {"사진": "photo", "이력서": "resume",
                "커버레터": "cover", "추천서": "rec"}
        ftype = rev.get(vals[0]) if vals else None
        if ftype and ftype in self._files:
            del self._files[ftype]
        self._file_tv.delete(item)

    # ══════════════════════════════════════════════════════════════════
    # 대기열
    # ══════════════════════════════════════════════════════════════════

    def _queue_add(self):
        if len(self._queue) >= QUEUE_MAX:
            messagebox.showwarning("대기열 가득 참",
                                   f"최대 {QUEUE_MAX}명까지만 추가 가능합니다.")
            return
        cid = self._candidate_id.get().strip()
        if not cid:
            messagebox.showwarning("입력 필요", "강사 번호를 입력하세요.")
            return
        if not self._files:
            messagebox.showwarning("파일 없음", "먼저 파일을 추가하세요.")
            return

        self._queue_counter += 1
        item = QueueItem(
            queue_id=f"Q{self._queue_counter:02d}",
            candidate_id=cid,
            files=dict(self._files),
            status="대기",
        )
        self._queue.append(item)
        self._refresh_queue_tv()

        # 입력 초기화
        self._candidate_id.set("")
        self._files.clear()
        for row in self._file_tv.get_children():
            self._file_tv.delete(row)
        self._meta_label.config(text="")
        messagebox.showinfo("추가 완료",
                             f"강사 {cid}번이 {len(self._queue)}번 슬롯에 추가됐습니다.")

    def _queue_remove(self):
        sel = self._queue_tv.selection()
        if not sel:
            return
        all_rows = list(self._queue_tv.get_children(""))
        idx = all_rows.index(sel[0]) if sel[0] in all_rows else -1
        if 0 <= idx < len(self._queue):
            del self._queue[idx]
        self._refresh_queue_tv()

    def _queue_start(self):
        if not self._queue:
            messagebox.showwarning("대기열 비어 있음", "처리할 항목이 없습니다.")
            return
        if self._pipeline_thread and self._pipeline_thread.is_alive():
            messagebox.showwarning("처리 중", "이미 처리가 진행 중입니다.")
            return
        self._stopped = False
        self._paused  = False
        self._pipeline_thread = threading.Thread(
            target=self._run_queue_pipeline, daemon=True)
        self._pipeline_thread.start()

    def _run_queue_pipeline(self):
        for item in self._queue:
            if self._stopped:
                break
            if item.status != "대기":
                continue
            item.status = "처리중"
            self._active_queue_id = item.queue_id
            self.root.after(0, self._refresh_queue_tv)
            try:
                self._process_item(item)
                item.status = "완료"
            except Exception as e:
                item.status = "오류"
                item.error  = str(e)
                log.error(f"Queue [{item.candidate_id}]: {e}")
            self.root.after(0, self._refresh_queue_tv)
        self._active_queue_id = None
        self.root.after(0, lambda: self._status_var.set("모든 항목 처리 완료"))

    def _process_item(self, item: QueueItem):
        self._files = item.files
        self.root.after(0, lambda: self._candidate_id.set(item.candidate_id))
        for step_idx in range(len(STEPS)):
            while self._paused and not self._stopped:
                time.sleep(0.3)
            if self._stopped:
                raise InterruptedError("강제 중단됨")
            self._current_step = step_idx
            self.root.after(0, self._update_step_ui)
            self._start_blink(STEP_ACTIONS[step_idx])
            if step_idx == 1:
                self.root.after(0, self._run_face_crop)
            elif step_idx == 2:
                self.root.after(0, self._run_pii)
            elif step_idx == 3:
                self.root.after(0, self._run_build_pdf)
            elif step_idx == 4:
                self.root.after(0, self._run_save)
            time.sleep(0.8)
        self._stop_blink()

    def _refresh_queue_tv(self):
        for row in self._queue_tv.get_children():
            self._queue_tv.delete(row)
        s_icons = {"대기": "대기", "처리중": "처리중", "완료": "완료", "오류": "오류"}
        tag_map  = {"대기": "wait", "처리중": "active", "완료": "done", "오류": "error"}
        for i, item in enumerate(self._queue, 1):
            tag = tag_map.get(item.status, "wait")
            self._queue_tv.insert("", "end",
                                   values=(i, item.candidate_id,
                                           len(item.files),
                                           s_icons.get(item.status, item.status)),
                                   tags=(tag,))

    # ══════════════════════════════════════════════════════════════════
    # 애니메이션 (깜박 점)
    # ══════════════════════════════════════════════════════════════════

    def _start_blink(self, text: str):
        self._blink_base = text
        self._blink_dots = 0
        self._do_blink()

    def _do_blink(self):
        dots = "." * (self._blink_dots % 4)
        self._status_var.set(f"⚙  {self._blink_base}{dots}")
        self._blink_dots += 1
        self._blink_after = self.root.after(480, self._do_blink)

    def _stop_blink(self):
        if self._blink_after:
            self.root.after_cancel(self._blink_after)
            self._blink_after = None
        self._status_var.set("")

    # ══════════════════════════════════════════════════════════════════
    # 컨트롤 버튼
    # ══════════════════════════════════════════════════════════════════

    def _toggle_pause(self):
        self._paused = not self._paused
        if self._paused:
            self._pause_btn.config(text="계속 진행")
            self._status_var.set("일시정지됨")
        else:
            self._pause_btn.config(text="일시정지")
            if self._blink_base:
                self._start_blink(self._blink_base)

    def _force_stop(self):
        ok = messagebox.askyesno("강제 중단",
                                  "처리를 중단하시겠습니까?\n현재 항목은 오류로 표시됩니다.")
        if ok:
            self._stopped = True
            self._paused  = False
            self._stop_blink()
            self._status_var.set("중단됨")
            for item in self._queue:
                if item.status == "처리중":
                    item.status = "오류"
                    item.error  = "강제 중단"
            self._refresh_queue_tv()

    def _next_step(self):
        if self._current_step < len(STEPS) - 1:
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

    # ══════════════════════════════════════════════════════════════════
    # PII 패널 토글
    # ══════════════════════════════════════════════════════════════════

    def _toggle_pii(self):
        if self._pii_expanded:
            self._pii_container.pack_forget()
            self._pii_toggle_btn.config(text="  PII 탐지 결과 보기")
            self._pii_expanded = False
        else:
            self._pii_container.pack(fill="both", expand=True)
            self._pii_toggle_btn.config(text="  PII 탐지 결과 숨기기")
            self._pii_expanded = True

    # ══════════════════════════════════════════════════════════════════
    # 시트 연결
    # ══════════════════════════════════════════════════════════════════

    def _open_sheet_settings(self):
        try:
            from .vault_import import VaultConfig
            vc = VaultConfig()
            vc.open_dialog(self.root, on_saved=self._check_sheet_connection)
        except ImportError:
            self._simple_sheet_dialog()

    def _simple_sheet_dialog(self):
        """연결 설정 다이얼로그 — Bridge API (기본) + Google Sheets (폴백)."""
        dlg = tk.Toplevel(self.root)
        dlg.title("데이터 소스 연결 설정")
        dlg.geometry("480x420")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.configure(bg=C_SIDE)

        try:
            import keyring
            _kr = keyring
        except ImportError:
            messagebox.showerror("keyring 없음",
                                  "pip install keyring 을 실행하세요.", parent=dlg)
            dlg.destroy()
            return

        # 현재 저장값 로드
        def _get(key, default=""):
            try:
                return _kr.get_password("BRIDGE_RC_CONFIG_V1", key) or default
            except Exception:
                return default

        source_var = tk.StringVar(value=_get("source", "bridge"))

        # ── 소스 선택 ──────────────────────────────────────────────
        src_frame = tk.LabelFrame(dlg, text="데이터 소스", font=(F, 11, "bold"),
                                   bg=C_SIDE, fg=C_TEXT, padx=12, pady=6)
        src_frame.pack(fill="x", padx=18, pady=(14, 6))
        for val, lbl in [("bridge", "Bridge 관리자 API  (권장 — 실시간 연동)"),
                          ("sheets", "Google Sheets  (폴백)")]:
            tk.Radiobutton(src_frame, text=lbl, variable=source_var, value=val,
                           bg=C_SIDE, fg=C_TEXT, selectcolor=C_SIDE,
                           font=(F, 11), activebackground=C_HOVER
                           ).pack(anchor="w")

        # ── Bridge API ─────────────────────────────────────────────
        ba_frame = tk.LabelFrame(dlg, text="Bridge API 설정", font=(F, 11, "bold"),
                                  bg=C_SIDE, fg=C_TEXT, padx=12, pady=6)
        ba_frame.pack(fill="x", padx=18, pady=4)

        tk.Label(ba_frame, text="관리자 비밀번호:", font=(F, 10),
                 bg=C_SIDE).pack(anchor="w")
        pw_var = tk.StringVar()
        tk.Entry(ba_frame, textvariable=pw_var, font=(F, 11), show="*", width=38
                 ).pack(fill="x", pady=(0, 4))
        tk.Label(ba_frame,
                 text="API URL은 운영 도메인(api.bridgejob.co.kr)이 자동 적용됩니다.",
                 font=(F, 9), fg=C_SUB, bg=C_SIDE
                 ).pack(anchor="w")

        # ── Google Sheets ──────────────────────────────────────────
        gs_frame = tk.LabelFrame(dlg, text="Google Sheets 설정 (폴백용)",
                                  font=(F, 11, "bold"),
                                  bg=C_SIDE, fg=C_TEXT, padx=12, pady=6)
        gs_frame.pack(fill="x", padx=18, pady=4)

        tk.Label(gs_frame, text="Spreadsheet ID:", font=(F, 10),
                 bg=C_SIDE).pack(anchor="w")
        sid_var = tk.StringVar(value=_get("sheet_id"))
        tk.Entry(gs_frame, textvariable=sid_var, font=(F, 11), width=38
                 ).pack(fill="x", pady=(0, 4))
        tk.Label(gs_frame, text="Service Account JSON Key:", font=(F, 10),
                 bg=C_SIDE).pack(anchor="w")
        key_var = tk.StringVar()
        tk.Entry(gs_frame, textvariable=key_var, font=(F, 11), show="*", width=38
                 ).pack(fill="x")

        def _save():
            source = source_var.get()
            pw     = pw_var.get().strip()
            sid    = sid_var.get().strip()
            key    = key_var.get().strip()

            if source == "bridge" and not pw:
                messagebox.showwarning("입력 필요", "관리자 비밀번호를 입력하세요.", parent=dlg)
                return
            if source == "sheets" and (not sid):
                messagebox.showwarning("입력 필요", "Spreadsheet ID를 입력하세요.", parent=dlg)
                return
            try:
                _kr.set_password("BRIDGE_RC_CONFIG_V1", "source", source)
                if pw:
                    _kr.set_password("BRIDGE_RC_CONFIG_V1", "admin_pw", pw)
                if sid:
                    _kr.set_password("BRIDGE_RC_CONFIG_V1", "sheet_id", sid)
                if key:
                    _kr.set_password("BRIDGE_RC_CONFIG_V1", "sa_json", key)
                dlg.destroy()
                self._check_sheet_connection()
            except Exception as e:
                messagebox.showerror("저장 실패", str(e), parent=dlg)

        tk.Button(dlg, text="저장 & 연결 테스트", command=_save,
                  bg=C_PRI, fg="white", font=(F, 11, "bold"),
                  relief="flat", padx=14, pady=5).pack(pady=10)

    def _check_sheet_connection(self):
        def _check():
            try:
                from .sheets_connector import is_connected
                ok = is_connected()
            except Exception:
                ok = False
            color = C_PRI   if ok else C_DANGER
            text  = "● 시트 연결됨" if ok else "● 시트 미연결"
            self._sheet_connected = ok
            self.root.after(0, lambda: self._sheet_label.config(text=text, fg=color))
        threading.Thread(target=_check, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════
    # 시트 / 미처리 목록
    # ══════════════════════════════════════════════════════════════════

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
                    text=(f"국적: {info.get('nationality', '?')}  "
                          f"성별: {info.get('gender', '?')}  "
                          f"생년: {info.get('birth_year', '?')}"))
                self._update_fname_preview(info)
            else:
                self._meta_label.config(text="번호를 찾을 수 없음")
        except Exception as e:
            self._meta_label.config(text=f"조회 실패: {e}")

    def _refresh_unproc(self):
        for row in self._unproc_tv.get_children():
            self._unproc_tv.delete(row)
        try:
            from .sheets_connector import get_unprocessed_rows
            rows = get_unprocessed_rows(20)
            for r in rows:
                err = r.get("error", "")
                self._unproc_tv.insert(
                    "", "end",
                    values=(r["id"], r.get("name", ""), err or "정상"),
                    open=False)
        except Exception as e:
            log.warning(f"미처리 목록 갱신 실패: {e}")

    def _unproc_expand(self, event):
        item = self._unproc_tv.focus()
        if not item:
            return
        children = self._unproc_tv.get_children(item)
        if children:
            return  # 이미 자식 있음
        vals = self._unproc_tv.item(item, "values")
        err = vals[2] if len(vals) > 2 else ""
        if err and err != "정상":
            self._unproc_tv.insert(item, "end",
                                    values=("", f"오류 상세: {err}", ""),
                                    tags=("detail",))

    def _unproc_collapse(self, event):
        item = self._unproc_tv.focus()
        if not item:
            return
        for c in self._unproc_tv.get_children(item):
            self._unproc_tv.delete(c)

    def _load_selected_unproc(self):
        sel = self._unproc_tv.selection()
        if not sel:
            return
        vals = self._unproc_tv.item(sel[0], "values")
        if vals:
            self._candidate_id.set(str(vals[0]))
            self._load_from_sheet()

    # ══════════════════════════════════════════════════════════════════
    # 파이프라인 단계
    # ══════════════════════════════════════════════════════════════════

    def _run_current_step(self):
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
            data   = crop_face(photo)
            img    = Image.open(io.BytesIO(data)).resize((150, 200), Image.LANCZOS)
            tk_img = ImageTk.PhotoImage(img)
            self._preview_lbl.configure(image=tk_img, text="")
            self._preview_lbl.image = tk_img
        except FaceNotFoundError:
            messagebox.showwarning("얼굴 미감지",
                                   "얼굴을 찾지 못했습니다. 수동 영역 선택이 필요합니다.")

    def _run_pii(self):
        from .pii_engine import analyze_pii, load_api_key
        api_key  = load_api_key()
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
        for item in result.pii_found:
            ph = f"[{item.type.upper()}_REMOVED]"
            st = text.find(ph)
            if st >= 0:
                self._pii_text.tag_add(item.color,
                                        f"1.0+{st}c",
                                        f"1.0+{st + len(ph)}c")
        for u in result.uncertain:
            ut = u.get("text", "")
            if ut in text:
                st = text.find(ut)
                self._pii_text.tag_add("yellow",
                                        f"1.0+{st}c",
                                        f"1.0+{st + len(ut)}c")
        self._pii_text.config(state="disabled")
        self._meta_info_labels["pii_count"].config(text=str(len(result.pii_found)))
        if not self._pii_expanded:
            self._toggle_pii()

    def _run_build_pdf(self):
        cid = self._candidate_id.get().strip() or "0000"
        from .pdf_builder import build_pdf
        out, size = build_pdf(
            candidate_id=cid,
            photo_bytes=None,
            cover_text=self._pii_result.cleaned_text if self._pii_result else None,
            out_dir=OUTPUT_DIR)
        self._meta_info_labels["size"].config(text=f"{size // 1024}KB")
        self._fname_lbl.config(text=out.name)

    def _run_save(self):
        messagebox.showinfo("저장 완료", "PDF 변환이 완료되었습니다.")

    def _finish(self):
        messagebox.showinfo("완료", "모든 단계가 완료되었습니다.")
        self._current_step = 0
        self._update_step_ui()

    # ══════════════════════════════════════════════════════════════════
    # UI 업데이트 헬퍼
    # ══════════════════════════════════════════════════════════════════

    def _update_step_ui(self):
        for i, (dot, lbl) in enumerate(self._step_rows):
            if i < self._current_step:
                dot.config(text="✓", fg=C_PRI)
                lbl.config(fg=C_SUB, font=(F, 11))
            elif i == self._current_step:
                dot.config(text="●", fg=C_WARN)
                lbl.config(fg=C_TEXT, font=(F, 11, "bold"))
            else:
                dot.config(text="○", fg=C_BORDER)
                lbl.config(fg=C_TEXT, font=(F, 11))
        self._progress["value"] = self._current_step

    def _update_fname_preview(self, info: dict | None = None):
        cid = self._candidate_id.get().strip() or "?"
        nat = info.get("nationality", "") if info else ""
        gen = info.get("gender",      "") if info else ""
        yr  = info.get("birth_year",  "") if info else ""
        try:
            from .pdf_builder import build_filename
            self._fname_lbl.config(text=build_filename(cid, nat, gen, yr))
        except Exception:
            pass

    def _focus_check(self):
        try:
            sel_text = self._pii_text.get("sel.first", "sel.last")
        except tk.TclError:
            sel_text = ""
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

    def _on_pii_select(self, event=None):
        try:
            sel   = self._pii_text.get("sel.first", "sel.last")
            state = "normal" if sel.strip() else "disabled"
        except tk.TclError:
            state = "disabled"
        self._focus_btn.config(state=state)

    # ══════════════════════════════════════════════════════════════════
    # 알림 카드 (외부 호출)
    # ══════════════════════════════════════════════════════════════════

    def show_duplicate_alert(self, candidate_id: str, old_path, new_path):
        self._dup_body.config(
            text=f"이전: {old_path.name}\n{candidate_id}번 7일 내 재제출 감지")
        for w in [self._dup_title, self._dup_body, self._dup_btn]:
            w.pack(anchor="w", padx=8, pady=2)
        self._dup_card.pack(fill="x", padx=12, pady=4)

    def show_reapply_alert(self, candidate_id: str, old_path):
        self._reapp_body.config(text=f"이전 지원: {old_path.name}")
        for w in [self._reapp_title, self._reapp_body]:
            w.pack(anchor="w", padx=8, pady=2)
        btn_row = self._reapp_view_btn.master
        btn_row.pack(anchor="w", padx=8, pady=4)
        self._reapp_view_btn.config(
            command=lambda: os.startfile(str(old_path.parent)))
        self._reapp_del_btn.config(
            command=lambda: self._confirm_delete_old(old_path))
        self._reapp_keep_btn.config(
            command=lambda: self._reapp_card.pack_forget())
        self._reapp_card.pack(fill="x", padx=12, pady=4)

    def _confirm_delete_old(self, old_path):
        ok = messagebox.askyesno(
            "이전 파일 삭제",
            f"이전 파일을 originals\\ 로 이동 후 삭제합니다.\n\n{old_path}"
            "\n\n복구 불가합니다. 계속하시겠습니까?")
        if ok:
            from .security import secure_delete, encrypt_file
            import shutil
            dest = BASE_DIR / "originals" / old_path.name
            dest.parent.mkdir(exist_ok=True)
            shutil.move(str(old_path), str(dest))
            encrypt_file(dest)
            secure_delete(dest)
            self._reapp_card.pack_forget()
            messagebox.showinfo("삭제 완료", "이전 파일이 삭제되었습니다.")

    # ══════════════════════════════════════════════════════════════════
    # 실행
    # ══════════════════════════════════════════════════════════════════

    def run(self):
        self.root.mainloop()


# ── 진입점 ─────────────────────────────────────────────────────────────────
def main():
    app = BridgeConverterApp()
    app.run()


if __name__ == "__main__":
    main()
