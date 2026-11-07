' C:\tools\scripts\9router.vbs
' Launches 9Router supervisor and watchdog silently with SW_HIDE (0)
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""C:\tools\scripts\9router-supervisor.ps1""", 0, False
WshShell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""C:\tools\scripts\9router-watchdog.ps1""", 0, False
