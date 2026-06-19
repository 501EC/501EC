#!/usr/bin/env python3
"""
Claude Code Usage Monitor — Floating Desktop Gadget (Windows x64)
Reads local Claude Code session files and shows live token/cost usage.
Right-click the gadget to access settings or exit.
Drag anywhere to reposition.
"""

import tkinter as tk
import json
import os
from datetime import date
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIG  (edit these to match your plan / budget)
# ─────────────────────────────────────────────────────────────────────────────
REFRESH_INTERVAL_MS = 60_000      # How often to re-scan (ms). 60 000 = 1 min.
MONTHLY_COST_LIMIT_USD = 50.0     # Your monthly budget in USD.
DAILY_TOKEN_LIMIT = 1_500_000     # Soft daily token ceiling (for the bar).

# Anthropic API pricing — USD per 1 M tokens (Sonnet 4.x default)
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
    "bg3":     "#21262d",
    "accent":  "#7c3aed",
    "text":    "#e6edf3",
    "dim":     "#8b949e",
    "green":   "#3fb950",
    "yellow":  "#d29922",
    "red":     "#f85149",
    "blue":    "#58a6ff",
    "border":  "#30363d",
}

FONT_MAIN  = ("Segoe UI", 9)
FONT_BOLD  = ("Segoe UI", 9, "bold")
FONT_SMALL = ("Segoe UI", 7)
FONT_BIG   = ("Segoe UI", 18, "bold")


# ─────────────────────────────────────────────────────────────────────────────
#  DATA LAYER
# ─────────────────────────────────────────────────────────────────────────────

def find_claude_dir() -> Path | None:
    """Return the Claude Code 'projects' directory for the current OS."""
    candidates = [
        # Windows — installed via winget / installer
        Path(os.environ.get("APPDATA", "")) / "Claude" / "projects",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Claude" / "projects",
        # Windows WSL / cross-platform fallback
        Path.home() / ".claude" / "projects",
        # macOS
        Path.home() / "Library" / "Application Support" / "Claude" / "projects",
    ]
    for p in candidates:
        if p.is_dir():
            return p
    return None


def parse_usage(data_dir: Path, today_only: bool = False) -> dict:
    """
    Walk all JSONL session files and aggregate token counts.
    Deduplication is done on the API message ID so that messages stored
    multiple times (e.g. queue entries) are counted only once.
    """
    seen_ids: set[str] = set()
    totals = {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0,
              "sessions": set(), "messages": 0}
    today = date.today().isoformat()

    for jfile in data_dir.rglob("*.jsonl"):
        try:
            with open(jfile, encoding="utf-8", errors="replace") as fh:
                for raw in fh:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        entry = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    msg = entry.get("message")
                    if not isinstance(msg, dict):
                        continue

                    usage = msg.get("usage")
                    if not isinstance(usage, dict):
                        continue

                    # Skip if we already counted this API response
                    msg_id = msg.get("id", "")
                    if msg_id and msg_id in seen_ids:
                        continue
                    if msg_id:
                        seen_ids.add(msg_id)

                    # Date filter
                    if today_only:
                        ts = entry.get("timestamp", "")
                        if not ts.startswith(today):
                            continue

                    totals["input"]       += usage.get("input_tokens", 0)
                    totals["output"]      += usage.get("output_tokens", 0)
                    totals["cache_write"] += usage.get("cache_creation_input_tokens", 0)
                    totals["cache_read"]  += usage.get("cache_read_input_tokens", 0)
                    totals["messages"]    += 1
                    sid = entry.get("sessionId")
                    if sid:
                        totals["sessions"].add(sid)
        except Exception:
            continue

    return totals


def calc_cost(u: dict) -> float:
    return (
        u["input"]       * PRICING["input"]       +
        u["output"]      * PRICING["output"]      +
        u["cache_write"] * PRICING["cache_write"] +
        u["cache_read"]  * PRICING["cache_read"]
    ) / 1_000_000


def fmt_tok(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


# ─────────────────────────────────────────────────────────────────────────────
#  MINI PROGRESS BAR WIDGET
# ─────────────────────────────────────────────────────────────────────────────

class Bar(tk.Canvas):
    H = 6
    R = 3

    def __init__(self, parent, width=238, **kw):
        super().__init__(parent, width=width, height=self.H,
                         bg=C["bg"], highlightthickness=0, **kw)
        self._w = width
        self._pct = 0.0

    def set(self, pct: float):
        self._pct = max(0.0, min(1.0, pct))
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h, r = self._w, self.H, self.R
        self._rrect(0, 0, w, h, r, fill=C["bg3"])
        if self._pct > 0:
            fw = max(2 * r, int(w * self._pct))
            color = (C["green"] if self._pct < 0.70
                     else C["yellow"] if self._pct < 0.90
                     else C["red"])
            self._rrect(0, 0, fw, h, r, fill=color)

    def _rrect(self, x1, y1, x2, y2, r, **kw):
        kw.setdefault("outline", "")
        arc_kw = {**kw, "style": "pieslice"}
        self.create_arc(x1, y1, x1+2*r, y1+2*r, start=90,  extent=90, **arc_kw)
        self.create_arc(x2-2*r, y1, x2, y1+2*r, start=0,   extent=90, **arc_kw)
        self.create_arc(x1, y2-2*r, x1+2*r, y2, start=180, extent=90, **arc_kw)
        self.create_arc(x2-2*r, y2-2*r, x2, y2, start=270, extent=90, **arc_kw)
        self.create_rectangle(x1+r, y1, x2-r, y2, **kw)
        self.create_rectangle(x1, y1+r, x2, y2-r, **kw)


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN GADGET
# ─────────────────────────────────────────────────────────────────────────────

class ClaudeGadget:
    W, H = 270, 340

    def __init__(self):
        self.root = tk.Tk()
        self._setup_window()
        self._build_ui()
        self._build_menu()
        self.data_dir = find_claude_dir()
        self._refresh()           # first paint, schedules future refreshes
        self.root.mainloop()

    # ── Window setup ──────────────────────────────────────────────────────────

    def _setup_window(self):
        r = self.root
        r.title("Claude Usage")
        r.configure(bg=C["bg"])
        r.resizable(False, False)

        # Position: top-right corner, 20 px from edge
        r.update_idletasks()
        sw = r.winfo_screenwidth()
        r.geometry(f"{self.W}x{self.H}+{sw - self.W - 20}+40")

        # Go frameless after geometry is set (avoids invisible-window bug)
        r.overrideredirect(True)
        r.attributes("-topmost", True)
        r.attributes("-alpha", 0.94)

        # Force the window to the front
        r.lift()
        r.after(100, lambda: r.attributes("-topmost", True))

        # Drag support
        r.bind("<Button-1>",   self._drag_start)
        r.bind("<B1-Motion>",  self._drag_move)

    # ── UI construction ───────────────────────────────────────────────────────

    def _lbl(self, parent, text="", fg=None, font=None, **kw):
        return tk.Label(parent, text=text, bg=C["bg"],
                        fg=fg or C["text"], font=font or FONT_MAIN, **kw)

    def _sep(self, parent):
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", pady=6)

    def _build_ui(self):
        pad = {"padx": 14}
        root = self.root

        # ── Header ──────────────────────────────────────────────────────────
        hdr = tk.Frame(root, bg=C["bg"])
        hdr.pack(fill="x", padx=14, pady=(12, 0))

        tk.Label(hdr, text="◈", bg=C["bg"], fg=C["accent"],
                 font=("Segoe UI", 11, "bold")).pack(side="left")
        tk.Label(hdr, text=" Claude Code", bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        self.lbl_clock = tk.Label(hdr, text="", bg=C["bg"], fg=C["dim"],
                                  font=FONT_SMALL)
        self.lbl_clock.pack(side="right")

        tk.Frame(root, bg=C["border"], height=1).pack(fill="x", padx=14, pady=(8, 0))

        body = tk.Frame(root, bg=C["bg"])
        body.pack(fill="both", expand=True, **pad)

        # ── Today ───────────────────────────────────────────────────────────
        tk.Label(body, text="TODAY", bg=C["bg"], fg=C["dim"],
                 font=FONT_SMALL).pack(anchor="w", pady=(8, 0))

        self.lbl_today_cost = tk.Label(body, text="$0.000",
                                       bg=C["bg"], fg=C["text"], font=FONT_BIG)
        self.lbl_today_cost.pack(anchor="w")

        self.lbl_today_detail = tk.Label(body, text="— tokens  •  — msgs",
                                         bg=C["bg"], fg=C["dim"], font=FONT_SMALL)
        self.lbl_today_detail.pack(anchor="w")

        self.bar_today = Bar(body, width=242)
        self.bar_today.pack(anchor="w", pady=(5, 2))

        self.lbl_limit_caption = tk.Label(
            body, text=f"Monthly budget: ${MONTHLY_COST_LIMIT_USD:.0f}",
            bg=C["bg"], fg=C["dim"], font=FONT_SMALL)
        self.lbl_limit_caption.pack(anchor="w")

        tk.Frame(body, bg=C["border"], height=1).pack(fill="x", pady=(10, 0))

        # ── Token breakdown ─────────────────────────────────────────────────
        tk.Label(body, text="ALL TIME", bg=C["bg"], fg=C["dim"],
                 font=FONT_SMALL).pack(anchor="w", pady=(8, 2))

        grid = tk.Frame(body, bg=C["bg"])
        grid.pack(fill="x")

        def row(label, color=C["text"]):
            f = tk.Frame(grid, bg=C["bg"])
            f.pack(fill="x", pady=1)
            tk.Label(f, text=label, bg=C["bg"], fg=C["dim"],
                     font=FONT_SMALL, width=14, anchor="w").pack(side="left")
            v = tk.Label(f, text="—", bg=C["bg"], fg=color,
                         font=("Segoe UI", 8, "bold"))
            v.pack(side="right")
            return v

        self.lbl_total_cost    = row("Total cost",    C["blue"])
        self.lbl_input_tok     = row("Input tokens",  C["text"])
        self.lbl_output_tok    = row("Output tokens", C["text"])
        self.lbl_cache_write   = row("Cache created", C["dim"])
        self.lbl_cache_read    = row("Cache hits",    C["green"])
        self.lbl_sessions      = row("Sessions",      C["text"])

        tk.Frame(body, bg=C["border"], height=1).pack(fill="x", pady=(10, 0))

        # ── Status ──────────────────────────────────────────────────────────
        self.lbl_status = tk.Label(body, text="Starting…",
                                   bg=C["bg"], fg=C["dim"], font=FONT_SMALL,
                                   wraplength=240, justify="left")
        self.lbl_status.pack(anchor="w", pady=(6, 0))

        # ── Footer hint ─────────────────────────────────────────────────────
        tk.Label(root, text="right-click for options  •  drag to move",
                 bg=C["bg"], fg=C["border"], font=("Segoe UI", 6)).pack(pady=(4, 6))

    # ── Context menu ──────────────────────────────────────────────────────────

    def _build_menu(self):
        m = tk.Menu(self.root, tearoff=0, bg=C["bg2"], fg=C["text"],
                    activebackground=C["accent"], activeforeground=C["text"],
                    font=FONT_MAIN)
        m.add_command(label="⟳  Refresh now",   command=self._refresh_now)
        m.add_separator()
        m.add_command(label="📂  Open data folder", command=self._open_data_dir)
        m.add_separator()
        m.add_command(label="✕  Exit",           command=self.root.destroy)
        self.menu = m
        self.root.bind("<Button-3>", self._show_menu)

    def _show_menu(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)

    def _open_data_dir(self):
        if self.data_dir and self.data_dir.exists():
            os.startfile(str(self.data_dir))  # Windows explorer

    # ── Drag ─────────────────────────────────────────────────────────────────

    def _drag_start(self, e):
        self._ox, self._oy = e.x, e.y

    def _drag_move(self, e):
        x = self.root.winfo_x() + (e.x - self._ox)
        y = self.root.winfo_y() + (e.y - self._oy)
        self.root.geometry(f"+{x}+{y}")

    # ── Refresh logic ────────────────────────────────────────────────────────

    def _refresh_now(self):
        """Cancel pending timer and refresh immediately."""
        if hasattr(self, "_after_id"):
            self.root.after_cancel(self._after_id)
        self._refresh()

    def _refresh(self):
        from datetime import datetime
        now_str = datetime.now().strftime("%H:%M:%S")
        self.lbl_clock.config(text=now_str)

        if not self.data_dir:
            self.lbl_status.config(
                text="⚠ Claude data folder not found.\n"
                     "Make sure Claude Code is installed.")
            self._after_id = self.root.after(REFRESH_INTERVAL_MS, self._refresh)
            return

        try:
            today   = parse_usage(self.data_dir, today_only=True)
            alltime = parse_usage(self.data_dir, today_only=False)

            today_cost  = calc_cost(today)
            all_cost    = calc_cost(alltime)
            today_total = (today["input"] + today["output"] +
                           today["cache_write"] + today["cache_read"])

            # Today panel
            cost_color = (C["green"] if today_cost < MONTHLY_COST_LIMIT_USD * 0.7
                          else C["yellow"] if today_cost < MONTHLY_COST_LIMIT_USD * 0.9
                          else C["red"])
            self.lbl_today_cost.config(text=f"${today_cost:.3f}", fg=cost_color)
            self.lbl_today_detail.config(
                text=f"{fmt_tok(today_total)} tokens  •  {today['messages']} messages")
            self.bar_today.set(today_cost / MONTHLY_COST_LIMIT_USD)

            # All-time table
            self.lbl_total_cost.config(text=f"${all_cost:.3f}")
            self.lbl_input_tok.config(text=fmt_tok(alltime["input"]))
            self.lbl_output_tok.config(text=fmt_tok(alltime["output"]))
            self.lbl_cache_write.config(text=fmt_tok(alltime["cache_write"]))
            self.lbl_cache_read.config(text=fmt_tok(alltime["cache_read"]))
            self.lbl_sessions.config(text=str(len(alltime["sessions"])))

            jfiles = list(self.data_dir.rglob("*.jsonl"))
            self.lbl_status.config(
                text=f"✓ Watching {len(jfiles)} session file(s)  "
                     f"•  next refresh in 60 s")

        except Exception as exc:
            self.lbl_status.config(text=f"⚠ {exc}")

        # Schedule next refresh — no threads, minimal CPU
        self._after_id = self.root.after(REFRESH_INTERVAL_MS, self._refresh)


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ClaudeGadget()
