@echo off
REM ==============================================================
REM  AI Finance Advisor - start the app.
REM  Opens two windows (Backend + Frontend), then the browser.
REM  Close those two windows to stop the app.
REM ==============================================================
cd /d "%~dp0"
if not exist "frontend\node_modules\" (echo Run INSTALL.bat first. & pause & exit /b 1)
if not exist "backend\api\.env" (echo Run INSTALL.bat first. & pause & exit /b 1)

start "Backend - AI Finance Advisor" /D "%~dp0backend\api" cmd /k python -m uvicorn main:app --reload
start "Frontend - AI Finance Advisor" /D "%~dp0frontend" cmd /k npm run dev

echo Starting... the app will open in your browser in a few seconds.
timeout /t 8 /nobreak >nul
start "" http://localhost:5173
