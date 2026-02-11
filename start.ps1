# Enterprise Business Game - Startup Script

Write-Host "🏢 Starting Enterprise Business Game..." -ForegroundColor Green
Write-Host ""

# Check if backend is already running
$backendRunning = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
if ($backendRunning) {
    Write-Host "✓ Backend already running on port 8001" -ForegroundColor Yellow
}
else {
    Write-Host "🚀 Starting backend API server..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; python src/api.py"
    Start-Sleep -Seconds 3
}

# Check if frontend dependencies are installed
if (-not (Test-Path "$PSScriptRoot\frontend\node_modules")) {
    Write-Host "📦 Installing frontend dependencies..." -ForegroundColor Cyan
    Set-Location "$PSScriptRoot\frontend"
    npm install
    Set-Location "$PSScriptRoot"
}

# Start frontend
Write-Host "🎨 Starting frontend dev server..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npm run dev"

Start-Sleep -Seconds 5

# Open browser
Write-Host ""
Write-Host "✅ Enterprise Business Game is running!" -ForegroundColor Green
Write-Host ""
Write-Host "   Backend API: http://localhost:8001" -ForegroundColor White
Write-Host "   Frontend UI: http://localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "Opening browser..." -ForegroundColor Cyan

Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "Press any key to stop all services..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Cleanup
Write-Host "Stopping services..." -ForegroundColor Red
Get-Process | Where-Object { $_.MainWindowTitle -like "*uvicorn*" -or $_.MainWindowTitle -like "*vite*" } | Stop-Process -Force
