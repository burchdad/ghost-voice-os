#!/bin/bash
# Ghost Voice OS - SSL & Nginx Setup
# Run after domain is pointing to your server

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 yourdomain.com"
    echo "Example: $0 voice.ghostcrm.ai"
    exit 1
fi

DOMAIN=$1

echo "🔐 Setting up SSL for $DOMAIN"
echo "================================"

# Step 1: Generate SSL certificate
echo "📜 Step 1: Generating Let's Encrypt certificate..."
certbot certonly --standalone -d "$DOMAIN" --non-interactive --agree-tos -m admin@$DOMAIN --expand

# Step 2: Create Nginx config
echo "🌐 Step 2: Creating Nginx configuration..."
cat > /etc/nginx/sites-available/voice-api << EOF
upstream voice_api {
    server localhost:8000;
}

server {
    listen 80;
    server_name $DOMAIN;

    # Redirect HTTP to HTTPS
    location / {
        return 301 https://\$server_name\$request_uri;
    }

    # Let's Encrypt validation
    location /.well-known/acme-challenge/ {
        allow all;
    }
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    # SSL optimization
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Logging
    access_log /var/log/nginx/voice-api-access.log;
    error_log /var/log/nginx/voice-api-error.log;

    # API routes
    location /v1/ {
        proxy_pass http://voice_api;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        
        # Long timeout for async operations
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://voice_api;
        proxy_set_header Host \$host;
        access_log off;
    }

    # Root path
    location / {
        proxy_pass http://voice_api;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Static files (if any)
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        proxy_pass http://voice_api;
        add_header Cache-Control "public, max-age=3600";
    }
}
EOF

# Step 3: Enable Nginx config
echo "🔗 Step 3: Enabling Nginx configuration..."
ln -sf /etc/nginx/sites-available/voice-api /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test Nginx config
if ! nginx -t; then
    echo "❌ Nginx configuration error"
    exit 1
fi

# Step 4: Reload Nginx
echo "🔄 Step 4: Reloading Nginx..."
systemctl reload nginx

# Step 5: Enable automatic certificate renewal
echo "♻️  Step 5: Enabling automatic certificate renewal..."
systemctl enable certbot.timer
systemctl start certbot.timer

echo ""
echo "================================"
echo "✅ SSL Setup Complete!"
echo "================================"
echo ""
echo "Your site is now available at:"
echo "https://$DOMAIN"
echo ""
echo "Verify it works:"
echo "curl https://$DOMAIN/health"
echo ""
echo "View logs:"
echo "tail -f /var/log/nginx/voice-api-error.log"
echo ""
