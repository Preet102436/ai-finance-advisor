@echo off
REM ==============================================================
REM  Optional: share the running app / open it on a phone.
REM  Start the app with START.bat first. Needs cloudflared:
REM    winget install --id Cloudflare.cloudflared
REM  Copy the https://....trycloudflare.com link this prints.
REM ==============================================================
where cloudflared >nul 2>&1 || (echo cloudflared not installed. Run: winget install --id Cloudflare.cloudflared & pause & exit /b 1)
cloudflared tunnel --url http://localhost:5173
pause
