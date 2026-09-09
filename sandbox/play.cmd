@echo off
rem A launcher wrapper: starts the game, waits for it to end and then backs up
rem the saved games, the graphics settings and the content created in the game.
rem
rem Usage:  play.cmd        = the game
rem         play.cmd -o     = the graphics configuration dialog
setlocal
set GAME=C:\Game
set CFG=C:\SoA\_sandbox\config
set REGKEY=HKCU\Software\Silver Style Entertainment

if not exist "%GAME%\soa.exe" (
    echo [ERROR] %GAME%\soa.exe does not exist - did you run prepare.cmd?
    pause
    exit /b 1
)

echo Starting soa.exe %*
echo (once the game ends the saves, the settings and any new missions are backed up automatically)
echo.
start "" /wait "%GAME%\soa.exe" %*

echo.
echo ============================================================
echo  The game has ended - backing up
echo ============================================================

rem --- saved games: a generation snapshot + a mirror ---
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\SoA\_sandbox\backup-saves.ps1"

echo.
rem --- the graphics settings ---
rem The game writes the settings from the -o dialog into the registry. The
rem export carries it to the host and prepare.cmd puts it back on the next start
rem of the sandbox.
if not exist "%CFG%" mkdir "%CFG%"
reg query "%REGKEY%" >nul 2>&1
if errorlevel 1 (
    echo [settings] the game has not written anything into the registry yet
) else (
    reg export "%REGKEY%" "%CFG%\soa-settings.reg" /y >nul
    if errorlevel 1 (echo [settings] the export failed) else (echo [settings] saved into %CFG%\soa-settings.reg)
)

echo.
rem --- anything the game created (missions from the editor and so on) ---
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\SoA\_sandbox\export-changes.ps1"

echo.
echo Done. Everything survives the sandbox being closed.
timeout /t 5 >nul
endlocal
