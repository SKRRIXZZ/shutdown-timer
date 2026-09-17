@echo off
cd /d "%~dp0"

set "PY=python"
where py >nul 2>nul
if not errorlevel 1 set "PY=py"

%PY% -m PyInstaller --version >nul 2>nul
if errorlevel 1 %PY% -m pip install --upgrade pyinstaller

%PY% -c "import pystray, PIL" >nul 2>nul
if errorlevel 1 %PY% -m pip install --upgrade pystray Pillow

%PY% -c "import keyboard" >nul 2>nul
if errorlevel 1 %PY% -m pip install --upgrade keyboard

set "ICON="
if exist icon.ico set "ICON=--icon=icon.ico"

%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --name=ShutdownTimer %ICON% --hidden-import=pystray._win32 --hidden-import=PIL._tkinter_finder --hidden-import=keyboard --collect-all pystray --collect-all PIL shutdown_timer_multilang.pyw

echo.
echo DONE. See dist\ShutdownTimer.exe
pause