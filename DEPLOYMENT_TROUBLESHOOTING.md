# Ghost Voice OS - Deployment Troubleshooting Guide

## Common Issues & Solutions

### 🔴 Docker Issues

#### "docker: command not found"
The deployment script didn't finish or wasn't run as root.

**Solution:**
```bash
# Run as root
sudo -i

# Then re-run deployment
curl -sSL https://raw.githubusercontent.com/burchdad/ghost-voice-os/main/scripts/deploy.sh | bash
```

#### "Cannot connect to Docker daemon"
Docker isn't running.

**Solution:**
```bash
systemctl start docker
systemctl enable docker
docker ps  # Should work now
```

---

### 🔴 Container won't start

#### "CrashLoopBackOff" status
A service is failing to start.

**Diagnose:**
```bash
cd /root/ghost-voice-os

# See which service is failing
docker compose ps

# View its logs
docker compose logs voice-api    # Replace with failing service
docker compose logs voice-stt-whisper
docker compose logs opensearch
```

#### Common cause: Missing environment variables
```bash
# Check .env file
cat /root/ghost-voice-os/.env

# Make sure you filled in actual values (not "your_xxx")
nano /root/ghost-voice-os/.env

# Restart
docker compose restart
```

#### Common cause: Port already in use
```bash
# Check what's using ports
lsof -i :8000  # voice-api
lsof -i :8001  # voice-stt
lsof -i :9200  # opensearch
lsof -i :6379  # redis

# If something else is using them, kill it:
kill -9 <PID>

# Then restart services
docker compose restart
```

---

### 🔴 DNS Issues

#### "curl: (6) Could not resolve host"
Your domain isn't pointing to the server.

**Diagnose:**
```bash
nslookup voice.yourdomain.com

# Should show your server's IP
# If it shows something else or "can't find", DNS not updated yet
```

**Solution:**
1. Wait 5-30 minutes for DNS propagation
2. Check your domain registrar DNS settings
3. Ensure A record points to correct IP
4. Try `nslookup voice.yourdomain.com 8.8.8.8` (Google's DNS)

#### "Connection refused" vs DNS resolved
DNS works but server not responding.

**Check if services running:**
```bash
docker compose ps

# Should show all 5 services
# If any say "Exited", see Container Issues above
```

---

### 🔴 SSL/Nginx Issues

#### "SSL_ERROR_BAD_CERT_DOMAIN"
Certificate domain doesn't match request domain.

**Check certificate:**
```bash
ls -la /etc/letsencrypt/live/

# Should see your domain
# If empty, run setup-ssl.sh
```

**Solution:**
```bash
# If it's a different domain, regenerate:
certbot revoke /etc/letsencrypt/live/OLD_DOMAIN/fullchain.pem --email admin@yourdomain.com

# Then rerun:
/root/ghost-voice-os/scripts/setup-ssl.sh voice.yourdomain.com
```

#### "Nginx: [emerg] bind() to 0.0.0.0:443 failed"
Another process is using port 443.

**Solution:**
```bash
# Check what's using it
lsof -i :443

# Kill it
kill -9 <PID>

# Restart Nginx
systemctl reload nginx
```

#### "Nginx successful, but site still shows 502 Bad Gateway"
Nginx is routing to voice-api but it's not responding.

**Check voice-api is running:**
```bash
curl http://localhost:8000/health

# Should work if running locally
# If not, service isn't responding
```

**View voice-api logs:**
```bash
docker compose logs voice-api

# Look for Python errors
```

---

### 🔴 Service Connection Issues

#### "Connection refused" on port 8000/8001 from outside server
Firewall is blocking ports, or services aren't bound to 0.0.0.0.

**Check Hetzner firewall:**
1. Go to Hetzner Console
2. Firewalls → Your Firewall
3. Ensure rules allow ports 80, 443, 8000, 8001
4. If not, add them

**Test locally on server:**
```bash
curl http://localhost:8000/health
curl http://localhost:8001/health

# If these work but external access fails = firewall issue
```

---

### 🔴 OpenSearch Issues

#### "OpenSearch won't start - keeps restarting"
Usually memory or vm.max_map_count issue.

**Check logs:**
```bash
docker compose logs opensearch | tail -50

# Look for "memory" or "max_map_count" errors
```

**Solution - increase max_map_count:**
```bash
# On host (not in container)
sysctl -w vm.max_map_count=262144

# Make permanent
echo "vm.max_map_count=262144" >> /etc/sysctl.conf
sysctl -p

# Restart
docker compose restart opensearch
```

#### "OpenSearch high memory usage"
It's fine - OpenSearch uses memory aggressively by design.

You can limit it in docker-compose.yml:
```yaml
environment:
  - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
```

---

### 🔴 Webhook Issues

#### "Telnyx/Twilio calling but no activity in Voice OS"
Webhooks aren't reaching your API.

**Check webhook URL in provider console:**
```bash
# Telnyx: https://voice.yourdomain.com/v1/webhooks/telnyx
# Twilio: https://voice.yourdomain.com/v1/webhooks/twilio/answer
```

**Test the webhook manually:**
```bash
curl -X POST https://voice.yourdomain.com/v1/webhooks/telnyx \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "event_type": "hook.incoming_call",
      "payload": {
        "from": "+1234567890",
        "to": "+0987654321"
      }
    }
  }'
```

Should respond with 200 and call created.

**Enable webhook logging:**
```bash
# Temporarily increase logging
docker compose exec voice-api bash
python -c "import logging; logging.basicConfig(level=logging.DEBUG)"

# View detailed logs
docker compose logs -f voice-api | grep "webhook"
```

---

### 🔴 Transcription Issues

#### "Calls complete but no transcripts"
STT service not transcribing or callback failing.

**Check STT service:**
```bash
curl http://localhost:8001/health

# Should work
```

**View STT logs:**
```bash
docker compose logs voice-stt-whisper | tail -100

# Look for errors during transcription
```

**Test transcription manually:**
```bash
# Create a test audio file (or use existing)
curl -X POST http://localhost:8001/v1/transcribe \
  -F "file=@test.mp3" \
  -F "tenant_id=default" \
  -F "session_id=test-123" \
  -F "language=en" \
  -H "Content-Type: multipart/form-data"

# Should return job_id
```

**Check if callback received:**
```bash
# In voice-api logs
docker compose logs voice-api | grep "callback"
```

---

### 🔴 Performance Issues

#### "Slow response times"
Could be multiple issues.

**Check resource usage:**
```bash
# CPU and memory
docker stats

# Disk space
df -h

# Watch in real-time
watch 'docker stats --no-stream'
```

**If low on disk:**
```bash
# Clean up Docker
docker system prune -a

# Remove old logs
docker compose logs --tail 0 > /dev/null
```

**If high CPU:**
- OpenSearch indexing (normal during high traffic)
- STT processing multiple audio files
- Check for error loops in logs

**If high memory:**
```bash
# OpenSearch uses lots of memory by default
# Check OpenSearch Java heap size

docker compose exec opensearch jps -lmv | grep Elasticsearch
```

---

### 🔴 Connectivity Issues

#### "Can SSH but no internet"
Server might not have internet or firewall blocks outbound.

**Test internet:**
```bash
ping 8.8.8.8

# If no response, contact Hetzner support
# If response, firewall may block specific ports
```

**Check if Telnyx/Twilio API calls work:**
```bash
# Test Telnyx
curl -H "Authorization: Bearer $TELNYX_API_KEY" \
  https://api.telnyx.com/v2/messaging_profiles

# Test OpenAI
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models
```

---

### 🔴 Certificate/SSL Issues

#### "SSL certificate will expire in X days"
Let's Encrypt has auto-renewal but may have failed.

**Check renewal:**
```bash
certbot renew --dry-run

# Should show successful renewal or error
```

**Manual renewal:**
```bash
certbot renew --force-renewal

# Then reload Nginx
systemctl reload nginx
```

#### "OSCP stapling errors in logs"
Usually harmless, but indicates OSCP server issues.

**Won't affect functionality** - just ignore.

---

## Getting Help

### Useful diagnostic commands:

```bash
# Full service status
docker compose ps -a

# Real-time logs (all services)
docker compose logs -f

# Single service logs
docker compose logs -f voice-api

# System resource usage
docker stats

# Network connectivity
docker network ls
docker network inspect ghost-voice-os_default

# DNS check
nslookup voice.yourdomain.com
dig voice.yourdomain.com

# Port availability
lsof -i :8000
lsof -i :443

# Nginx test
nginx -t
systemctl status nginx

# SSL certificate info
certbot certificates

# Full system info
uname -a
df -h
free -h
```

### Still stuck?

1. **Collect information:**
   ```bash
   docker compose ps > status.txt
   docker compose logs --tail=100 > logs.txt
   curl https://voice.yourdomain.com/health > health.txt
   ```

2. **Check official docs:**
   - Docker Compose: https://docs.docker.com/compose/
   - Let's Encrypt: https://letsencrypt.org/docs/
   - Nginx: https://nginx.org/en/docs/
   - Hetzner: https://docs.hetzner.cloud/

3. **Common solution:** Turn it off and on again
   ```bash
   docker compose down
   docker compose up -d
   
   # Wait 30-60 seconds
   /root/ghost-voice-os/scripts/validate-deployment.sh
   ```

---

**Most issues resolve with these steps. If you're still stuck, the logs should tell you what's wrong.** 🔧
