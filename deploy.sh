#!/bin/bash

# Enterprise Business Game - Deployment Script
# Deploys the game hub as a Docker service cluster

set -e

echo "🏙️  Enterprise Business Game - Deployment Script"
echo "=================================================="

# Check Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install docker-compose first."
    exit 1
fi

# Configuration
ENV_FILE="${1:-.env}"

if [ -f "$ENV_FILE" ]; then
    echo "✓ Loading environment from $ENV_FILE"
    source "$ENV_FILE"
else
    echo "⚠️  No environment file found, using defaults"
fi

# Build images
echo ""
echo "🔨 Building Docker images..."
docker-compose build

# Start services
echo ""
echo "🚀 Starting services..."
docker-compose up -d

# Wait for health checks
echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 5

# Check service health
echo ""
echo "🏥 Health Check Status:"
echo "----------------------"

check_health() {
    local service=$1
    local url=$2
    
    if curl -f -s "$url" > /dev/null 2>&1; then
        echo "  ✓ $service: healthy"
        return 0
    else
        echo "  ✗ $service: unhealthy"
        return 1
    fi
}

check_health "SSOT API" "http://localhost:8000/health"
check_health "Game API" "http://localhost:8001/health"

# Show running containers
echo ""
echo "📦 Running Containers:"
echo "---------------------"
docker-compose ps

# Show logs
echo ""
echo "📋 Recent Logs:"
echo "--------------"
docker-compose logs --tail=20

# Instructions
echo ""
echo "✅ Deployment complete!"
echo ""
echo "🔗 Service URLs:"
echo "   Game API:    http://localhost:8001"
echo "   SSOT API:    http://localhost:8000"
echo "   Nginx Proxy: http://localhost:80"
echo ""
echo "📊 Useful commands:"
echo "   View logs:        docker-compose logs -f"
echo "   Stop services:    docker-compose stop"
echo "   Restart:          docker-compose restart"
echo "   Shutdown:         docker-compose down"
echo "   Full cleanup:     docker-compose down -v"
echo ""
echo "🎮 The Master Agent is now running and will:"
echo "   - Spawn 3 AI companies automatically"
echo "   - Advance game ticks every 5 seconds"
echo "   - Emit state capsules to SSOT every 3 ticks"
echo "   - Monitor health and tune market conditions"
echo ""
