@echo off
setlocal
cd /d "%~dp0"

if not exist ".runtime\uvicorn.pid" (
  call :log WARN "PID file not found: .runtime\uvicorn.pid"
  call :log WARN "Service may already be stopped."
  endlocal
  exit /b 0
)

set /p UVICORN_PID=<".runtime\uvicorn.pid"
if "%UVICORN_PID%"=="" (
  call :log WARN "PID file is empty. Cleaning stale pid file."
  del /f /q ".runtime\uvicorn.pid" >nul 2>&1
  endlocal
  exit /b 0
)

taskkill /PID %UVICORN_PID% /T /F >nul 2>&1
if errorlevel 1 (
  call :log WARN "Failed to kill PID %UVICORN_PID%. Process may not exist."
) else (
  call :log OK "Service stopped. PID=%UVICORN_PID%"
)

del /f /q ".runtime\uvicorn.pid" >nul 2>&1

endlocal
exit /b 0

:log
for /f "delims=" %%I in ('powershell -NoProfile -Command "Get-Date -Format \"yyyy-MM-dd HH:mm:ss\""') do set "NOW=%%I"
echo [%NOW%] [%~1] %~2
exit /b 0
