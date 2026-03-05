"""
BRIDGE RPA Overlay — 바탕화면 상단 알림
=======================================
작업 중/완료 오버레이를 주 모니터 상단에 표시.
2모니터 환경에서 게임 방해 없음 (주 모니터만 사용).
보안: 개인정보 미표시, 상태 메시지만.
"""

import threading
import tkinter as tk
from tkinter import font as tkfont


class RPAOverlay:
    """RPA 작업 상태 오버레이 (주 모니터 상단, topmost, 반투명)."""

    def __init__(self):
        self._root = None
        self._thread = None
        self._ready = threading.Event()

    def show_working(self):
        """작업 시작 오버레이 표시."""
        self._start_overlay(
            title="🏗️ 크래이그 작업중",
            message="인터넷 창을 건들지 마세요!",
            emoji="👨‍💻",
            bg_color="#1a1a2e",
            accent_color="#e94560",
            text_color="#ffffff",
        )

    def show_complete(self, posted_count: int = 0):
        """작업 완료 오버레이로 교체."""
        if self._root:
            try:
                self._root.after(0, self._root.destroy)
            except Exception:
                pass
            self._ready.clear()

        self._start_overlay(
            title=f"✅ 크래이그 광고 완료! ({posted_count}건)",
            message="개인정보 노출이 없도록\n한번 더 직접 확인해주세요 🙏",
            emoji="🎉",
            bg_color="#0f3460",
            accent_color="#16c79a",
            text_color="#ffffff",
            auto_close_sec=30,
        )

    def close(self):
        """오버레이 닫기."""
        if self._root:
            try:
                self._root.after(0, self._root.destroy)
            except Exception:
                pass
        self._ready.clear()

    def _start_overlay(self, title, message, emoji, bg_color, accent_color,
                       text_color, auto_close_sec=0):
        """별도 스레드에서 tkinter 오버레이 실행."""
        self._thread = threading.Thread(
            target=self._run,
            args=(title, message, emoji, bg_color, accent_color,
                  text_color, auto_close_sec),
            daemon=True,
        )
        self._thread.start()
        self._ready.wait(timeout=3)

    def _run(self, title, message, emoji, bg_color, accent_color,
             text_color, auto_close_sec):
        """tkinter 메인루프 (스레드 내)."""
        root = tk.Tk()
        self._root = root

        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.92)
        root.configure(bg=bg_color)

        # 주 모니터 중앙 상단 배치 (2모니터 중 주 모니터만)
        win_w, win_h = 620, 140
        screen_w = root.winfo_screenwidth()
        x = (screen_w - win_w) // 2
        y = 18
        root.geometry(f"{win_w}x{win_h}+{x}+{y}")

        # 둥근 느낌의 프레임
        frame = tk.Frame(root, bg=bg_color, padx=20, pady=12)
        frame.pack(fill="both", expand=True)

        # 이모지 (왼쪽 크게)
        try:
            emoji_font = tkfont.Font(family="Segoe UI Emoji", size=38)
        except Exception:
            emoji_font = tkfont.Font(size=38)

        emoji_label = tk.Label(frame, text=emoji, font=emoji_font,
                               bg=bg_color, fg=text_color)
        emoji_label.pack(side="left", padx=(0, 16))

        # 텍스트 영역 (중앙)
        text_frame = tk.Frame(frame, bg=bg_color)
        text_frame.pack(side="left", fill="both", expand=True)

        try:
            title_font = tkfont.Font(family="Malgun Gothic", size=16, weight="bold")
            msg_font = tkfont.Font(family="Malgun Gothic", size=11)
        except Exception:
            title_font = tkfont.Font(size=16, weight="bold")
            msg_font = tkfont.Font(size=11)

        tk.Label(text_frame, text=title, font=title_font,
                 bg=bg_color, fg=accent_color, anchor="w").pack(anchor="w")
        tk.Label(text_frame, text=message, font=msg_font,
                 bg=bg_color, fg=text_color, anchor="w",
                 justify="left").pack(anchor="w", pady=(4, 0))

        # 닫기 버튼 (오른쪽)
        try:
            btn_font = tkfont.Font(family="Segoe UI Emoji", size=18)
        except Exception:
            btn_font = tkfont.Font(size=18)

        close_btn = tk.Label(frame, text="✕", font=btn_font,
                             bg=bg_color, fg="#888888", cursor="hand2")
        close_btn.pack(side="right", padx=(10, 0))
        close_btn.bind("<Button-1>", lambda e: root.destroy())
        close_btn.bind("<Enter>", lambda e: close_btn.configure(fg="#ff4444"))
        close_btn.bind("<Leave>", lambda e: close_btn.configure(fg="#888888"))

        # 하단 액센트 라인
        tk.Frame(root, bg=accent_color, height=3).pack(fill="x", side="bottom")

        # 드래그 이동 지원
        def _start_drag(event):
            root._drag_x = event.x
            root._drag_y = event.y

        def _do_drag(event):
            dx = event.x - root._drag_x
            dy = event.y - root._drag_y
            nx = root.winfo_x() + dx
            ny = root.winfo_y() + dy
            root.geometry(f"+{nx}+{ny}")

        frame.bind("<ButtonPress-1>", _start_drag)
        frame.bind("<B1-Motion>", _do_drag)

        # 자동 닫기 타이머
        if auto_close_sec > 0:
            root.after(auto_close_sec * 1000, root.destroy)

        self._ready.set()

        try:
            root.mainloop()
        except Exception:
            pass


# 싱글턴 인스턴스
_overlay = RPAOverlay()


def show_working():
    """작업 시작 오버레이."""
    _overlay.show_working()


def show_complete(posted_count: int = 0):
    """작업 완료 오버레이."""
    _overlay.show_complete(posted_count)


def close():
    """오버레이 닫기."""
    _overlay.close()
