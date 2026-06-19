# Claude Code Usage Monitor — Installation Guide

A lightweight floating dashboard that shows your Claude Code token and cost usage
in real time. Reads directly from Claude Code's local session files — no API key needed.

---

## What it shows

| Panel | Info |
|---|---|
| **TODAY** | Cost so far today + token count + progress bar |
| **ALL TIME** | Total cost, input/output/cache token breakdown, session count |

The progress bar turns **yellow** at 70 % of your monthly budget and **red** at 90 %.

---

## Prerequisites

- Windows 10/11 x64
- [Python 3.10+](https://www.python.org/downloads/) — tick **"Add Python to PATH"** during setup
- Claude Code CLI installed and at least one session run

> **tkinter** ships with the standard Python installer. No extra `pip install` needed.

---

## Install (2 steps)

1. **Download** `claude_usage_gadget.py` and `install_gadget.bat` into the same folder  
   (e.g. `Downloads\ClaudeGadget\`)

2. **Double-click `install_gadget.bat`** and follow the prompts:
   - Creates `%USERPROFILE%\ClaudeGadget\` with the script
   - Puts a shortcut on your Desktop
   - Optionally adds itself to Windows Startup (auto-launch on login)
   - Optionally launches the gadget immediately

---

## Customise

Open `claude_usage_gadget.py` in Notepad and edit the CONFIG block near the top:

```python
REFRESH_INTERVAL_MS   = 60_000   # 60 000 ms = refresh every 60 seconds
MONTHLY_COST_LIMIT_USD = 50.0    # your monthly spend ceiling in USD
DAILY_TOKEN_LIMIT      = 1_500_000  # soft daily token cap for the bar
```

Pricing constants are also there if you switch models.

---

## Usage

| Action | Result |
|---|---|
| **Drag** anywhere on the widget | Move it around the screen |
| **Right-click** | Menu: Refresh now / Open data folder / Exit |
| Closes with the **✕ Exit** menu item | Gadget exits; no tray icon left behind |

The gadget uses `pythonw.exe` (no console window) and refreshes via tkinter's
`after()` timer — it consumes < 0.1 % CPU at idle.

---

## Where Claude Code stores data

| OS | Path |
|---|---|
| Windows | `%APPDATA%\Claude\projects\` |
| macOS | `~/Library/Application Support/Claude/projects/` |
| Linux / WSL | `~/.claude/projects/` |

The gadget checks all three locations automatically.

---

## Uninstall

1. Right-click the gadget → **Exit**
2. Delete `%USERPROFILE%\ClaudeGadget\`
3. Delete `Desktop\Claude Usage Gadget.lnk`
4. If you enabled auto-start, delete the shortcut from  
   `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\`
