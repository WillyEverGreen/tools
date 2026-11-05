@echo off
rem Tesseract OCR (portable). Keeps the engine in C:\tools\tesseract-bin and points it at its language data.
set "TESSDATA_PREFIX=%~dp0tesseract-bin\tessdata"
"%~dp0tesseract-bin\tesseract.exe" %*
