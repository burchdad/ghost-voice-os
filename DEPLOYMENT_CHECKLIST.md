# Ghost Voice OS - Quick Deployment Checklist

## Phase 1: Server Setup (15 minutes)

### 1. Create Hetzner Account & Server
- [ ] Go to https://www.hetzner.com/cloud
- [ ] Sign up → Create project → Create server
- [ ] Choose Ubuntu 24.04
- [ ] Choose CPX11 (€3.99/month)
- [ ] Add SSH key (generate one if needed)
- [ ] Wait for server to boot
- [ ] Note: Server IP address: `_________________`

### 2. SSH to Server
```bash
# Replace with your IP
ssh root@YOUR_SERVER_IP

# Should see a prompt
```

### 3. Run Deployment Script
```bash
# On the server, paste this:
curl -sSL https://raw.githubusercontent.com/burchdad/ghost-voice-os/main/scripts/deploy.sh | bash
```

### 4. Edit Configuration
```bash
nano /root/ghost-voice-os/.env
```

Add your credentials:
- `TELNYX_API_KEY` from Telnyx dashboard
- `TELNYX_CONNECTION_ID` from Telnyx
- `TELNYX_PHONE_NUMBER` your Telnyx number
- `TWILIO_ACCOUNT_SID` from Twilio console
- `TWILIO_AUTH_TOKEN` from Twilio console
- `TWILIO_PHONE_NUMBER` your Twilio number
- `OPENAI_API_KEY` from OpenAI dashboard
- `VOICE_OS_BASE_URL` your domain (e.g., https://voice.ghostcrm.ai)

Save: `Ctrl+X`, `Y`, `Enter`

---

## Phase 2: Domain & DNS (5 minutes)

### 5. Point Domain to Server
In your domain registrar (GoDaddy, Namecheap, Vercel, etc.):

- [ ] Find DNS settings
- [ ] Create A record:
  - **Name:** `voice`
  - **Type:** `A`
  - **Value:** `YOUR_SERVER_IP`
- [ ] Save

Example if using voice.ghostcrm.ai:
```
voice.ghostcrm.ai  A  YOUR_SERVER_IP
```

Wait 5-10 minutes for DNS to propagate.

### 6. Test DNS Resolution
```bash
# From your local computer:
nslookup voice.yourdomain.com

# Should show your server's IP
```

---

## Phase 3: SSL & Nginx (10 minutes)

### 7. Start Voice OS Services
```bash
# SSH to server, then:
cd /root/ghost-voice-os
docker compose up -d
```

Wait ~30 seconds for services to start.

### 8. Set Up SSL
```bash
# On server:
/root/ghost-voice-os/scripts/setup-ssl.sh voice.yourdomain.com
```

Replace `voice.yourdomain.com` with your actual domain.

### 9. Verify Everything Works
```bash
# Local computer, test the domain:
curl https://voice.yourdomain.com/health

# Should see:
# {"status":"ok","service":"Ghost Voice OS","version":"1.0.0","tenants":2}
```

---

## Phase 4: Connect Providers (10 minutes)

### 10. Update Telnyx Webhook
In Telnyx Mission Control:
- [ ] Go to Connections → Your Connection
- [ ] Webhook URL: `https://voice.yourdomain.com/v1/webhooks/telnyx`
- [ ] Save

### 11. Update Twilio Webhook
In Twilio Console:
- [ ] Phone Numbers → Manage → Your Number
- [ ] Voice webhook: `https://voice.yourdomain.com/v1/webhooks/twilio/answer`
- [ ] Save

---

## Phase 5: Test (15 minutes)

### 12. Make a Test Call
Option 1: Using Twilio CLI
```bash
twilio api:core:phone-calls:list
```

Option 2: Using Telnyx API
```bash
curl -X POST https://api.telnyx.com/v2/calls \
  -H "Authorization: Bearer YOUR_TELNYX_API_KEY" \
  -d '{...call params...}'
```

### 13. Verify in OpenSearch
```bash
# On server:
curl -s http://localhost:9200/calls/_search | jq '.hits.hits[0]'

# Should see call record
```

### 14. Check Transcripts
```bash
curl -s http://localhost:9200/transcripts/_search | jq '.hits.hits[0]'

# Should see transcript with segments
```

---

## Phase 6: Monitoring (5 minutes)

### 15. View Logs Remotely
```bash
# On server:
docker compose logs -f voice-api

# Or for specific service:
docker compose logs -f voice-stt-whisper
```

### 16. Check Health
```bash
# On server:
/root/ghost-voice-os/scripts/validate-deployment.sh
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Can't SSH | Check Hetzner console - server running? |
| Services not starting | `docker compose logs -f` - see errors |
| Domain not resolving | Run `nslookup voice.yourdomain.com` - DNS may need more time |
| SSL certificate error | Ensure domain is resolving to server IP |
| Calls not routing | Check Telnyx/Twilio webhook URLs in console |
| No transcripts | Ensure OpenSearch is running: `docker compose ps` |

---

## Estimated Timeline

| Phase | Time | Status |
|-------|------|--------|
| Server setup | 15 min | - |
| Domain & DNS | 5 min | - |
| SSL & Nginx | 10 min | - |
| Connect providers | 10 min | - |
| Test & verify | 15 min | - |
| **TOTAL** | **~55 minutes** | - |

---

## Next Steps After Deployment

Once live:

1. **Run real test calls** to verify the full pipeline
2. **Monitor logs** for errors
3. **Set up alerts** (New Relic, DataDog, Sentry)
4. **Connect GhostCRM** as a REST client
5. **Implement Priority 4** (Call Orchestrator for bulk calling)

---

## Important Files

On your server:
```
/root/ghost-voice-os/.env              <- Your credentials (KEEP SAFE!)
/root/ghost-voice-os/docker-compose.yml    <- Service definitions
/var/log/nginx/voice-api-error.log    <- Nginx errors
```

View logs:
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f voice-api
docker compose logs -f voice-stt-whisper
docker compose logs -f opensearch
```

---

## Rollback / Updates

### To update code:
```bash
cd /root/ghost-voice-os
git pull origin main
docker compose up -d --build
```

### To restart a service:
```bash
docker compose restart voice-api
docker compose restart voice-stt-whisper
```

### To stop everything:
```bash
docker compose down
```

---

**You're ready to deploy! Let's go.** 🚀
