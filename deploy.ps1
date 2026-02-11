# Enterprise Business Game - Deployment Script (PowerShell)
# Deploys the game hub as a Docker service cluster

Write-Host "🏙️  Enterprise Business Game - Deployment Script" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker is installed
try {
    $null = docker --version
    Write-Host "✓ Docker found" -ForegroundColor Green
}
catch {
    Write-Host "❌ Docker not found. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}

try {
    $null = docker-compose --version
    Write-Host "✓ docker-compose found" -ForegroundColor Green
}
catch {
    Write-Host "❌ docker-compose not found. Please install docker-compose first." -ForegroundColor Red
    exit 1
}

# Copy environment file if it doesn't exist
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "✓ Created .env from template" -ForegroundColor Green
    }
    else {
        Write-Host "⚠️  No .env.example found" -ForegroundColor Yellow
    }
}
else {
    Write-Host "✓ Using existing .env file" -ForegroundColor Green
}

# Build images
Write-Host ""
Write-Host "🔨 Building Docker images..." -ForegroundColor Cyan
docker-compose build

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}

# Start services
Write-Host ""
Write-Host "🚀 Starting services..." -ForegroundColor Cyan
docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Startup failed!" -ForegroundColor Red
    exit 1
}

# Wait for services
Write-Host ""
Write-Host "⏳ Waiting for services to be healthy..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

# Check service health
Write-Host ""
Write-Host "🏥 Health Check Status:" -ForegroundColor Cyan
Write-Host "----------------------" -ForegroundColor Cyan

function Test-ServiceHealth {
    param($service, $url)
    try {
        $response = Invoke-WebRequest -Uri $url -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "  ✓ $service`: healthy" -ForegroundColor Green
            return $true
        }
    }
    catch {
        Write-Host "  ✗ $service`: unhealthy" -ForegroundColor Red
        return $false
    }
}

Test-ServiceHealth "SSOT API" "http://localhost:8000/health"
Test-ServiceHealth "Game API" "http://localhost:8001/health"

# Show running containers
Write-Host ""
Write-Host "📦 Running Containers:" -ForegroundColor Cyan
Write-Host "---------------------" -ForegroundColor Cyan
docker-compose ps

# Show logs
Write-Host ""
Write-Host "📋 Recent Logs:" -ForegroundColor Cyan
Write-Host "--------------" -ForegroundColor Cyan
docker-compose logs --tail=20

# Instructions
Write-Host ""
Write-Host "✅ Deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "🔗 Service URLs:" -ForegroundColor Cyan
Write-Host "   Game API:    http://localhost:8001" -ForegroundColor White
Write-Host "   SSOT API:    http://localhost:8000" -ForegroundColor White
Write-Host "   Nginx Proxy: http://localhost:80" -ForegroundColor White
Write-Host ""
Write-Host "📊 Useful commands:" -ForegroundColor Cyan
Write-Host "   View logs:        docker-compose logs -f" -ForegroundColor White
Write-Host "   Stop services:    docker-compose stop" -ForegroundColor White
Write-Host "   Restart:          docker-compose restart" -ForegroundColor White
Write-Host "   Shutdown:         docker-compose down" -ForegroundColor White
Write-Host "   Full cleanup:     docker-compose down -v" -ForegroundColor White
Write-Host ""
Write-Host "🎮 The Master Agent is now running and will:" -ForegroundColor Cyan
Write-Host "   - Spawn 3 AI companies automatically" -ForegroundColor White
Write-Host "   - Advance game ticks every 5 seconds" -ForegroundColor White
Write-Host "   - Emit state capsules to SSOT every 3 ticks" -ForegroundColor White
Write-Host "   - Monitor health and tune market conditions" -ForegroundColor White
Write-Host ""
