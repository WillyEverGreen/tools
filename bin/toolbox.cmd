@echo off
if exist "%USERPROFILE%\tools\Toolbox\toolbox.cmd" (
  "%USERPROFILE%\tools\Toolbox\toolbox.cmd" %*
) else (
  echo Toolbox not found at %%USERPROFILE%%\tools\Toolbox\toolbox.cmd.
)
