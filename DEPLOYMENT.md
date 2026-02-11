# 🐳 Docker Deployment Guide

## Quick Start

### 1. Deploy the Hub

```bash
cd C:\Users\eqhsp\.gemini\antigravity\scratch\enterprise_business_game

# Copy environment template
cp .env.example .env

# Deploy
chmod +x deploy.sh
./deploy.sh
```

### 2. Verify Services

```bash
# Check health
curl http://localhost:8001/health  # Game API
curl http://localhost:8000/health  # SSOT API

# View logs
docker-compose logs -f master-agent
```

---

## Architecture

```text
┌─────────────────────────────────────────────────┐
│              Nginx Reverse Proxy                │
│         (port 80, rate limiting)                │
└──────────┬──────────────────────┬────────────────┘
           │                      │
     ┌─────▼──────┐        ┌─────▼──────┐
     │  Game API  │        │  SSOT API  │
     │ (port 8001)│        │ (port 8000)│
     └─────▲──────┘        └─────▲──────┘
           │                      │
           │    ┌─────────────────┘
           │    │
     ┌─────▼────▼──────┐
     │  Master Agent   │
     │ (orchestrator)  │
     │  - Auto-spawn   │
     │  - Health check │
     │  - Market tuning│
     └─────────────────┘
```

---

## Services

### 1. **ssot-api** (Port 8000)

- Sovereign State of Truth audit backend
- Merkle-chained capsule storage
- Lineage verification

### 2. **game-api** (Port 8001)

- FastAPI business game engine
- Company registration & operations
- Ledger management

### 3. **master-agent**

- Autonomous orchestrator
- Spawns AI competitors
- Ticks every 5 seconds
- Emits to SSOT every 3 ticks
- Self-tuning market conditions

### 4. **nginx** (Port 80)

- Reverse proxy
- Rate limiting (10 req/s)
- Path routing:
  - `/api/game/` → game-api
  - `/api/ssot/` → ssot-api

---

## Configuration

Edit `.env` to customize:

```bash
# Tick speed (seconds between game ticks)
TICK_INTERVAL_SECONDS=5

# AI opponents
NUM_AI_COMPANIES=3

# Market health thresholds
MIN_CASH_THRESHOLD=10000
```

---

## Management Commands

```bash
# Start
docker-compose up -d

# Stop
docker-compose stop

# Restart single service
docker-compose restart master-agent

# View logs
docker-compose logs -f

# Shutdown + cleanup volumes
docker-compose down -v

# Rebuild after code changes
docker-compose build
docker-compose up -d
```

---

## Monitoring

### Health Endpoints

```bash
# Direct service checks
curl http://localhost:8001/health
curl http://localhost:8000/health

# Via Nginx
curl http://localhost/health/game
curl http://localhost/health/ssot
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f master-agent

# Last 100 lines
docker-compose logs --tail=100
```

### Metrics

```bash
# Game state
curl http://localhost:8001/game/state

# Verify chains
curl http://localhost:8001/game/verify

# Company list
curl http://localhost:8001/game/companies

# SSOT lineage
curl http://localhost:8000/lineage/latest
```

---

## Production Deployment

### 1. Enable SSL

```nginx
# nginx.conf (uncomment HTTPS section)
server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
}
```

Add certificates to `./ssl/` directory.

### 2. Set API Keys

```bash
# .env
API_KEY=your-secret-key-here
```

### 3. Persistent Storage

Volumes are automatically created:

- `game-data`: Game state and ledgers
- `ssot-data`: SSOT capsule storage

Backup:

```bash
docker run --rm -v game-data:/data -v $(pwd):/backup \
    alpine tar czf /backup/game-data-backup.tar.gz /data
```

### 4. Resource Limits

```yaml
# docker-compose.yml
services:
  game-api:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
```

---

## Troubleshooting

### Services won't start

```bash
# Check Docker daemon
docker info

# View startup errors
docker-compose logs

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Master Agent not spawning AI

```bash
# Check environment
docker-compose exec master-agent env | grep AUTO_SPAWN_AI

# View agent logs
docker-compose logs master-agent | grep "Spawned"
```

### SSOT connection failed

```bash
# Verify SSOT is healthy
curl http://localhost:8000/health

# Check master-agent environment
docker-compose exec master-agent env | grep SSOT_API_URL
```

---

## Field Deployment (Remote Server)

```bash
# 1. Copy project to server
scp -r enterprise_business_game user@server:/opt/

# 2. SSH to server
ssh user@server

# 3. Deploy
cd /opt/enterprise_business_game
./deploy.sh

# 4. Verify
curl localhost:8001/health
```

---

## Next Steps

1. **Add Authentication** — Implement API key middleware
2. **Metrics Dashboard** — Prometheus + Grafana
3. **Multi-Region** — Deploy to multiple data centers
4. **React Frontend** — Add web UI container

---

🏁 **Your game hub is now self-running in the field!**
