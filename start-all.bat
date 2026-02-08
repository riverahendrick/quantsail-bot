@echo off
setlocal EnableDelayedExpansion

echo ========================================
echo    QuantSail Bot - Startup Script
echo ========================================
echo.

:: Configuration
set "FASTAPI_PORT=8000"
set "DASHBOARD_PORT=3000"
set "POSTGRES_PORT=5433"
set "REDIS_PORT=6380"
set "HEALTH_RETRIES=30"
set "HEALTH_DELAY=2"

:: Parse arguments
set "START_INFRA=no"
set "SKIP_INFRA_CHECK=no"
set "VERBOSE=no"

:parse_args
if "%~1"=="" goto :done_parse
if /I "%~1"=="--with-infra" set "START_INFRA=yes" & shift & goto :parse_args
if /I "%~1"=="--skip-infra-check" set "SKIP_INFRA_CHECK=yes" & shift & goto :parse_args
if /I "%~1"=="--verbose" set "VERBOSE=yes" & shift & goto :parse_args
if /I "%~1"=="--help" goto :show_help
if /I "%~1"=="-h" goto :show_help
echo Unknown option: %~1
goto :show_help
:done_parse

:: Change to script directory
cd /d "%~dp0"

:: Show configuration
echo Configuration:
echo   FastAPI Port:    %FASTAPI_PORT%
echo   Dashboard Port:  %DASHBOARD_PORT%
echo   Postgres Port:   %POSTGRES_PORT%
echo   Redis Port:      %REDIS_PORT%
echo   Start Infra:     %START_INFRA%
echo.

:: Check if Docker is available and start infrastructure if requested
if /I "%START_INFRA%"=="yes" (
    echo [INFRA] Starting Docker infrastructure...
    call :start_infrastructure
    if errorlevel 1 goto :error
    echo.
)

:: Check infrastructure health (unless skipped)
if /I "%SKIP_INFRA_CHECK%"=="no" (
    echo [CHECK] Verifying infrastructure...
    call :check_infrastructure
    if errorlevel 1 (
        echo.
        echo WARNING: Infrastructure not fully available.
        echo You can start it with: start-all.bat --with-infra
        echo Or skip this check with: start-all.bat --skip-infra-check
        echo.
        choice /C YN /M "Continue anyway"
        if errorlevel 2 goto :error
    )
    echo.
)

:: Check for existing processes
echo [CHECK] Checking for existing server processes...
call :check_existing_processes
if errorlevel 1 goto :error
echo.

:: Start FastAPI Backend
echo [1/3] Starting FastAPI Backend Server...
echo         URL: http://localhost:%FASTAPI_PORT%
echo         Docs: http://localhost:%FASTAPI_PORT%/docs
call :start_service "FastAPI" "services\api" "uv run python main.py" %FASTAPI_PORT% "fastapi"
if errorlevel 1 goto :error
echo.

:: Start Trading Engine
echo [2/3] Starting Trading Engine...
echo         Running in background window
call :start_service "TradingEngine" "services\engine" "uv run python main.py" 0 "engine"
if errorlevel 1 goto :error
echo.

:: Start Dashboard (last because it depends on API)
echo [3/3] Starting Next.js Dashboard...
echo         URL: http://localhost:%DASHBOARD_PORT%
call :start_service "Dashboard" "apps\dashboard" "pnpm dev" %DASHBOARD_PORT% "next"
if errorlevel 1 goto :error
echo.

:: Final health check
echo [CHECK] Performing final health checks...
call :health_check "http://localhost:%FASTAPI_PORT%/health" "FastAPI" 10
if errorlevel 1 (
    echo WARNING: FastAPI health check failed. Service may still be starting.
)
call :health_check "http://localhost:%DASHBOARD_PORT%" "Dashboard" 10
if errorlevel 1 (
    echo WARNING: Dashboard health check failed. Service may still be starting.
)
echo.

echo ========================================
echo    All servers started successfully!
echo ========================================
echo.
echo Service URLs:
echo   FastAPI Backend:  http://localhost:%FASTAPI_PORT%
echo   API Documentation: http://localhost:%FASTAPI_PORT%/docs
echo   Dashboard:        http://localhost:%DASHBOARD_PORT%
echo.
echo Press any key to open dashboard in browser...
pause > nul
start http://localhost:%DASHBOARD_PORT%/app/overview
goto :eof

:: ========================================================================
:: Functions
:: ========================================================================

:show_help
echo Usage: start-all.bat [options]
echo.
echo Options:
echo   --with-infra        Start Docker infrastructure (Postgres, Redis)
echo   --skip-infra-check  Skip infrastructure health checks
echo   --verbose           Show detailed output
echo   -h, --help          Show this help message
echo.
echo Examples:
echo   start-all.bat                    Start services only
echo   start-all.bat --with-infra       Start infrastructure + services
echo   start-all.bat --skip-infra-check Skip infrastructure validation
echo.
goto :eof

:start_infrastructure
:: Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running. Please start Docker Desktop first.
    exit /b 1
)

:: Check if docker-compose.yml exists
if not exist "infra\docker\docker-compose.yml" (
    echo ERROR: docker-compose.yml not found at infra\docker\docker-compose.yml
    exit /b 1
)

:: Start infrastructure
echo         Starting Postgres and Redis...
cd "infra\docker"
docker-compose up -d
if errorlevel 1 (
    echo ERROR: Failed to start Docker infrastructure
    cd "%~dp0"
    exit /b 1
)
cd "%~dp0"

:: Wait for services to be ready
echo         Waiting for Postgres on port %POSTGRES_PORT%...
timeout /t 3 /nobreak >nul

:: Check Postgres
call :wait_for_port %POSTGRES_PORT% "Postgres" 15
if errorlevel 1 (
    echo ERROR: Postgres failed to start
    exit /b 1
)

:: Check Redis
call :wait_for_port %REDIS_PORT% "Redis" 15
if errorlevel 1 (
    echo ERROR: Redis failed to start
    exit /b 1
)

echo         Infrastructure is ready!
exit /b 0

:check_infrastructure
set "INFRA_OK=yes"

:: Check Postgres
netstat -an | findstr ":%POSTGRES_PORT% " | findstr "LISTENING" >nul
if errorlevel 1 (
    echo         [X] Postgres not found on port %POSTGRES_PORT%
    set "INFRA_OK=no"
) else (
    echo         [OK] Postgres is running on port %POSTGRES_PORT%
)

:: Check Redis
netstat -an | findstr ":%REDIS_PORT% " | findstr "LISTENING" >nul
if errorlevel 1 (
    echo         [X] Redis not found on port %REDIS_PORT%
    set "INFRA_OK=no"
) else (
    echo         [OK] Redis is running on port %REDIS_PORT%
)

if /I "%INFRA_OK%"=="no" exit /b 1
exit /b 0

:check_existing_processes
set "FOUND=no"

:: Check for existing FastAPI
tasklist /FI "WINDOWTITLE eq FastAPI Server" 2>nul | findstr "cmd.exe" >nul
if not errorlevel 1 (
    echo         [!] FastAPI Server is already running
    set "FOUND=yes"
)

:: Check for existing Dashboard
tasklist /FI "WINDOWTITLE eq Dashboard Server" 2>nul | findstr "cmd.exe" >nul
if not errorlevel 1 (
    echo         [!] Dashboard Server is already running
    set "FOUND=yes"
)

:: Check for existing Trading Engine
tasklist /FI "WINDOWTITLE eq Trading Engine" 2>nul | findstr "cmd.exe" >nul
if not errorlevel 1 (
    echo         [!] Trading Engine is already running
    set "FOUND=yes"
)

:: Check ports
netstat -an | findstr ":%FASTAPI_PORT% " | findstr "LISTENING" >nul
if not errorlevel 1 (
    echo         [!] Port %FASTAPI_PORT% is already in use
    set "FOUND=yes"
)

netstat -an | findstr ":%DASHBOARD_PORT% " | findstr "LISTENING" >nul
if not errorlevel 1 (
    echo         [!] Port %DASHBOARD_PORT% is already in use
    set "FOUND=yes"
)

if /I "%FOUND%"=="yes" (
    echo.
    echo Some services appear to already be running.
    choice /C YN /M "Stop existing services and continue"
    if errorlevel 2 exit /b 1
    call stop-all.bat
    timeout /t 2 /nobreak >nul
)

exit /b 0

:start_service
set "SERVICE_NAME=%~1"
set "SERVICE_DIR=%~2"
set "SERVICE_CMD=%~3"
set "SERVICE_PORT=%~4"
set "SERVICE_TYPE=%~5"

:: Verify directory exists
if not exist "%SERVICE_DIR%" (
    echo ERROR: Directory not found: %SERVICE_DIR%
    exit /b 1
)

:: Start the service in a new window
start "%SERVICE_NAME% Server" cmd /k "cd /d "%~dp0%SERVICE_DIR%" && echo Starting %SERVICE_NAME%... && %SERVICE_CMD%"

:: Wait a moment for initialization
timeout /t 2 /nobreak >nul

:: Check if port-based health check is needed
if %SERVICE_PORT% GTR 0 (
    call :wait_for_port %SERVICE_PORT% %SERVICE_NAME% %HEALTH_RETRIES%
    if errorlevel 1 (
        echo WARNING: %SERVICE_NAME% may not have started properly
        :: Don't fail immediately, give it more time
    )
)

exit /b 0

:wait_for_port
set "PORT=%~1"
set "NAME=%~2"
set "RETRIES=%~3"
set "COUNT=0"

:wait_port_loop
if %COUNT% GEQ %RETRIES% (
    echo         [X] %NAME% did not respond on port %PORT%
    exit /b 1
)

netstat -an | findstr ":%PORT% " | findstr "LISTENING" >nul
if not errorlevel 1 (
    echo         [OK] %NAME% is listening on port %PORT%
    exit /b 0
)

set /a COUNT+=1
if /I "%VERBOSE%"=="yes" echo         ... waiting for %NAME% on port %PORT% (attempt %COUNT%/%RETRIES%)
timeout /t %HEALTH_DELAY% /nobreak >nul
goto :wait_port_loop

:health_check
set "URL=%~1"
set "NAME=%~2"
set "RETRIES=%~3"
set "COUNT=0"

:health_loop
if %COUNT% GEQ %RETRIES% (
    exit /b 1
)

:: Try to fetch health endpoint
powershell -Command "try { $r = Invoke-WebRequest -Uri '%URL%' -TimeoutSec 2 -UseBasicParsing; exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 (
    echo         [OK] %NAME% health check passed
    exit /b 0
)

set /a COUNT+=1
timeout /t 1 /nobreak >nul
goto :health_loop

:error
echo.
echo ========================================
echo    ERROR: Startup failed!
echo ========================================
echo.
echo Check the error messages above.
echo You may need to run stop-all.bat first.
echo.
pause
exit /b 1

:eof
endlocal
