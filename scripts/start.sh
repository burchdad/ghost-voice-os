#!/bin/bash
# Production startup script
# Deploys Ghost Voice OS to Docker Swarm

set -e

echo "🚀 Deploying Ghost Voice OS (Production)"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi

# Check Swarm mode
if ! docker info | grep -q "Swarm: active"; then
    echo "❌ Docker Swarm is not initialized"
    echo "Initialize with: docker swarm init"
    exit 1
fi

# Build image
echo "🔨 Building Docker image..."
docker build -t ghost-voice-os:latest ./services/voice-api

# Tag for registry (optional)
if [ ! -z "$DOCKER_REGISTRY" ]; then
    docker tag ghost-voice-os:latest $DOCKER_REGISTRY/ghost-voice-os:latest
    docker push $DOCKER_REGISTRY/ghost-voice-os:latest
    echo "✅ Image pushed to registry"
fi

# Create namespace
docker exec any_swarm_manager kubectl create namespace ghost-voice-os 2>/dev/null || true

# Deploy stack
echo ""
echo "🐳 Deploying stack to Swarm..."
docker stack deploy -c deployment/swarm/stack.yml ghost-voice-os

echo ""
echo "⏳ Waiting for services to stabilize..."
sleep 10

# Check status
echo ""
echo "📊 Deployment status:"
docker stack services ghost-voice-os

echo ""
echo "✅ Ghost Voice OS deployed to production!"
echo ""
echo "Next steps:"
echo "  1. Configure load balancer to point to voice-api service"
echo "  2. Set up monitoring (Datadog, Prometheus, etc.)"
echo "  3. View logs: docker service logs ghost-voice-os_voice-api"
echo ""
