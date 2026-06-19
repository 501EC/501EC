"""
Claude Code Usage Monitor - Installer
Run with:  python install_gadget.py
"""

import sys
import os
import shutil
import subprocess
from pathlib import Path


def pause():
    input("\nPress Enter to exit...")


def find_python_with_tkinter():
    """Return (python_exe, pythonw_exe) for a Python that has tkinter."""
    candidates = [
        r"C:\Program Files\Python313\python.exe",
        r"C:\Program Files\Python312\python.exe",
        r"C:\Program Files\Python311\python.exe",
        r"C:\Program Files\Python310\python.exe",
        r"C:\Python314\python.exe",
        r"C:\Python313\python.exe",
        r"C:\Python312\python.exe",
        r"C:\Python311\python.exe",
        r"C:\Python310\python.exe",
        sys.executable,  # whatever ran this script
    ]

    for exe in candidates:
        exe = Path(exe)
        if not exe.exists():
            continue
        # Skip Microsoft Store stub
        if "WindowsApps" in str(exe):
            continue
        result = subprocess.run(
            [str(exe), "-c", "import tkinter"],
            capture_output=True
        )
        if result.returncode == 0:
            pyw = exe.parent / "pythonw.exe"
            if not pyw.exists():
                pyw = exe
            return exe, pyw

    return None, None


def create_shortcut(link_path: Path, target: Path, args: str, workdir: Path):
    """Create a Windows .lnk shortcut via PowerShell."""
    ps = (
        f'$ws = New-Object -ComObject WScript.Shell; '
        f'$s = $ws.CreateShortcut("{link_path}"); '
        f'$s.TargetPath = "{target}"; '
        f'$s.Arguments = "{args}"; '
        f'$s.WorkingDirectory = "{workdir}"; '
        f'$s.Save()'
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                   capture_output=True)


def main():
    print()
    print("  === Claude Code Usage Monitor - Installer ===")
    print()

    # ── 1. Find usable Python ────────────────────────────────────────────────
    print("  Searching for Python with tkinter...")
    py_exe, pyw_exe = find_python_with_tkinter()

    if py_exe is None:
        print()
        print("  [ERROR] No Python installation with tkinter found.")
        print()
        print("  Fix: reinstall Python from https://www.python.org/downloads/")
        print("  During setup choose 'Customize installation' and")
        print("  make sure 'tcl/tk and IDLE' is ticked.")
        pause()
        sys.exit(1)

    result = subprocess.run([str(py_exe), "--version"], capture_output=True, text=True)
    ver = result.stdout.strip() or result.stderr.strip()
    print(f"  [OK] {ver} found at {py_exe}")
    print(f"  [OK] tkinter available")

    # ── 2. Find gadget script ────────────────────────────────────────────────
    here = Path(__file__).parent
    src = here / "claude_usage_gadget.py"
    if not src.exists():
        print()
        print("  [ERROR] claude_usage_gadget.py not found.")
        print(f"  Expected it next to this installer in: {here}")
        pause()
        sys.exit(1)

    # ── 3. Install to user folder ────────────────────────────────────────────
    install_dir = Path.home() / "ClaudeGadget"
    install_dir.mkdir(exist_ok=True)
    dest = install_dir / "claude_usage_gadget.py"
    shutil.copy2(src, dest)
    print(f"  [OK] Gadget copied to {install_dir}")

    # ── 4. Write launcher .bat ───────────────────────────────────────────────
    launcher = install_dir / "run_gadget.bat"
    launcher.write_text(
        f'@echo off\nstart "" /B "{pyw_exe}" "{dest}"\n',
        encoding="utf-8"
    )
    print(f"  [OK] Launcher created: {launcher}")

    # ── 5. Desktop shortcut ──────────────────────────────────────────────────
    desktop = Path.home() / "Desktop"
    shortcut = desktop / "Claude Usage Gadget.lnk"
    create_shortcut(shortcut, pyw_exe, f'"{dest}"', install_dir)
    if shortcut.exists():
        print(f"  [OK] Desktop shortcut created")
    else:
        print(f"  [WARN] Shortcut creation failed - use run_gadget.bat instead")

    # ── 6. Auto-start option ─────────────────────────────────────────────────
    print()
    ans = input("  Auto-start at Windows login? [Y/N]: ").strip().lower()
    if ans == "y":
        startup = (Path(os.environ["APPDATA"])
                   / "Microsoft" / "Windows" / "Start Menu"
                   / "Programs" / "Startup")
        create_shortcut(startup / "Claude Usage Gadget.lnk",
                        pyw_exe, f'"{dest}"', install_dir)
        print("  [OK] Added to Windows Startup")
    else:
        print("  [--] Skipped auto-start")

    # ── 7. Launch now ────────────────────────────────────────────────────────
    print()
    ans = input("  Launch the gadget now? [Y/N]: ").strip().lower()
    if ans == "y":
        subprocess.Popen([str(pyw_exe), str(dest)],
                         creationflags=subprocess.DETACHED_PROCESS)
        print("  [OK] Gadget launched - look for it in the top-right corner")

    print()
    print("  ============================================")
    print("   Installation complete!")
    print(f"  Script : {dest}")
    print(f"  Launch : {launcher}")
    print(f"  Python : {py_exe}")
    print("  ============================================")
    pause()


if __name__ == "__main__":
    main()
