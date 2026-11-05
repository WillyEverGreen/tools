@echo off
rem `sg` is the old name of ast-grep. The sg.exe binary now prints a deprecation banner on every call
rem (wasted tokens), so this shim calls ast-grep directly.
"%~dp0ast-grep.exe" %*
