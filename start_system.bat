@echo off
setlocal
cd /d "%~dp0"

if not exist ".runtime" (
  mkdir ".runtime"
)

if exist ".runtime\uvicorn.pid" (
  echo [WARN] Existing PID file found: .runtime\uvicorn.pid
  echo [WARN] If service is not running, run stop_system.bat first.
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$p = Start-Process -FilePath 'python' -ArgumentList '-m','uvicorn','src.app.main:app','--host','0.0.0.0','--port','8000' -WorkingDirectory '%~dp0' -PassThru; Set-Content -Path '.runtime\uvicorn.pid' -Value $p.Id; Write-Host ('[OK] Service started. PID=' + $p.Id + ', URL=http://127.0.0.1:8000')"

echo.
echo Press any key to exit...
pause >nul
endlocal
