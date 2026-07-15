@echo off
echo ============================================
echo  CBP Ruling Explorer - Stop All Services
echo ============================================
echo.

echo [*] Stopping backend on port 9000 and frontend on port 5173 ...
for %%P in (9000 5173) do (
    powershell -NoProfile -Command "$port=%%P; $c=Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue; if($c){$c|%%{Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue}; Write-Host ('  killed process on port '+$port)} else {Write-Host ('  nothing listening on port '+$port)}"
)

echo.
echo [*] Fallback: closing launcher windows by title ...
taskkill /FI "WINDOWTITLE eq CBP-Backend" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq CBP-Frontend" /F >nul 2>&1

echo.
echo [done] All CBP services stopped (if any were running).
echo.
pause
