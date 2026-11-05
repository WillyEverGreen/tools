@echo off
rem Tesseract OCR (portable). Keeps the engine in vendor\tesseract-bin and points it at its language data.
set "TESSDATA_PREFIX=%~dp0..\vendor\tesseract-bin\tessdata"
"%~dp0..\vendor\tesseract-bin\tesseract.exe" %*
