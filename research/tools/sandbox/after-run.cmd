@echo off
rem Check after playing - what the launcher set and what the game left behind.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0after-run.ps1"
pause
