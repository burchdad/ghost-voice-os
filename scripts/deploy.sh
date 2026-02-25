#!/bin/bash
# Ghost Voice OS - Automated Deployment Script
# Run on a fresh Ubuntu 24.04 server as root

set -e

echo "🚀 Ghost Voice OS - Server Setup"
echo "================================"

# Step 1: Update system
echo "📦 Step 1: Updating system..."
apt update && apt upgrade -y

# Step 2: Install Docker
echo "🐳 Step 2: Installing Docker..."
apt install -y docker.io docker-compose-v2 git curl

# Step 3: Start Docker
echo "🔧 Step 3: Configuring Docker..."
systemctl start docker
systemctl enable docker
usermod -aG docker root

# Step 4: Clone repository
echo "📥 Step 4: Cloning repository..."
if [ ! -d "/root/ghost-voice-os" ]; then
    cd /root
    git clone https://github.com/burchdad/ghost-voice-os.git
fi
cd /root/ghost-voice-os

# Step 5: Create .env file if not exists
echo "⚙️  Step 5: Setting up environment..."
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# Telephony Providers
TELNYX_API_KEY=your_telnyx_api_key
TELNYX_CONNECTION_ID=your_connection_id
TELNYX_PHONE_NUMBER=+1234567890

TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# LLM
OPENAI_API_KEY=your_openai_key

# Voice OS
VOICE_OS_BASE_URL=https://voice.yourdomain.com
STT_SERVICE_URL=http://localhost:8001

# Other
REDIS_URL=redis://localhost:6379
OPENSEARCH_URL=http://localhost:9200
EOF
    echo "⚠️  Created .env file - EDIT IT WITH YOUR CREDENTIALS"
    echo "   nano /root/ghost-voice-os/.env"
else
    echo "✅ .env already exists"
fi

# Step 6: Install Nginx
echo "🌐 Step 6: Installing Nginx..."
apt install -y nginx

# Step 7: Install Certbot for SSL
echo "🔐 Step 7: Installing Let's Encrypt..."
apt install -y certbot python3-certbot-nginx

# Step 8: Get server IP
SERVER_IP=$(curl -s https://api.ipify.org)
echo ""
echo "================================"
echo "✅ Server Setup Complete!"
echo "================================"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Edit your configuration:"
echo "   nano /root/ghost-voice-os/.env"
echo ""
echo "2. Add your credentials:"
echo "   - TELNYX_API_KEY"
echo "   - TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN"
echo "   - OPENAI_API_KEY"
echo ""
echo "3. Point your domain to this server:"
echo "   A Record: voice.yourdomain.com → $SERVER_IP"
echo ""
echo "4. Once domain is ready, run:"
echo "   /root/ghost-voice-os/scripts/setup-ssl.sh"
echo ""
echo "5. Then start services:"
echo "   cd /root/ghost-voice-os"
echo "   docker compose up -d"
echo ""
