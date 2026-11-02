# Windows IP Switcher v3.0

Windows 10/11 GUI utility for managing static IPv4 and DHCP profiles using Python Tkinter and built-in Windows netsh commands.

## Features
- Select and refresh Windows network adapters
- Create, save, update and delete named IP profiles
- Apply static IPv4, subnet mask, optional gateway and DNS
- Restore DHCP for IPv4 and DNS
- Show current adapter configuration
- Check external public IPv4 over HTTPS and copy to clipboard
- Build a single-file Windows executable using PyInstaller

## Run
Requires Windows 10/11 and Python 3. Run `Run_Python.bat` or `py IP_Switcher.py`. Accept UAC elevation to make network changes.

## EXE build
Run `Build_EXE.bat` on Windows with Python and internet access (to install PyInstaller). The portable app appears under `dist/Windows-IP-Switcher.exe`; other PCs do not need Python.

## Profiles
Local profiles live at `%APPDATA%\WindowsIPSwitcher\profiles.json`. Profiles are *not* bundled with the EXE or shared across PCs. Default MikroTik/OLT/ONU addresses are examples. Review addressing before clicking Apply.

## Important safety notes
Changing the active adapter IP can interrupt connectivity, especially on remote machines. Always select the intended adapter. Do not commit local network profiles or credentials. Public IP lookup reports the outward-facing address; under CGNAT/VPN it may differ from router WAN IP.

## Runtime dependencies
Python 3 standard library only: tkinter, subprocess, ipaddress, urllib, etc. PyInstaller is only needed for packaging.

## v3.1: Current IP display
Click **Show Current IP** to open a separate resizable, scrollable configuration window. The main activity log is also larger and easier to read. Rebuild the EXE using Build_EXE.bat after pulling the latest source.
