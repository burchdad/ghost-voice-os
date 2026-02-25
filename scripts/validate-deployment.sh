#!/bin/bash
# Ghost Voice OS - Post-Deployment Validation

echo "🔍 Ghost Voice OS - Deployment Check"
echo "===================================="
echo ""

# Check Docker
echo "1️⃣  Docker Status:"
if docker --version > /dev/null 2>&1; then
    echo "   ✅ Docker installed: $(docker --version)"
else
    echo "   ❌ Docker not found"
    exit 1
fi

# Check Docker Compose
echo ""
echo "2️⃣  Docker Compose Status:"
if docker compose --version > /dev/null 2>&1; then
    echo "   ✅ Docker Compose: $(docker compose --version)"
else
    echo "   ❌ Docker Compose not found"
    exit 1
fi

# Check running containers
echo ""
echo "3️⃣  Container Status:"
cd /root/ghost-voice-os
docker compose ps

# Check service health
echo ""
echo "4️⃣  Service Health:"

echo "   Testing voice-api (port 8000)..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    HEALTH=$(curl -s http://localhost:8000/health | jq -r '.status // "unknown"')
    echo "   ✅ voice-api: $HEALTH"
else
    echo "   ⏳ voice-api: not yet responding (may still be starting)"
fi

echo "   Testing voice-stt (port 8001)..."
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    HEALTH=$(curl -s http://localhost:8001/health | jq -r '.status // "unknown"')
    echo "   ✅ voice-stt: $HEALTH"
else
    echo "   ⏳ voice-stt: not yet responding (may still be starting)"
fi

echo "   Testing opensearch (port 9200)..."
if curl -s http://localhost:9200/_cluster/health > /dev/null 2>&1; then
    STATUS=$(curl -s http://localhost:9200/_cluster/health | jq -r '.status // "unknown"')
    echo "   ✅ opensearch: $STATUS"
else
    echo "   ⏳ opensearch: not yet responding"
fi

echo "   Testing redis (port 6379)..."
if docker exec ghost-voice-redis redis-cli ping > /dev/null 2>&1; then
    echo "   ✅ redis: responding"
else
    echo "   ⏳ redis: not yet responding"
fi

# Check Nginx
echo ""
echo "5️⃣  Nginx Status:"
if systemctl is-active --quiet nginx; then
    echo "   ✅ Nginx: running"
else
    echo "   ⏳ Nginx: not running"
fi

# Check SSL certificates
echo ""
echo "6️⃣  SSL Certificates:"
if [ -d "/etc/letsencrypt/live" ]; then
    CERTS=$(ls /etc/letsencrypt/live/ | wc -l)
    if [ $CERTS -gt 0 ]; then
        echo "   ✅ $CERTS certificate(s) found"
        ls -1 /etc/letsencrypt/live/
    else
        echo "   ⏳ No certificates yet (run setup-ssl.sh)"
    fi
else
    echo "   ⏳ Let's Encrypt not configured (run setup-ssl.sh)"
fi

# Check environment
echo ""
echo "7️⃣  Environment File:"
if [ -f "/root/ghost-voice-os/.env" ]; then
    echo "   ✅ .env file exists"
    MISSING=0
    
    for VAR in TELNYX_API_KEY TWILIO_ACCOUNT_SID OPENAI_API_KEY; do
        VALUE=$(grep "^$VAR=" /root/ghost-voice-os/.env 2>/dev/null | cut -d= -f2)
        if [[ "$VALUE" == *"your_"* ]] || [ -z "$VALUE" ]; then
            echo "   ⚠️  $VAR - needs configuration"
            ((MISSING++))
        fi
    done
    
    if [ $MISSING -eq 0 ]; then
        echo "   ✅ All credentials configured"
    fi
else
    echo "   ❌ .env file not found"
fi

echo ""
echo "===================================="
echo "✅ Deployment check complete!"
echo ""
echo "If services are still starting, wait 30-60 seconds and run this script again."
echo ""
