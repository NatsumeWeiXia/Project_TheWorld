@echo off
setlocal
cd /d "%~dp0"

if not exist ".runtime\uvicorn.pid" (
  echo [WARN] PID file not found: .runtime\uvicorn.pid
  echo [WARN] Service may already be stopped.
  echo.
  echo Press any key to exit...
  pause >nul
  endlocal
  exit /b 0
)

set /p UVICORN_PID=<".runtime\uvicorn.pid"
if "%UVICORN_PID%"=="" (
  echo [ERROR] PID file is empty.
  echo.
  echo Press any key to exit...
  pause >nul
  endlocal
  exit /b 1
)

taskkill /PID %UVICORN_PID% /T /F >nul 2>&1
if errorlevel 1 (
  echo [WARN] Failed to kill PID %UVICORN_PID%. Process may not exist.
) else (
  echo [OK] Service stopped. PID=%UVICORN_PID%
)

del /f /q ".runtime\uvicorn.pid" >nul 2>&1

echo.
echo Press any key to exit...
pause >nul
endlocal
