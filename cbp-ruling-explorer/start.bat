@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

REM ============================================================
REM  CBP Ruling Explorer - One-Click Startup
REM  1) backend  2) frontend
REM ============================================================

set "ROOT=%~dp0"
set "PYTHON=D:\Develop\miniconda\envs\py312\python.exe"

echo ============================================================
echo   CBP Ruling Explorer - Starting...
echo ============================================================

if not exist "%PYTHON%" (
    echo [WARN] py312 not found at %PYTHON%, falling back to "python".
    set "PYTHON=python"
)

REM ---- 1) Backend (FastAPI) ----
echo [1/2] Launching backend (FastAPI :9000)...
cd /d "%ROOT%backend"
start "CBP-Backend" cmd /k "%PYTHON% -m pip install -q -r requirements.txt && echo. && echo [Backend] deps ready, starting server... && %PYTHON% run.py"

REM ---- 2) Frontend (Vite) ----
echo [2/2] Launching frontend (Vite :5173)...
cd /d "%ROOT%frontend"
start "CBP-Frontend" cmd /k "npm install && echo. && echo [Frontend] deps ready, starting dev server... && npm run dev"

echo.
echo Both services are launching in new windows.
echo   Backend  -^> http://localhost:9000
echo   Frontend -^> http://localhost:5173
echo Close those windows to stop the services.
echo.
pause
endlocal
