@echo off
setlocal EnableDelayedExpansion
title Claude Usage Gadget — Installer

echo.
echo  ╔═══════════════════════════════════════════════╗
echo  ║    Claude Code Usage Monitor — Installer      ║
echo  ╚═══════════════════════════════════════════════╝
echo.

:: ── 1. Check Python ──────────────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found in PATH.
    echo.
    echo  Please install Python 3.10+ from https://www.python.org/downloads/
    echo  Make sure to tick "Add Python to PATH" during setup.
    echo.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%V in ('python --version 2^>^&1') do set PY_VER=%%V
echo  [OK] Python %PY_VER% found.

:: ── 2. Check tkinter (included with standard Python installs) ─────────────
python -c "import tkinter" 2>nul
if errorlevel 1 (
    echo  [ERROR] tkinter not available.
    echo  Reinstall Python from python.org (choose 'Custom install' and
    echo  make sure 'tcl/tk and IDLE' is checked).
    pause
    exit /b 1
)
echo  [OK] tkinter available.

:: ── 3. Determine install folder ───────────────────────────────────────────
set "INSTALL_DIR=%USERPROFILE%\ClaudeGadget"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: ── 4. Copy gadget script ─────────────────────────────────────────────────
set "SCRIPT_SRC=%~dp0claude_usage_gadget.py"
if not exist "%SCRIPT_SRC%" (
    echo  [ERROR] claude_usage_gadget.py not found next to this installer.
    echo  Make sure both files are in the same folder.
    pause
    exit /b 1
)

copy /Y "%SCRIPT_SRC%" "%INSTALL_DIR%\claude_usage_gadget.py" >nul
echo  [OK] Gadget copied to %INSTALL_DIR%

:: ── 5. Create launcher .bat ───────────────────────────────────────────────
set "LAUNCHER=%INSTALL_DIR%\run_gadget.bat"
(
    echo @echo off
    echo start "" /B pythonw "%INSTALL_DIR%\claude_usage_gadget.py"
) > "%LAUNCHER%"
echo  [OK] Launcher created: %LAUNCHER%

:: ── 6. Create Desktop shortcut via PowerShell ────────────────────────────
set "SHORTCUT=%USERPROFILE%\Desktop\Claude Usage Gadget.lnk"
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $s  = $ws.CreateShortcut('%SHORTCUT%'); ^
   $s.TargetPath   = 'pythonw.exe'; ^
   $s.Arguments    = '\"%INSTALL_DIR%\claude_usage_gadget.py\"'; ^
   $s.WorkingDirectory = '%INSTALL_DIR%'; ^
   $s.Description  = 'Claude Code Usage Monitor'; ^
   $s.Save()"

if exist "%SHORTCUT%" (
    echo  [OK] Desktop shortcut created.
) else (
    echo  [WARN] Shortcut creation failed — you can still run run_gadget.bat manually.
)

:: ── 7. Optionally add to Startup folder ──────────────────────────────────
echo.
set /p ADD_STARTUP=  Start gadget automatically at Windows login? [Y/N]:
if /i "%ADD_STARTUP%"=="Y" (
    set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
    set "STARTUP_LINK=!STARTUP_DIR!\Claude Usage Gadget.lnk"
    powershell -NoProfile -Command ^
      "$ws = New-Object -ComObject WScript.Shell; ^
       $s  = $ws.CreateShortcut('!STARTUP_LINK!'); ^
       $s.TargetPath   = 'pythonw.exe'; ^
       $s.Arguments    = '\"%INSTALL_DIR%\claude_usage_gadget.py\"'; ^
       $s.WorkingDirectory = '%INSTALL_DIR%'; ^
       $s.Save()"
    echo  [OK] Added to Windows Startup.
) else (
    echo  [--] Skipped auto-start.
)

:: ── 8. Launch now ─────────────────────────────────────────────────────────
echo.
set /p LAUNCH_NOW=  Launch the gadget now? [Y/N]:
if /i "%LAUNCH_NOW%"=="Y" (
    start "" /B pythonw "%INSTALL_DIR%\claude_usage_gadget.py"
    echo  [OK] Gadget launched — look for it in the top-right corner.
)

echo.
echo  ══════════════════════════════════════════════════
echo   Installation complete!
echo   Shortcut:  %SHORTCUT%
echo   Script:    %INSTALL_DIR%\claude_usage_gadget.py
echo  ══════════════════════════════════════════════════
echo.
pause
