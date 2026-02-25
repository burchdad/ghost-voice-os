#!/bin/bash
# Development startup script
# Runs Ghost Voice OS with hot-reload for development

set -e

echo "🚀 Starting Ghost Voice OS (Development Mode)"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env not found, creating from .env.example..."
    cp .env.example .env
    echo "✅ Created .env - please configure it before running"
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi

# Stop existing containers
echo "Stopping existing containers..."
docker-compose down 2>/dev/null || true

echo ""
echo "🐳 Starting Docker services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 5

# Check health
echo ""
echo "🏥 Checking service health..."

for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ voice-api is healthy"
        break
    fi
    echo "   Waiting... ($i/30)"
    sleep 1
done

echo ""
echo "✅ Ghost Voice OS is running!"
echo ""
echo "Services:"
echo "  • voice-api:      http://localhost:8000"
echo "  • Redis:          localhost:6379"
echo "  • Postgres:       localhost:5432"
echo "  • OpenSearch:     http://localhost:9200"
echo "  • Dashboards:     http://localhost:5601"
echo ""
echo "Commands:"
echo "  • View logs:      docker-compose logs -f voice-api"
echo "  • Stop:           docker-compose down"
echo "  • Kill:           docker-compose down -v"
echo ""
