@echo off
setlocal EnableDelayedExpansion
title Claude Usage Gadget - Installer

echo.
echo  === Claude Code Usage Monitor - Installer ===
echo.

:: ── 1. Find a Python with tkinter ────────────────────────────────────────────
set "PYEXE="

:: Check candidates in order of preference
for %%P in (
    "C:\Program Files\Python312\python.exe"
    "C:\Program Files\Python313\python.exe"
    "C:\Program Files\Python311\python.exe"
    "C:\Program Files\Python310\python.exe"
    "C:\Python314\python.exe"
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
) do (
    if exist %%P (
        %%P -c "import tkinter" >nul 2>&1
        if not errorlevel 1 (
            if "!PYEXE!"=="" set "PYEXE=%%~P"
        )
    )
)

:: Also try whatever 'python' resolves to in PATH (skip WindowsApps)
if "!PYEXE!"=="" (
    for /f "delims=" %%F in ('where python 2^>nul') do (
        echo %%F | findstr /i "WindowsApps" >nul
        if errorlevel 1 (
            %%F -c "import tkinter" >nul 2>&1
            if not errorlevel 1 (
                if "!PYEXE!"=="" set "PYEXE=%%F"
            )
        )
    )
)

if "!PYEXE!"=="" (
    echo  [ERROR] No Python with tkinter found.
    echo.
    echo  You have Python installed but tkinter is missing.
    echo  Fix: Open the Python installer again, choose 'Modify',
    echo  and make sure 'tcl/tk and IDLE' is ticked.
    echo.
    echo  Alternatively reinstall from https://www.python.org/downloads/
    echo  using 'Customize installation' and tick 'tcl/tk and IDLE'.
    echo.
    pause
    exit /b 1
)

:: Derive pythonw.exe path from python.exe
set "PYWEXE=!PYEXE:python.exe=pythonw.exe!"
if not exist "!PYWEXE!" set "PYWEXE=!PYEXE!"

for /f "tokens=2 delims= " %%V in ('"!PYEXE!" --version 2^>^&1') do set PY_VER=%%V
echo  [OK] Using Python !PY_VER! at !PYEXE!
echo  [OK] tkinter available.

:: ── 2. Determine install folder ───────────────────────────────────────────────
set "INSTALL_DIR=%USERPROFILE%\ClaudeGadget"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: ── 3. Copy gadget script ─────────────────────────────────────────────────────
set "SCRIPT_SRC=%~dp0claude_usage_gadget.py"
if not exist "%SCRIPT_SRC%" (
    echo  [ERROR] claude_usage_gadget.py not found next to this installer.
    echo  Make sure both files are in the same folder.
    pause
    exit /b 1
)

copy /Y "%SCRIPT_SRC%" "%INSTALL_DIR%\claude_usage_gadget.py" >nul
echo  [OK] Gadget copied to %INSTALL_DIR%

:: ── 4. Write launcher that uses the correct python ────────────────────────────
set "LAUNCHER=%INSTALL_DIR%\run_gadget.bat"
(
    echo @echo off
    echo start "" /B "!PYWEXE!" "%INSTALL_DIR%\claude_usage_gadget.py"
) > "%LAUNCHER%"
echo  [OK] Launcher created: %LAUNCHER%

:: ── 5. Desktop shortcut ───────────────────────────────────────────────────────
set "SHORTCUT=%USERPROFILE%\Desktop\Claude Usage Gadget.lnk"
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT%'); $s.TargetPath = '!PYWEXE!'; $s.Arguments = '\"%INSTALL_DIR%\claude_usage_gadget.py\"'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.Description = 'Claude Code Usage Monitor'; $s.Save()"

if exist "%SHORTCUT%" (
    echo  [OK] Desktop shortcut created.
) else (
    echo  [WARN] Shortcut creation failed - run run_gadget.bat manually.
)

:: ── 6. Add to Startup? ────────────────────────────────────────────────────────
echo.
set /p ADD_STARTUP=  Auto-start at Windows login? [Y/N]:
if /i "!ADD_STARTUP!"=="Y" (
    set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
    powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('!STARTUP_DIR!\Claude Usage Gadget.lnk'); $s.TargetPath = '!PYWEXE!'; $s.Arguments = '\"%INSTALL_DIR%\claude_usage_gadget.py\"'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.Save()"
    echo  [OK] Added to Windows Startup.
) else (
    echo  [--] Skipped auto-start.
)

:: ── 7. Launch now? ────────────────────────────────────────────────────────────
echo.
set /p LAUNCH_NOW=  Launch the gadget now? [Y/N]:
if /i "!LAUNCH_NOW!"=="Y" (
    start "" /B "!PYWEXE!" "%INSTALL_DIR%\claude_usage_gadget.py"
    echo  [OK] Gadget launched - look for it in the top-right corner of your screen.
)

echo.
echo  ============================================
echo   Done!
echo   Script : %INSTALL_DIR%\claude_usage_gadget.py
echo   Launch : %INSTALL_DIR%\run_gadget.bat
echo   Python : !PYEXE!
echo  ============================================
echo.
pause
