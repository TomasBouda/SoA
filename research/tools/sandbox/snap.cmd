@echo off
rem A screenshot from the sandbox to the host through the mapped folder.
rem   snap.cmd        in 5 seconds
rem   snap.cmd 10     in 10 seconds
rem   snap.cmd 5 3    three shots five seconds apart
setlocal
set DELAY=%~1
set COUNT=%~2
if "%DELAY%"=="" set DELAY=5
if "%COUNT%"=="" set COUNT=1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0snap.ps1" -Delay %DELAY% -Count %COUNT%
timeout /t 3 >nul
