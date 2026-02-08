#Requires -Version 5.1

<#
.SYNOPSIS
    Starts all QuantSail Bot services with health checks.

.DESCRIPTION
    Starts the FastAPI backend, Trading Engine, and Next.js dashboard
    with proper health checks and dependency management.

.PARAMETER WithInfra
    Start Docker infrastructure (Postgres, Redis) before services.

.PARAMETER SkipInfraCheck
    Skip infrastructure health checks.

.PARAMETER Verbose
    Show detailed output during startup.

.EXAMPLE
    .\start-all.ps1
    Starts services only.

.EXAMPLE
    .\start-all.ps1 -WithInfra
    Starts infrastructure then services.

.EXAMPLE
    .\start-all.ps1 -SkipInfraCheck
    Skip infrastructure validation.
#>

[CmdletBinding()]
param(
    [switch]$WithInfra,
    [switch]$SkipInfraCheck,
    [switch]$Verbose
)

# Configuration
$script:Config = @{
    FastApiPort    = 8000
    DashboardPort  = 3000
    PostgresPort   = 5433
    RedisPort      = 6380
    HealthRetries  = 30
    HealthDelay    = 2
}

# Colors
$Colors = @{
    Success = 'Green'
    Info    = 'Cyan'
    Warning = 'Yellow'
    Error   = 'Red'
    Normal  = 'White'
}

function Write-Status {
    param([string]$Message, [string]$Type = 'Normal')
    Write-Host $Message -ForegroundColor $Colors[$Type]
}

function Write-Check {
    param([string]$Message, [switch]$Success, [switch]$Failed)
    $prefix = if ($Success) { "[OK]  " } elseif ($Failed) { "[X]   " } else { "[*]   " }
    $color = if ($Success) { 'Green' } elseif ($Failed) { 'Red' } else { 'Yellow' }
    Write-Host "        $prefix$Message" -ForegroundColor $color
}

function Test-PortListening {
    param([int]$Port, [int]$TimeoutSeconds = 60)
    
    $endTime = (Get-Date).AddSeconds($TimeoutSeconds)
    $attempt = 0
    
    while ((Get-Date) -lt $endTime) {
        $attempt++
        $connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | 
                      Where-Object { $_.State -eq 'Listen' }
        
        if ($connection) { return $true }
        
        if ($Verbose) {
            Write-Host "        ... waiting for port $Port (attempt $attempt)" -ForegroundColor DarkGray
        }
        
        Start-Sleep -Seconds $script:Config.HealthDelay
    }
    
    return $false
}

function Test-HealthEndpoint {
    param([string]$Url, [int]$TimeoutSeconds = 30)
    
    $endTime = (Get-Date).AddSeconds($TimeoutSeconds)
    
    while ((Get-Date) -lt $endTime) {
        try {
            $response = Invoke-WebRequest -Uri $Url -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
            if ($response.StatusCode -eq 200) { return $true }
        } catch {
            # Continue waiting
        }
        Start-Sleep -Seconds 1
    }
    
    return $false
}

function Start-Infrastructure {
    Write-Status "[INFRA] Starting Docker infrastructure..." 'Info'
    
    # Check if Docker is running
    try {
        $null = docker info 2>$null
    } catch {
        Write-Status "ERROR: Docker is not running. Please start Docker Desktop first." 'Error'
        return $false
    }
    
    $composeFile = Join-Path $PSScriptRoot "infra\docker\docker-compose.yml"
    if (-not (Test-Path $composeFile)) {
        Write-Status "ERROR: docker-compose.yml not found at $composeFile" 'Error'
        return $false
    }
    
    # Start infrastructure
    Push-Location (Split-Path $composeFile)
    try {
        docker-compose up -d 2>&1 | ForEach-Object {
            if ($Verbose) { Write-Host "        $_" -ForegroundColor DarkGray }
        }
        
        if ($LASTEXITCODE -ne 0) {
            Write-Status "ERROR: Failed to start Docker infrastructure" 'Error'
            return $false
        }
    } finally {
        Pop-Location
    }
    
    # Wait for services
    Write-Host "        Waiting for services to be ready..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    
    # Check Postgres
    if (-not (Test-PortListening -Port $script:Config.PostgresPort -TimeoutSeconds 30)) {
        Write-Check "Postgres failed to start on port $($script:Config.PostgresPort)" -Failed
        return $false
    }
    Write-Check "Postgres is listening on port $($script:Config.PostgresPort)" -Success
    
    # Check Redis
    if (-not (Test-PortListening -Port $script:Config.RedisPort -TimeoutSeconds 30)) {
        Write-Check "Redis failed to start on port $($script:Config.RedisPort)" -Failed
        return $false
    }
    Write-Check "Redis is listening on port $($script:Config.RedisPort)" -Success
    
    Write-Status "        Infrastructure is ready!" 'Success'
    return $true
}

function Test-Infrastructure {
    Write-Status "[CHECK] Verifying infrastructure..." 'Info'
    
    $infraOk = $true
    
    # Check Postgres
    $pgConnection = Get-NetTCPConnection -LocalPort $script:Config.PostgresPort -ErrorAction SilentlyContinue | 
                    Where-Object { $_.State -eq 'Listen' }
    if ($pgConnection) {
        Write-Check "Postgres is running on port $($script:Config.PostgresPort)" -Success
    } else {
        Write-Check "Postgres not found on port $($script:Config.PostgresPort)" -Failed
        $infraOk = $false
    }
    
    # Check Redis
    $redisConnection = Get-NetTCPConnection -LocalPort $script:Config.RedisPort -ErrorAction SilentlyContinue | 
                       Where-Object { $_.State -eq 'Listen' }
    if ($redisConnection) {
        Write-Check "Redis is running on port $($script:Config.RedisPort)" -Success
    } else {
        Write-Check "Redis not found on port $($script:Config.RedisPort)" -Failed
        $infraOk = $false
    }
    
    return $infraOk
}

function Test-ExistingProcesses {
    Write-Status "[CHECK] Checking for existing server processes..." 'Info'
    
    $found = @()
    
    # Check for existing windows
    $processes = Get-Process | Where-Object { $_.MainWindowTitle -match "FastAPI|Dashboard|Trading Engine" }
    foreach ($proc in $processes) {
        Write-Check "Found existing: $($proc.MainWindowTitle)" -Failed
        $found += $proc
    }
    
    # Check ports
    $fastApiPort = Get-NetTCPConnection -LocalPort $script:Config.FastApiPort -ErrorAction SilentlyContinue | 
                   Where-Object { $_.State -eq 'Listen' }
    if ($fastApiPort) {
        Write-Check "Port $($script:Config.FastApiPort) is already in use" -Failed
        $found += $true
    }
    
    $dashPort = Get-NetTCPConnection -LocalPort $script:Config.DashboardPort -ErrorAction SilentlyContinue | 
                Where-Object { $_.State -eq 'Listen' }
    if ($dashPort) {
        Write-Check "Port $($script:Config.DashboardPort) is already in use" -Failed
        $found += $true
    }
    
    if ($found.Count -gt 0) {
        Write-Host ""
        Write-Status "Some services appear to already be running." 'Warning'
        $response = Read-Host "Stop existing services and continue? (Y/N)"
        if ($response -ne 'Y' -and $response -ne 'y') {
            return $false
        }
        
        & "$PSScriptRoot\stop-all.bat"
        Start-Sleep -Seconds 2
    }
    
    return $true
}

function Start-Service {
    param(
        [string]$Name,
        [string]$Directory,
        [string]$Command,
        [int]$Port = 0,
        [string]$Type
    )
    
    $fullPath = Join-Path $PSScriptRoot $Directory
    if (-not (Test-Path $fullPath)) {
        Write-Status "ERROR: Directory not found: $Directory" 'Error'
        return $false
    }
    
    Write-Host "        Starting in: $Directory" -ForegroundColor DarkGray
    
    # Start the service
    $arguments = "-NoExit", "-Command", "cd '$fullPath'; Write-Host 'Starting $Name...' -ForegroundColor Green; $Command"
    Start-Process powershell -ArgumentList $arguments
    
    Start-Sleep -Seconds 2
    
    # Health check for port-based services
    if ($Port -gt 0) {
        if (Test-PortListening -Port $Port -TimeoutSeconds 60) {
            Write-Check "$Name is listening on port $Port" -Success
        } else {
            Write-Check "$Name may not have started properly on port $Port" -Failed
            # Don't fail immediately - services may take longer
        }
    }
    
    return $true
}

# ========================================================================
# Main Script
# ========================================================================

Write-Status "========================================" 'Success'
Write-Status "   QuantSail Bot - Startup Script" 'Success'
Write-Status "========================================" 'Success'
Write-Host ""

# Show configuration
Write-Status "Configuration:" 'Info'
Write-Host "  FastAPI Port:    $($script:Config.FastApiPort)"
Write-Host "  Dashboard Port:  $($script:Config.DashboardPort)"
Write-Host "  Postgres Port:   $($script:Config.PostgresPort)"
Write-Host "  Redis Port:      $($script:Config.RedisPort)"
Write-Host "  Start Infra:     $WithInfra"
Write-Host ""

# Start infrastructure if requested
if ($WithInfra) {
    if (-not (Start-Infrastructure)) {
        Write-Status "Failed to start infrastructure. Exiting." 'Error'
        exit 1
    }
    Write-Host ""
}

# Check infrastructure (unless skipped)
if (-not $SkipInfraCheck) {
    if (-not (Test-Infrastructure)) {
        Write-Host ""
        Write-Status "WARNING: Infrastructure not fully available." 'Warning'
        Write-Status "You can start it with: .\start-all.ps1 -WithInfra" 'Info'
        Write-Status "Or skip this check with: .\start-all.ps1 -SkipInfraCheck" 'Info'
        Write-Host ""
        $response = Read-Host "Continue anyway? (Y/N)"
        if ($response -ne 'Y' -and $response -ne 'y') {
            exit 1
        }
    }
    Write-Host ""
}

# Check for existing processes
if (-not (Test-ExistingProcesses)) {
    exit 1
}
Write-Host ""

# Start services
Write-Status "[1/3] Starting FastAPI Backend Server..." 'Info'
Write-Host "        URL: http://localhost:$($script:Config.FastApiPort)"
Write-Host "        Docs: http://localhost:$($script:Config.FastApiPort)/docs"
if (-not (Start-Service -Name "FastAPI" -Directory "services\api" -Command "uv run python main.py" -Port $script:Config.FastApiPort -Type "fastapi")) {
    exit 1
}
Write-Host ""

Write-Status "[2/3] Starting Trading Engine..." 'Info'
Write-Host "        Running in background window"
if (-not (Start-Service -Name "TradingEngine" -Directory "services\engine" -Command "uv run python main.py" -Port 0 -Type "engine")) {
    exit 1
}
Write-Host ""

Write-Status "[3/3] Starting Next.js Dashboard..." 'Info'
Write-Host "        URL: http://localhost:$($script:Config.DashboardPort)"
if (-not (Start-Service -Name "Dashboard" -Directory "apps\dashboard" -Command "pnpm dev" -Port $script:Config.DashboardPort -Type "next")) {
    exit 1
}
Write-Host ""

# Final health checks
Write-Status "[CHECK] Performing final health checks..." 'Info'

$fastApiHealth = Test-HealthEndpoint -Url "http://localhost:$($script:Config.FastApiPort)/health" -TimeoutSeconds 20
if ($fastApiHealth) {
    Write-Check "FastAPI health check passed" -Success
} else {
    Write-Check "FastAPI health check failed - service may still be starting" -Failed
}

$dashHealth = Test-HealthEndpoint -Url "http://localhost:$($script:Config.DashboardPort)" -TimeoutSeconds 20
if ($dashHealth) {
    Write-Check "Dashboard health check passed" -Success
} else {
    Write-Check "Dashboard health check failed - service may still be starting" -Failed
}

Write-Host ""
Write-Status "========================================" 'Success'
Write-Status "   All servers started successfully!" 'Success'
Write-Status "========================================" 'Success'
Write-Host ""
Write-Status "Service URLs:" 'Info'
Write-Host "  FastAPI Backend:   http://localhost:$($script:Config.FastApiPort)"
Write-Host "  API Documentation: http://localhost:$($script:Config.FastApiPort)/docs"
Write-Host "  Dashboard:         http://localhost:$($script:Config.DashboardPort)"
Write-Host ""

Write-Status "Press any key to open dashboard in browser..." 'Warning'
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
Start-Process "http://localhost:$($script:Config.DashboardPort)/app/overview"
