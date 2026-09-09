@echo off
rem Forcing a save backup by hand - the same logic as after a session ends:
rem a snapshot of a new generation and mirroring, deletions included.
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\SoA\_sandbox\backup-saves.ps1"
pause
