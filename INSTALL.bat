@echo off
REM ==============================================================
REM  AI Finance Advisor - one-time install.
REM  Right-click this file > "Run as administrator".
REM ==============================================================
cd /d "%~dp0"
title AI Finance Advisor - Install

echo.
echo [1/4] Checking prerequisites...
where python >nul 2>&1 || (echo   Python not found. Install Python 3.11+ from python.org ^(tick "Add to PATH"^). & goto :fail)
where npm >nul 2>&1 || (echo   Node.js not found. Install Node.js LTS from nodejs.org. & goto :fail)
if not exist "C:\Program Files\PostgreSQL\" (echo   PostgreSQL not found. Install PostgreSQL from postgresql.org. & goto :fail)
echo   OK

echo.
echo [2/4] Installing backend packages...
python -m pip install -r backend\api\requirements.txt || goto :fail

echo.
echo [3/4] Installing frontend packages...
pushd frontend
call npm install || (popd & goto :fail)
popd

echo.
echo [4/4] Setting up the database...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-db.ps1" || goto :fail

echo.
echo ==============================================================
echo  Install complete. Double-click START.bat to run the app.
echo ==============================================================
pause
exit /b 0

:fail
echo.
echo  Install stopped - fix the problem above, then run INSTALL.bat again.
pause
exit /b 1
