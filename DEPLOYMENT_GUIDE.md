# Ghost Voice OS - Deployment Guide

## Overview

This guide walks you through deploying Ghost Voice OS to a cloud server. No prior cloud experience needed.

## Step 1: Choose Your Server

### Recommended: Hetzner (Easiest, Cheapest)

**Why Hetzner?**
- €3.99/month for a basic server (more than enough for Voice OS)
- One-click Ubuntu setup
- Simple SSH access
- Great documentation
- No credit card tricks

**Alternative options:**
- DigitalOcean ($5/month, also beginner-friendly)
- AWS EC2 (more complex, good if you already have AWS account)

### For this guide, we'll use Hetzner:

1. Go to https://www.hetzner.com/cloud
2. Sign up with email
3. Add billing method (they may ask for verification)
4. Create new project named "ghost-voice-os"
5. Click "Create Server"
   - Choose **Ubuntu 24.04** image
   - Choose **CPX11** instance type (€3.99/month)
   - Choose datacenter region closest to you
   - Add your SSH key (see below)
   - Give it a name: `voice-api-1`
   - Click "Create & Buy"

Wait ~30 seconds for server to boot.

---

## Step 2: Set Up SSH Access

SSH is how you remotely access your server.

### If you DON'T have an SSH key yet:

Run this on your local machine:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/hetzner_key -N ""
cat ~/.ssh/hetzner_key.pub
```

Copy the output (starts with `ssh-ed25519`).

In Hetzner Console:
1. Go to Security → SSH keys
2. Click "Add SSH Key"
3. Paste the public key
4. Name it "My Key"
5. Save

### If you ALREADY have an SSH key:

Use it when creating the server.

### Test connection:

```bash
# Replace 1.2.3.4 with your server's IP (from Hetzner console)
ssh root@1.2.3.4
```

You should see a prompt. Type `exit` to disconnect.

---

## Step 3: Prepare Your Server

Once SSH-connected, run:

```bash
# Update system
apt update && apt upgrade -y

# Install Docker
apt install -y docker.io docker-compose-v2

# Start Docker
systemctl start docker
systemctl enable docker

# Add current user to docker group (so you don't need sudo)
usermod -aG docker root

# Verify Docker works
docker --version
```

---

## Step 4: Deploy Ghost Voice OS

### Clone the repository:

```bash
cd /root
git clone https://github.com/burchdad/ghost-voice-os.git
cd ghost-voice-os
```

### Set up environment variables:

```bash
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
```

Replace with YOUR actual credentials from Telnyx, Twilio, OpenAI.

### Start the services:

```bash
docker compose up -d
```

Wait ~30 seconds for all services to start.

Check status:

```bash
docker compose ps
```

You should see all 5 services running:
- voice-api (port 8000)
- voice-stt-whisper (port 8001)
- opensearch (port 9200)
- redis (port 6379)
- network

---

## Step 5: Set Up Nginx Reverse Proxy

Nginx acts as a security layer and handles SSL certificates.

### Install Nginx:

```bash
apt install -y nginx
systemctl start nginx
systemctl enable nginx
```

### Create Nginx config:

```bash
cat > /etc/nginx/sites-available/voice-api << 'EOF'
upstream voice_api {
    server localhost:8000;
}

upstream voice_stt {
    server localhost:8001;
}

server {
    listen 80;
    server_name voice.yourdomain.com;

    # Redirect HTTP to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name voice.yourdomain.com;

    # SSL certificates (generated later with Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/voice.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/voice.yourdomain.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;

    # Main API routes
    location /v1/ {
        proxy_pass http://voice_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Long timeout for async operations
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://voice_api;
        proxy_set_header Host $host;
    }
}
EOF
```

Replace `voice.yourdomain.com` with your actual domain.

### Enable the config:

```bash
ln -s /etc/nginx/sites-available/voice-api /etc/nginx/sites-enabled/
nginx -t  # Test config
systemctl reload nginx
```

---

## Step 6: Set Up SSL with Let's Encrypt

This makes your API secure (HTTPS).

### Install Certbot:

```bash
apt install -y certbot python3-certbot-nginx
```

### Generate certificate:

```bash
# Replace with your domain
certbot certonly --standalone -d voice.yourdomain.com
```

Follow the prompts. This creates `/etc/letsencrypt/live/voice.yourdomain.com/` with your certificates.

### Reload Nginx:

```bash
systemctl reload nginx
```

### Auto-renew certificates:

```bash
systemctl enable certbot.timer
systemctl start certbot.timer
```

---

## Step 7: Point Your Domain

In your domain registrar (GoDaddy, Namecheap, etc.):

1. Find DNS settings
2. Create an A record:
   - Name: `voice`
   - Type: `A`
   - Value: `1.2.3.4` (your server's IP)
3. Save

Wait a few minutes for DNS to propagate.

Test it:

```bash
curl https://voice.yourdomain.com/health
```

You should see:
```json
{"status":"ok","service":"Ghost Voice OS","version":"1.0.0","tenants":2}
```

---

## Step 8: Update Telnyx & Twilio Webhooks

### In Telnyx Mission Control:

1. Go to Connections → Your Connection
2. Set Webhook URL to: `https://voice.yourdomain.com/v1/webhooks/telnyx`
3. Save

### In Twilio Console:

1. Go to Phone Numbers → Manage → Your Number
2. Set Voice webhook to: `https://voice.yourdomain.com/v1/webhooks/twilio/answer`
3. Save

---

## Step 9: Monitor & Maintain

### View logs:

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f voice-api

# Nginx errors
tail -f /var/log/nginx/error.log
```

### Restart services:

```bash
# Restart everything
docker compose restart

# Restart specific service
docker compose restart voice-api
```

### Update codebase:

```bash
cd /root/ghost-voice-os
git pull origin main
docker compose up -d --build
```

---

## Troubleshooting

### "Connection refused" on port 8000?

Services may still be starting. Wait 30 seconds:

```bash
docker compose ps  # Check status
docker compose logs voice-api  # See errors
```

### SSL certificate error?

Make sure domain is pointing to server:

```bash
nslookup voice.yourdomain.com
```

Should show your server's IP. If not, wait for DNS propagation (up to 1 hour).

### Can't connect via SSH?

1. Check if server is running (Hetzner console)
2. Verify firewall allows port 22 (default in Hetzner)
3. Check SSH key permissions: `chmod 600 ~/.ssh/hetzner_key`

### Calls dropping?

Check Redis and OpenSearch are healthy:

```bash
docker compose ps
# Look for "healthy" status

docker exec ghost-voice-redis redis-cli ping
# Should respond: PONG

curl -s http://localhost:9200/_cluster/health | jq .
```

---

## Next Steps

Once deployment is complete:

1. **Test with staging number:**
   - Create a test number in Telnyx/Twilio
   - Point it to Voice OS
   - Make a test call
   - Verify transcription in OpenSearch

2. **Set up monitoring:**
   - New Relic, DataDog, or Sentry for error tracking

3. **Implement Priority 4 (Call Orchestrator):**
   - Adds bulk calling, scheduling, retries

---

## Getting Help

If you get stuck:

1. Check Docker logs: `docker compose logs -f`
2. Check Nginx logs: `tail -f /var/log/nginx/error.log`
3. SSH to server and test manually
4. Visit Hetzner Console → Logs tab

---

**Congratulations!**

You now have Ghost Voice OS running on production infrastructure.

This is the same stack used by production voice AI platforms.

Next: Connect GhostCRM as a REST client and start routing calls through Voice OS.
