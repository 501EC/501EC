#!/usr/bin/env python3
"""
Claude Code Usage Monitor — Compact Desktop Gadget (Windows x64)
Segmented horizontal bars: usage (blue) + remaining (green) vs limit.
Drag to move. Right-click for options.
"""

import tkinter as tk
import json
import os
from datetime import datetime, date, timedelta
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIG  — edit to match your plan
# ─────────────────────────────────────────────────────────────────────────────
REFRESH_INTERVAL_MS = 60_000     # 60 s between refreshes
MONTHLY_COST_LIMIT  = 20.0       # USD monthly budget
DAILY_TOKEN_LIMIT   = 1_000_000  # tokens per day
RESET_HOUR          = 0          # hour when daily limit resets (0 = midnight)

PRICING = {
    "input":       3.00,
    "output":     15.00,
    "cache_write": 3.75,
    "cache_read":  0.30,
}

# ─────────────────────────────────────────────────────────────────────────────
#  THEME
# ─────────────────────────────────────────────────────────────────────────────
C = {
    "bg":      "#0d1117",
    "bg2":     "#161b22",
    "bg3":     "#1c2128",
    "border":  "#30363d",
    "text":    "#e6edf3",
    "dim":     "#8b949e",
    "accent":  "#7c3aed",
    "used":    "#388bfd",   # blue  — used portion of bar
    "remain":  "#238636",   # green — remaining portion of bar
    "limit":   "#2d333b",   # dark  — the empty / limit background
    "warn":    "#d29922",
    "danger":  "#da3633",
}

FS = ("Segoe UI", 7)
FM = ("Segoe UI", 8)
FB = ("Segoe UI", 8, "bold")

BAR_W  = 195   # total bar width in px
BAR_H  = 10    # bar height in px

# ─────────────────────────────────────────────────────────────────────────────
#  DATA
# ─────────────────────────────────────────────────────────────────────────────

def find_claude_dir():
    for p in [
        Path(os.environ.get("APPDATA",     "")) / "Claude"  / "projects",
        Path(os.environ.get("LOCALAPPDATA","")) / "Claude"  / "projects",
        Path.home() / ".claude" / "projects",
        Path.home() / "Library" / "Application Support" / "Claude" / "projects",
    ]:
        if p.is_dir():
            return p
    return None


def parse_usage(data_dir, scope="today"):
    seen = set()
    out  = {"input": 0, "output": 0, "cache_write": 0,
            "cache_read": 0, "sessions": set(), "messages": 0}
    today = date.today().isoformat()

    files = sorted(data_dir.rglob("*.jsonl"),
                   key=lambda f: f.stat().st_mtime, reverse=True)
    if scope == "session":
        files = files[:1]

    for jf in files:
        try:
            with open(jf, encoding="utf-8", errors="replace") as fh:
                for raw in fh:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        e = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    msg = e.get("message")
                    if not isinstance(msg, dict):
                        continue
                    u = msg.get("usage")
                    if not isinstance(u, dict):
                        continue
                    mid = msg.get("id", "")
                    if mid and mid in seen:
                        continue
                    if mid:
                        seen.add(mid)
                    if scope == "today" and not e.get("timestamp","").startswith(today):
                        continue
                    out["input"]       += u.get("input_tokens", 0)
                    out["output"]      += u.get("output_tokens", 0)
                    out["cache_write"] += u.get("cache_creation_input_tokens", 0)
                    out["cache_read"]  += u.get("cache_read_input_tokens", 0)
                    out["messages"]    += 1
                    sid = e.get("sessionId")
                    if sid:
                        out["sessions"].add(sid)
        except Exception:
            continue
    return out


def calc_cost(u):
    return (u["input"]       * PRICING["input"]       +
            u["output"]      * PRICING["output"]      +
            u["cache_write"] * PRICING["cache_write"] +
            u["cache_read"]  * PRICING["cache_read"]) / 1_000_000

def total_tok(u):
    return u["input"] + u["output"] + u["cache_write"] + u["cache_read"]

def fmt_tok(n):
    return (f"{n/1e6:.2f}M" if n >= 1_000_000 else
            f"{n/1000:.0f}K" if n >= 1_000 else str(n))

def fmt_cost(v):
    return f"${v:.3f}"

def time_to_reset():
    now   = datetime.now()
    nxt   = now.replace(hour=RESET_HOUR, minute=0, second=0, microsecond=0)
    if nxt <= now:
        nxt += timedelta(days=1)
    h, r  = divmod(int((nxt - now).total_seconds()), 3600)
    m, s  = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# ─────────────────────────────────────────────────────────────────────────────
#  SEGMENTED BAR  — shows used (left) + remaining (right) vs limit (bg)
# ─────────────────────────────────────────────────────────────────────────────

class SegBar(tk.Frame):
    """
    Horizontal bar split into three zones:
      [== used (blue) ==][-- remaining (green) --][.. over limit (red) ..]
    """
    def __init__(self, parent, width=BAR_W, height=BAR_H, **kw):
        super().__init__(parent, width=width, height=height,
                         bg=C["limit"], **kw)
        self.pack_propagate(False)
        self._bar_w = width
        self._bar_h = height
        # used segment
        self._used_f = tk.Frame(self, bg=C["used"])
        self._used_f.place(x=0, y=0, width=0, height=height)
        # remaining segment (placed after used)
        self._rem_f  = tk.Frame(self, bg=C["remain"])
        self._rem_f.place(x=0, y=0, width=0, height=height)

    def set(self, used_pct, remaining_pct):
        used_pct      = max(0.0, min(1.0, used_pct))
        remaining_pct = max(0.0, min(1.0 - used_pct, remaining_pct))

        used_w = int(self._bar_w * used_pct)
        rem_w  = int(self._bar_w * remaining_pct)

        used_color = (C["danger"] if used_pct >= 0.90 else
                      C["warn"]   if used_pct >= 0.70 else C["used"])
        self._used_f.configure(bg=used_color)
        self._used_f.place(x=0,      y=0, width=used_w, height=self._h)
        self._rem_f.place( x=used_w, y=0, width=rem_w,  height=self._h)


# ─────────────────────────────────────────────────────────────────────────────
#  GADGET
# ─────────────────────────────────────────────────────────────────────────────

class ClaudeGadget:
    W, H = 240, 230

    def __init__(self):
        self.root     = tk.Tk()
        self.data_dir = find_claude_dir()
        self._setup_window()
        self._build_ui()
        self._build_menu()
        self._refresh()
        # Delay sink so window is fully visible before Win32 calls
        self.root.after(800, self._sink_to_desktop)
        self.root.mainloop()

    # ── window ───────────────────────────────────────────────────────────────

    def _setup_window(self):
        r = self.root
        r.title("Claude Usage")
        r.configure(bg=C["bg"])
        r.resizable(False, False)
        r.update_idletasks()
        sw = r.winfo_screenwidth()
        r.geometry(f"{self.W}x{self.H}+{sw - self.W - 16}+40")
        r.overrideredirect(True)
        r.attributes("-topmost", False)
        r.attributes("-alpha", 0.95)
        r.update()
        r.bind("<Button-1>",  self._drag_start)
        r.bind("<B1-Motion>", self._drag_move)
        r.bind("<ButtonRelease-1>", lambda e: self.root.after(100, self._sink_to_desktop))

    def _sink_to_desktop(self):
        """
        Send window behind all app windows using Win32 API.
        Called once after startup and re-applied every 3 s so it stays at
        the bottom even if Windows briefly raises it.
        """
        try:
            import ctypes
            # Try FindWindowW first (most reliable with overrideredirect)
            hwnd = ctypes.windll.user32.FindWindowW(None, "Claude Usage")
            if not hwnd:
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if not hwnd:
                hwnd = self.root.winfo_id()
            if not hwnd:
                return

            # Hide from taskbar and Alt+Tab
            GWL_EXSTYLE      = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_APPWINDOW  = 0x00040000
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE,
                (style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW)

            # Send behind all normal windows (desktop level)
            HWND_BOTTOM    = 1
            SWP_NOMOVE     = 0x0002
            SWP_NOSIZE     = 0x0001
            SWP_NOACTIVATE = 0x0010
            ctypes.windll.user32.SetWindowPos(
                hwnd, HWND_BOTTOM, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        except Exception:
            pass

        # Re-apply every 3 seconds to stay at the bottom
        self.root.after(3000, self._sink_to_desktop)

    # ── ui ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        r = self.root

        # ── header ──────────────────────────────────────────────────────────
        hdr = tk.Frame(r, bg=C["bg"])
        hdr.pack(fill="x", padx=10, pady=(8, 0))
        tk.Label(hdr, text="◈ Claude Code", bg=C["bg"],
                 fg=C["accent"], font=("Segoe UI", 8, "bold")).pack(side="left")
        self.lbl_time = tk.Label(hdr, text="", bg=C["bg"],
                                 fg=C["dim"], font=FS)
        self.lbl_time.pack(side="right")

        tk.Frame(r, bg=C["border"], height=1).pack(fill="x", padx=10, pady=(5, 4))

        body = tk.Frame(r, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=10)

        # helper: one labelled bar row
        def bar_row(label, limit_text):
            """Returns (value_label, bar_widget, right_label)."""
            row = tk.Frame(body, bg=C["bg"])
            row.pack(fill="x", pady=(0, 6))

            top = tk.Frame(row, bg=C["bg"])
            top.pack(fill="x")
            tk.Label(top, text=label, bg=C["bg"],
                     fg=C["dim"], font=FS).pack(side="left")
            rhs = tk.Label(top, text=limit_text, bg=C["bg"],
                           fg=C["border"], font=FS)
            rhs.pack(side="right")

            mid = tk.Frame(row, bg=C["bg"])
            mid.pack(fill="x")
            val = tk.Label(mid, text="—", bg=C["bg"],
                           fg=C["text"], font=FB)
            val.pack(side="left")
            remain_lbl = tk.Label(mid, text="", bg=C["bg"],
                                  fg=C["remain"], font=FS)
            remain_lbl.pack(side="right", anchor="s")

            bar = SegBar(row, width=BAR_W)
            bar.pack(anchor="w", pady=(3, 0))

            return val, remain_lbl, bar

        # ── COST row ─────────────────────────────────────────────────────────
        tk.Label(body, text="COST", bg=C["bg"],
                 fg=C["dim"], font=FS).pack(anchor="w")
        cost_row = tk.Frame(body, bg=C["bg"])
        cost_row.pack(fill="x")
        self.lbl_cost = tk.Label(cost_row, text="$0.000", bg=C["bg"],
                                 fg=C["used"], font=("Segoe UI", 13, "bold"))
        self.lbl_cost.pack(side="left")
        self.lbl_cost_rem = tk.Label(cost_row, text="", bg=C["bg"],
                                     fg=C["remain"], font=FS)
        self.lbl_cost_rem.pack(side="right", anchor="s", pady=(0, 2))
        self.bar_cost = SegBar(body, width=BAR_W)
        self.bar_cost.pack(anchor="w", pady=(3, 0))
        self.lbl_cost_caption = tk.Label(
            body, text=f"limit: ${MONTHLY_COST_LIMIT:.0f} / month",
            bg=C["bg"], fg=C["border"], font=FS)
        self.lbl_cost_caption.pack(anchor="w")

        tk.Frame(body, bg=C["border"], height=1).pack(fill="x", pady=(6, 4))

        # ── TOKENS row ───────────────────────────────────────────────────────
        tk.Label(body, text="TOKENS  (today)", bg=C["bg"],
                 fg=C["dim"], font=FS).pack(anchor="w")
        tok_row = tk.Frame(body, bg=C["bg"])
        tok_row.pack(fill="x")
        self.lbl_tok_used = tk.Label(tok_row, text="—", bg=C["bg"],
                                     fg=C["used"], font=FB)
        self.lbl_tok_used.pack(side="left")
        self.lbl_tok_rem = tk.Label(tok_row, text="", bg=C["bg"],
                                    fg=C["remain"], font=FS)
        self.lbl_tok_rem.pack(side="right", anchor="s")
        self.bar_tok = SegBar(body, width=BAR_W)
        self.bar_tok.pack(anchor="w", pady=(3, 0))
        self.lbl_tok_caption = tk.Label(
            body, text=f"limit: {fmt_tok(DAILY_TOKEN_LIMIT)} / day",
            bg=C["bg"], fg=C["border"], font=FS)
        self.lbl_tok_caption.pack(anchor="w")

        tk.Frame(body, bg=C["border"], height=1).pack(fill="x", pady=(6, 4))

        # ── bottom row: reset + session ───────────────────────────────────────
        bot = tk.Frame(body, bg=C["bg"])
        bot.pack(fill="x")

        tk.Label(bot, text="Reset", bg=C["bg"],
                 fg=C["dim"], font=FS).pack(side="left")
        self.lbl_reset = tk.Label(bot, text="—", bg=C["bg"],
                                  fg=C["warn"], font=FB)
        self.lbl_reset.pack(side="left", padx=(4, 0))

        self.lbl_sess = tk.Label(bot, text="", bg=C["bg"],
                                 fg=C["dim"], font=FS)
        self.lbl_sess.pack(side="right")

        # status
        self.lbl_status = tk.Label(body, text="", bg=C["bg"],
                                   fg=C["border"], font=FS)
        self.lbl_status.pack(anchor="w", pady=(4, 4))

        # ── legend ────────────────────────────────────────────────────────────
        leg = tk.Frame(r, bg=C["bg2"])
        leg.pack(fill="x")
        for color, label in [(C["used"], "used"), (C["remain"], "remaining"),
                             (C["limit"], "limit")]:
            tk.Frame(leg, bg=color, width=10, height=10).pack(
                side="left", padx=(8, 2), pady=4)
            tk.Label(leg, text=label, bg=C["bg2"],
                     fg=C["dim"], font=FS).pack(side="left", padx=(0, 6))

    # ── menu ─────────────────────────────────────────────────────────────────

    def _build_menu(self):
        m = tk.Menu(self.root, tearoff=0, bg=C["bg2"], fg=C["text"],
                    activebackground=C["accent"], activeforeground=C["text"],
                    font=FM)
        m.add_command(label="Refresh now",      command=self._refresh_now)
        m.add_separator()
        m.add_command(label="Open data folder", command=self._open_dir)
        m.add_separator()
        m.add_command(label="Exit",             command=self.root.destroy)
        self.menu = m
        self.root.bind("<Button-3>",
                       lambda e: m.tk_popup(e.x_root, e.y_root))

    def _open_dir(self):
        if self.data_dir and self.data_dir.exists():
            os.startfile(str(self.data_dir))

    # ── drag ─────────────────────────────────────────────────────────────────

    def _drag_start(self, e):
        self._ox, self._oy = e.x, e.y

    def _drag_move(self, e):
        x = self.root.winfo_x() + (e.x - self._ox)
        y = self.root.winfo_y() + (e.y - self._oy)
        self.root.geometry(f"+{x}+{y}")

    # ── refresh ───────────────────────────────────────────────────────────────

    def _refresh_now(self):
        if hasattr(self, "_aid"):
            self.root.after_cancel(self._aid)
        self._refresh()

    def _refresh(self):
        now = datetime.now().strftime("%H:%M")
        self.lbl_time.config(text=now)
        self.lbl_reset.config(text=time_to_reset())

        if not self.data_dir:
            # Show exactly where we looked so user can diagnose
            appdata = os.environ.get("APPDATA", "?")
            self.lbl_status.config(
                text=f"No data found.\nLooked in: {appdata}\\Claude\\projects\\"
                     f"\nInstall Claude Code CLI or run a session first.")
            self._aid = self.root.after(REFRESH_INTERVAL_MS, self._refresh)
            return

        try:
            today   = parse_usage(self.data_dir, "today")
            session = parse_usage(self.data_dir, "session")

            today_cost   = calc_cost(today)
            session_cost = calc_cost(session)
            today_tok    = total_tok(today)
            remaining_tok = max(0, DAILY_TOKEN_LIMIT - today_tok)
            remaining_cost = max(0.0, MONTHLY_COST_LIMIT - today_cost)

            # cost bar
            used_cost_pct = today_cost / MONTHLY_COST_LIMIT if MONTHLY_COST_LIMIT else 0
            rem_cost_pct  = remaining_cost / MONTHLY_COST_LIMIT if MONTHLY_COST_LIMIT else 0
            cost_col = (C["danger"] if used_cost_pct >= 0.90 else
                        C["warn"]   if used_cost_pct >= 0.70 else C["used"])
            self.lbl_cost.config(text=fmt_cost(today_cost), fg=cost_col)
            self.lbl_cost_rem.config(text=f"{fmt_cost(remaining_cost)} left")
            self.bar_cost.set(used_cost_pct, rem_cost_pct)

            # token bar
            used_tok_pct = today_tok / DAILY_TOKEN_LIMIT if DAILY_TOKEN_LIMIT else 0
            rem_tok_pct  = remaining_tok / DAILY_TOKEN_LIMIT if DAILY_TOKEN_LIMIT else 0
            tok_col = (C["danger"] if used_tok_pct >= 0.90 else
                       C["warn"]   if used_tok_pct >= 0.70 else C["used"])
            self.lbl_tok_used.config(text=fmt_tok(today_tok), fg=tok_col)
            self.lbl_tok_rem.config(text=f"{fmt_tok(remaining_tok)} left")
            self.bar_tok.set(used_tok_pct, rem_tok_pct)

            # sessions + status
            n_sess  = len(today["sessions"])
            n_files = len(list(self.data_dir.rglob("*.jsonl")))
            self.lbl_sess.config(
                text=f"{n_sess} session(s)  |  {fmt_cost(session_cost)} this session")
            self.lbl_status.config(
                text=f"updated {now}  •  {n_files} file(s)"
                if n_files else f"updated {now}  •  no session files yet")

        except Exception as exc:
            self.lbl_status.config(text=f"Error: {exc}")

        self._aid = self.root.after(REFRESH_INTERVAL_MS, self._refresh)


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ClaudeGadget()
