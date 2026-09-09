@echo off
setlocal
rem Lays out the sandbox the way a stranger's machine looks and then gets out of
rem the way. It installs nothing and configures nothing: whatever the kit needs,
rem the kit has to do itself, and anything this script did for it would be a
rem thing the test no longer covers.

set GIVEN=C:\Given
set GAME=C:\Game
set KIT=C:\SoAKit

echo ============================================================
echo  The kit, as a stranger meets it
echo ============================================================
echo.

echo [1/2] Putting a plain installation of the game on the local disk
rem Onto the local disk rather than left on the mapped folder, for the same
rem reason the playing sandbox does it: the game writes beside its own exe and
rem every write through the sandbox's redirected filesystem is slow enough to
rem freeze it while saving.
robocopy C:\Retail "%GAME%" /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (echo     ERROR while copying & pause & exit /b 1)
rem The vanilla package carries dgVoodoo inside its Game folder, because
rem without a wrapper there is no game on Windows 11 at all. For this test that
rem would be cheating: deploying the wrapper is one of the things the launcher
rem is supposed to do, and finding it already there would quietly skip it.
for %%F in (ddraw.dll D3DImm.dll dgVoodoo.conf dgVoodooCpl.exe) do (
    if exist "%GAME%\%%F" del /q "%GAME%\%%F"
)
echo     %GAME%  ^(the game as it shipped - no wrapper, no settings, nothing of ours^)
echo.

echo [2/2] Unpacking the kit exactly as it comes off the release page
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Expand-Archive -Path 'C:\Given\SoA-Kit-1.16.3.zip' -DestinationPath '%KIT%' -Force"
echo     %KIT%
echo.

echo ============================================================
echo  What to try, in this order
echo.
echo   1. Start %KIT%\Play.exe
echo      There is no Game folder beside it and nothing in the registry,
echo      so it should say it cannot find the game rather than crash.
echo   2. Use "Find the game..." and point it at %GAME%\soa.exe
echo      It should remember the answer.
echo   3. Look at Catalog, Saves and Models - those work without the
echo      game running. Models is the one to watch: it reads
echo      objects.ubn straight out of the installation.
echo   4. Press Play. The launcher has to deploy the wrapper and the
echo      settings itself; nothing here has done that for it.
echo   5. Console and Map need the game running, so they come last.
echo.
echo  %GAME% is a local copy and C:\Retail is now writable too, so
echo  anything written there lands on the host's clean installation
echo  and the next run will not start from a clean one. Rebuild it
echo  with:  build-package.ps1 -Variant vanilla
echo.
echo  The network is on, and the dead GameSpy servers are NOT blocked
echo  in hosts - a stranger's machine would not have that either - so
echo  the game may sit half a minute on its version check at startup.
echo ============================================================
explorer.exe "%KIT%"
endlocal
