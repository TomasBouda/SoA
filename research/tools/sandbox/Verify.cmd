@echo off
rem Verifies the game package on clean Windows. A different path to the package
rem is passed as an argument:  Verify.cmd D:\somewhere\SoA-Package
setlocal
if "%~1"=="" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0verify.ps1"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0verify.ps1" -Package "%~1"
)
pause
