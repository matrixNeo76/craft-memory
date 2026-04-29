@echo off
REM Craft Memory HTTP Server - Start as background service
REM Usage: start-http.bat (or double-click)
REM Stops with: Ctrl+C or close the window

set CRAFT_WORKSPACE_ID=ws_ecad0f3d
set CRAFT_MEMORY_TRANSPORT=http
set CRAFT_MEMORY_HOST=127.0.0.1
set CRAFT_MEMORY_PORT=8392
set PYTHONPATH=C:\Users\auresystem\craft-memory\src

echo ============================================
echo   Craft Memory HTTP Server
echo   Endpoint: http://127.0.0.1:8392/mcp
echo   Health:   http://127.0.0.1:8392/health
echo ============================================
echo.

REM Kill any previous instance on the same port
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8392 ^| findstr LISTENING') do (
    echo Killing previous instance PID %%a...
    taskkill /F /PID %%a >nul 2>&1
    timeout /t 1 /nobreak >nul
)

echo Starting server...
"C:\Users\auresystem\AppData\Local\Programs\Python\Python312\python.exe" -u "C:\Users\auresystem\craft-memory\src\server.py"
