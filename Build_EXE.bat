@echo off
cd /d "%~dp0"
py -m pip install --upgrade pyinstaller
if errorlevel 1 (echo PyInstaller installation failed & pause & exit /b 1)
py -m PyInstaller --noconfirm --clean --onefile --windowed --name Windows-IP-Switcher IP_Switcher.py
if errorlevel 1 (echo Build failed & pause & exit /b 1)
echo EXE: dist\Windows-IP-Switcher.exe
pause
