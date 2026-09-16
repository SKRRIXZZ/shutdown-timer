@echo off
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --onefile --windowed --icon=icon.ico --name=ShutdownTimer "shutdown_timer_multilang.pyw"
echo.
echo Done: dist\ShutdownTimer.exe
pause
