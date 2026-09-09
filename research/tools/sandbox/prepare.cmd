@echo off
setlocal
echo ============================================================
echo  Verification of the Soldiers of Anarchy package
echo ============================================================
echo.

if not exist "C:\Package\Play.exe" (
    echo [ERROR] The mapped package was not found: C:\Package\Play.exe
    pause
    exit /b 1
)

rem A copy on the local disk. The mapped folder is read-only so the test cannot
rem change the package, and the game freezes while saving through the redirected
rem sandbox filesystem - the copy avoids both.
echo [1/3] Copying the package to the local disk (about 1 GB, this takes a while)
robocopy "C:\Package" "C:\SoA" /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (echo      ERROR while copying & pause & exit /b 1)
echo      done.
echo.

echo [2/3] Checking the contents
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Test\check.ps1"
echo.

echo [3/3] The package is in C:\SoA
echo.
echo ============================================================
echo  Now just what anybody else would do: run C:\SoA\Play.exe
echo.
echo  What to watch for:
echo    - the launcher window offers the resolutions of this desktop
echo    - PLAY starts the game and it comes up without an error message
echo    - the game can save a position and does not freeze
echo    - the cursor does not escape the sandbox window
echo    - the body hit sounds play (the repaired archive)
echo    - the Game settings button opens the game configuration dialog
echo.
echo  When you are done, run C:\Test\after-run.cmd - it checks what the
echo  launcher really set and leaves a log on the host.
echo ============================================================
explorer.exe "C:\SoA"
endlocal
