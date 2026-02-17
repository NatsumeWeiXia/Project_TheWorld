@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "TS_FORMAT=yyyy-MM-dd HH:mm:ss"

if not exist ".runtime" (
  mkdir ".runtime"
)

if /I "!TW_USE_LOCAL_SQLITE!"=="1" (
  set "TW_DATABASE_URL=sqlite+pysqlite:///./test_m1.db"
  call :log INFO "TW_USE_LOCAL_SQLITE=1, using local sqlite database."
  call :log INFO "TW_DATABASE_URL=!TW_DATABASE_URL!"
)

if exist ".runtime\uvicorn.pid" (
  set /p OLD_PID=<".runtime\uvicorn.pid"
  if not "!OLD_PID!"=="" (
    tasklist /FI "PID eq !OLD_PID!" | findstr /R /C:" !OLD_PID! " >nul
    if not errorlevel 1 (
      call :log WARN "Service already running. PID=!OLD_PID!"
      call :log INFO "URL: http://127.0.0.1:8000"
      endlocal
      exit /b 0
    )
  )
  del /f /q ".runtime\uvicorn.pid" >nul 2>&1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference = 'Stop'; $wd = '%~dp0'; $outLog = Join-Path $wd '.runtime\uvicorn.out.log'; $errLog = Join-Path $wd '.runtime\uvicorn.err.log'; $pidFile = Join-Path $wd '.runtime\uvicorn.pid'; $logConfig = Join-Path $wd 'configs\uvicorn_log.json'; if (Test-Path $outLog) { Remove-Item $outLog -Force -ErrorAction SilentlyContinue }; if (Test-Path $errLog) { Remove-Item $errLog -Force -ErrorAction SilentlyContinue }; $pyw = Join-Path (Split-Path (Get-Command python | Select-Object -ExpandProperty Source) -Parent) 'pythonw.exe'; $exe = if (Test-Path $pyw) { $pyw } else { 'python' }; $p = Start-Process -FilePath $exe -ArgumentList '-m','uvicorn','src.app.main:app','--host','0.0.0.0','--port','8000','--log-config',$logConfig -WorkingDirectory $wd -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru; Set-Content -Path $pidFile -Value $p.Id; Start-Sleep -Seconds 2; if ($p.HasExited) { $ts=(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'); Write-Host ('[' + $ts + '] [ERROR] Service exited during startup.'); if (Test-Path $errLog) { Write-Host ('[' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '] [INFO] ------ .runtime\uvicorn.err.log (tail) ------'); Get-Content -Path $errLog -Tail 80 }; if (Test-Path $outLog) { Write-Host ('[' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '] [INFO] ------ .runtime\uvicorn.out.log (tail) ------'); Get-Content -Path $outLog -Tail 80 }; exit 1 }; $ts=(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'); Write-Host ('[' + $ts + '] [OK] Service started. PID=' + $p.Id + ', URL=http://127.0.0.1:8000'); Write-Host ('[' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '] [INFO] Out log: ' + $outLog); Write-Host ('[' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '] [INFO] Err log: ' + $errLog)"
if errorlevel 1 (
  endlocal
  exit /b 1
)

endlocal
exit /b 0

:log
for /f "delims=" %%I in ('powershell -NoProfile -Command "Get-Date -Format \"%TS_FORMAT%\""') do set "NOW=%%I"
echo [!NOW!] [%~1] %~2
exit /b 0
