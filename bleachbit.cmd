@echo off
rem BleachBit console. Always --preview before --clean.
if exist "%USERPROFILE%\tools\BleachBit\BleachBit-Portable\bleachbit_console.exe" (
  "%USERPROFILE%\tools\BleachBit\BleachBit-Portable\bleachbit_console.exe" %*
) else if exist "C:\Program Files (x86)\BleachBit\bleachbit_console.exe" (
  "C:\Program Files (x86)\BleachBit\bleachbit_console.exe" %*
) else (
  echo BleachBit console not found in %%USERPROFILE%%\tools or Program Files.
)
