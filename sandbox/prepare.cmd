@echo off
setlocal
set SRC=C:\SoA\_patched
set GAME=C:\Game
set TOOLS=C:\SoA\_sandbox\tools
set SAVES=C:\SoA\_saves
set GAMEOUT=C:\SoA\_gameout
set CFG=C:\SoA\_sandbox\config
set REGKEY=HKCU\Software\Silver Style Entertainment

echo ============================================================
echo  Soldiers of Anarchy - preparing the sandbox
echo ============================================================
echo.

if not exist "%SRC%\soa.exe" (
    echo [ERROR] %SRC%\soa.exe does not exist.
    pause
    exit /b 1
)

rem --- 1) the game onto the local disk --------------------------------------
rem The game writes the saved games and replay.log next to the exe. When it
rem runs straight from a folder mapped from the host, every write goes through
rem the redirected filesystem of the sandbox and the game freezes while saving.
rem A local copy goes around that.
echo [1/7] Copying the game onto the local disk: %SRC% -^> %GAME%
robocopy "%SRC%" "%GAME%" /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (echo     ERROR while copying & pause & exit /b 1)
copy /Y "C:\SoA\_sandbox\play.cmd" "%GAME%\" >nul
if exist "%GAMEOUT%" (
    robocopy "%GAMEOUT%" "%GAME%" /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP >nul
    echo     done ^(including play.cmd and the content created earlier - missions from the editor and so on^).
) else (
    echo     done ^(including play.cmd^).
)
echo.

rem --- 2) dgVoodoo2 ---------------------------------------------------------
echo [2/7] The dgVoodoo2 wrapper
if exist "%TOOLS%\dgVoodoo\MS\x86\DDraw.dll" (
    copy /Y "%TOOLS%\dgVoodoo\MS\x86\DDraw.dll"  "%GAME%\ddraw.dll"  >nul
    copy /Y "%TOOLS%\dgVoodoo\MS\x86\D3DImm.dll" "%GAME%\D3DImm.dll" >nul
    copy /Y "%TOOLS%\dgVoodoo\dgVoodooCpl.exe"   "%GAME%\" >nul
    copy /Y "%TOOLS%\dgVoodoo\dgVoodoo.conf"     "%GAME%\" >nul
    echo     copied ^(mode: windowed + mouse capture^).
) else (
    echo     MISSING in %TOOLS%\dgVoodoo\
)
echo.

rem --- 3) the graphics settings of the game ---------------------------------
rem The game keeps the settings from the -o dialog in the registry, which is
rem ephemeral in the sandbox. play.cmd exports it after every session, here it
rem goes back in.
echo [3/7] Graphics settings
if exist "%CFG%\soa-settings.reg" (
    reg import "%CFG%\soa-settings.reg" >nul 2>&1
    if errorlevel 1 (echo     the import failed) else (echo     restored from %CFG%\soa-settings.reg)
) else (
    echo     no saved settings.
    echo     Run "play.cmd -o" once, set the graphics to the maximum and close
    echo     the dialog - from then on it is restored automatically.
)
echo.

rem --- 4) restoring the saved games -----------------------------------------
echo [4/7] Saved games
if exist "%SAVES%" (
    robocopy "%SAVES%" "%GAME%\SaveGames" /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP >nul
    echo     restored from %SAVES%
) else (
    echo     none ^(first start^).
)
echo.

rem --- 5) the save watcher in the background --------------------------------
rem A safety net in case the game crashes or the sandbox is closed while it runs.
echo [5/7] The save watcher
start "" /min powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "C:\SoA\_sandbox\watch-saves.ps1"
echo     running in the background ^(log: _sandbox\logs\watch-saves.log^).
echo.

rem --- 6) the dead GameSpy servers ------------------------------------------
echo [6/7] Blocking GameSpy ^(otherwise the version check at startup waits for a timeout^)
>>"%SystemRoot%\System32\drivers\etc\hosts" echo.
>>"%SystemRoot%\System32\drivers\etc\hosts" echo 127.0.0.1 motd.gamespy.com
>>"%SystemRoot%\System32\drivers\etc\hosts" echo 127.0.0.1 master.gamespy.com
echo     done.
echo.

rem --- 7) the compatibility flag --------------------------------------------
echo [7/7] The compatibility flag
reg add "HKCU\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers" /v "%GAME%\soa.exe" /t REG_SZ /d "~ DISABLEDXMAXIMIZEDWINDOWEDMODE" /f >nul
echo     done.
echo.

echo ============================================================
echo  The game is on the local disk: %GAME%
echo.
echo  START IT THROUGH:  %GAME%\play.cmd
echo     play.cmd       = the game
echo     play.cmd -o    = the graphics configuration
echo.
echo  When the game ends, play.cmd backs up the saves and the
echo  settings to the host itself, so they survive the sandbox
echo  being closed.
echo ============================================================
explorer.exe "%GAME%"
endlocal
