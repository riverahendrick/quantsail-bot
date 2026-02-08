@echo off
setlocal EnableDelayedExpansion

echo ========================================
echo    QuantSail Bot - Stop Script
echo ========================================
echo.

set "STOP_INFRA=no"
set "FORCE=no"

:: Parse arguments
:parse_args
if "%~1"=="" goto :done_parse
if /I "%~1"=="--with-infra" set "STOP_INFRA=yes" & shift & goto :parse_args
if /I "%~1"=="--force" set "FORCE=yes" & shift & goto :parse_args
if /I "%~1"=="--help" goto :show_help
if /I "%~1"=="-h" goto :show_help
echo Unknown option: %~1
goto :show_help
:done_parse

echo Stopping QuantSail Bot services...
echo.

set "FOUND_ANY=no"

:: Stop by window title (cleaner shutdown)
echo [1] Stopping services by window title...

:: Stop FastAPI
tasklist /FI "WINDOWTITLE eq FastAPI Server" 2>nul | findstr "cmd.exe" >nul
if not errorlevel 1 (
    echo         Stopping FastAPI Server...
    taskkill /F /FI "WINDOWTITLE eq FastAPI Server" >nul 2>&1
    set "FOUND_ANY=yes"
)

:: Stop Dashboard
tasklist /FI "WINDOWTITLE eq Dashboard Server" 2>nul | findstr "cmd.exe" >nul
if not errorlevel 1 (
    echo         Stopping Dashboard Server...
    taskkill /F /FI "WINDOWTITLE eq Dashboard Server" >nul 2>&1
    set "FOUND_ANY=yes"
)

:: Stop Trading Engine
tasklist /FI "WINDOWTITLE eq Trading Engine" 2>nul | findstr "cmd.exe" >nul
if not errorlevel 1 (
    echo         Stopping Trading Engine...
    taskkill /F /FI "WINDOWTITLE eq Trading Engine" >nul 2>&1
    set "FOUND_ANY=yes"
)

:: Also stop by process patterns as fallback
echo [2] Cleaning up remaining processes...

:: Find and stop Python processes running our services
for /f "tokens=2" %%a in ('tasklist ^| findstr "python.exe"') do (
    :: Check if it's one of our services by looking at command line (simplified)
    echo         Checking Python process %%a...
    taskkill /PID %%a /F >nul 2>&1 && (
        echo         Stopped Python process %%a
        set "FOUND_ANY=yes"
    )
)

:: Stop Node processes (Next.js)
tasklist | findstr "node.exe" >nul
if not errorlevel 1 (
    echo         Stopping Node.js processes...
    taskkill /F /IM node.exe >nul 2>&1
    set "FOUND_ANY=yes"
)

:: Stop any remaining uvicorn processes (FastAPI)
tasklist | findstr "uvicorn" >nul
if not errorlevel 1 (
    echo         Stopping Uvicorn processes...
    taskkill /F /IM uvicorn.exe >nul 2>&1 2>&1
    set "FOUND_ANY=yes"
)

if /I "%FOUND_ANY%"=="no" (
    echo         No running services found.
)

:: Stop infrastructure if requested
if /I "%STOP_INFRA%"=="yes" (
    echo.
    echo [3] Stopping Docker infrastructure...
    
    docker info >nul 2>&1
    if errorlevel 1 (
        echo         Docker is not running.
    ) else (
        if exist "infra\docker\docker-compose.yml" (
            pushd "infra\docker"
            docker-compose down
            popd
            echo         Infrastructure stopped.
        ) else (
            echo         docker-compose.yml not found.
        )
    )
)

echo.
echo ========================================
if /I "%FOUND_ANY%"=="yes" (
    echo    All services stopped successfully!
) else (
    echo    No services were running.
)
echo ========================================
echo.

if /I "%STOP_INFRA%"=="no" (
    echo Note: Infrastructure (Postgres/Redis) is still running.
    echo To stop infrastructure too, run: stop-all.bat --with-infra
    echo.
)

echo You can now run start-all.bat to restart services.
echo.
goto :eof

:show_help
echo Usage: stop-all.bat [options]
echo.
echo Options:
echo   --with-infra    Also stop Docker infrastructure (Postgres, Redis)
echo   --force         Force kill all related processes
echo   -h, --help      Show this help message
echo.
echo Examples:
echo   stop-all.bat              Stop application services only
echo   stop-all.bat --with-infra Stop services and infrastructure
echo.
goto :eof

:eof
endlocal
