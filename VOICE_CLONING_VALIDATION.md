# Voice Cloning Validation & Testing Guide
## Pre-Deployment Checklist

---

## ✅ Pre-Launch Validation

### 1. File Structure Verification

Run this check to ensure all files exist:

```bash
#!/bin/bash
echo "🔍 Checking voice cloning files..."

files=(
  "services/voice-api/providers/streaming/local_tts.py"
  "services/voice-api/routes/voices.py"
  "services/voice-api/main.py"
  "services/voice-api/routes/streaming.py"
  "examples/voice_cloning_demo.py"
)

for file in "${files[@]}"; do
  if [ -f "$file" ]; then
    lines=$(wc -l < "$file")
    echo "✅ $file ($lines lines)"
  else
    echo "❌ MISSING: $file"
    exit 1
  fi
done

echo ""
echo "✅ All files present!"
```

**Expected output:**
```
✅ services/voice-api/providers/streaming/local_tts.py (200+ lines)
✅ services/voice-api/routes/voices.py (240+ lines)
✅ services/voice-api/main.py (updated)
✅ services/voice-api/routes/streaming.py (updated)
✅ examples/voice_cloning_demo.py (280+ lines)
✅ All files present!
```

### 2. Code Imports Verification

Ensure all imports work:

```bash
cd services/voice-api

# Quick import check
python3 -c "from routes.voices import router; print('✅ voices router imports OK')"
python3 -c "from providers.streaming.local_tts import LocalTTSProvider; print('✅ LocalTTSProvider imports OK')"
python3 -c "from routes.streaming import get_tts_provider; print('✅ Streaming utils import OK')"
```

**Expected output:**
```
✅ voices router imports OK
✅ LocalTTSProvider imports OK
✅ Streaming utils import OK
```

### 3. Main Application Startup

```bash
cd services/voice-api

# Start server (will run in foreground, Ctrl+C to stop)
python3 main.py
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

**Verify in another terminal:**
```bash
curl http://localhost:8000/health
# Should return 200 OK with health data
```

### 4. Voice Storage Directory Creation

```bash
# Check/Create voice storage directory
ls -la services/voice-api/voices/ 2>/dev/null || \
  mkdir -p services/voice-api/voices/{fingerprints,metadata}
echo "✅ Voice storage directory ready"
```

---

## 🧪 API Endpoint Testing

### Test 1: Health Check

```bash
curl -s http://localhost:8000/health | jq '.'
```

**Expected:**
```json
{
  "status": "ok",
  "timestamp": "2026-03-03T22:45:15"
}
```

### Test 2: List Empty Voices

```bash
curl -s http://localhost:8000/v1/voices/list \
  -H "X-User-ID: test_user_1" \
  -H "X-Tenant-ID: ghostcrm" | jq '.'
```

**Expected:**
```json
{
  "user_id": "test_user_1",
  "voices": [],
  "count": 0
}
```

### Test 3: Register a Test Voice

First, create a test audio file:

```bash
# Generate 3-second test audio using sox (if available)
if command -v sox &> /dev/null; then
  sox -n -r 16000 -c 1 -b 16 test_voice.wav synth 3 sine 200
  echo "✅ Created test_voice.wav (3 seconds)"
else
  # Or download one
  curl -s https://www.sample-videos.com/audio/mp3/crowd-cheering.mp3 -o test_voice.wav
  echo "✅ Downloaded test_voice.wav"
fi
```

Now register it:

```bash
curl -s -X POST http://localhost:8000/v1/voices/register \
  -H "X-User-ID: test_user_1" \
  -H "X-Tenant-ID: ghostcrm" \
  -F "file=@test_voice.wav" \
  -F "voice_name=Test Voice" | jq '.'
```

**Expected:**
```json
{
  "status": "success",
  "voice_id": "test_user_1_custom_...",
  "voice_details": {
    "voice_name": "Test Voice",
    "registered_at": "2026-03-03T22:45:15",
    "file_size": 96000
  }
}
```

**Save the `voice_id` for next tests!**

### Test 4: List Registered Voices

```bash
curl -s http://localhost:8000/v1/voices/list \
  -H "X-User-ID: test_user_1" \
  -H "X-Tenant-ID: ghostcrm" | jq '.'
```

**Expected:**
```json
{
  "user_id": "test_user_1",
  "voices": [
    {
      "voice_id": "test_user_1_custom_...",
      "name": "Test Voice",
      "registered_at": "2026-03-03T22:45:15"
    }
  ],
  "count": 1
}
```

### Test 5: Get Voice Info

```bash
VOICE_ID="test_user_1_custom_..."  # Use output from Test 3

curl -s http://localhost:8000/v1/voices/info \
  -H "X-User-ID: test_user_1" \
  -H "X-Tenant-ID: ghostcrm" \
  -d "voice_id=$VOICE_ID" | jq '.'
```

**Expected:**
```json
{
  "voice_id": "test_user_1_custom_...",
  "name": "Test Voice",
  "registered_at": "2026-03-03T22:45:15",
  "characteristics": {
    "pitch": 0.65,
    "clarity": 0.82,
    "stability": 0.78,
    "energy": 0.71,
    "brightness": 0.58
  }
}
```

### Test 6: Provider Health Check

```bash
curl -s -X POST http://localhost:8000/v1/voices/provider/health \
  -H "X-User-ID: test_user_1" \
  -H "X-Tenant-ID: ghostcrm" | jq '.'
```

**Expected:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-03T22:45:15",
  "voice_storage": {
    "total_voices": 1,
    "total_size_mb": 0.09
  }
}
```

### Test 7: Cost Comparison

```bash
curl -s http://localhost:8000/v1/voices/comparison | jq '.'
```

**Expected:**
```json
{
  "comparison": {
    "ghost_voice_os": {
      "cost_per_request": 0.0,
      "voice_cloning": true,
      "setup_time": "instant"
    },
    "elevenlabs": {
      "cost_per_request": 0.03,
      "voice_cloning": "premium",
      "setup_time": "minutes"
    }
  },
  "savings_at_scale": {
    "1k_requests": {
      "monthly": 30,
      "annual": 360
    },
    ...
  }
}
```

### Test 8: WebSocket Connection (Basic)

```bash
#!/bin/bash
# Test WebSocket connection (requires wscat)
# npm install -g wscat

VOICE_ID="test_user_1_custom_..."  # From Test 3

wscat -c "ws://localhost:8000/v1/stream/ws/call/test-session-1?tts_provider=local_tts&voice_id=$VOICE_ID"

# You can now type JSON messages:
# Connected (>) >
# Type: {"type": "conversation_message", "content": "Hello world"}
# Ctrl+C to exit
```

**Expected behavior:**
- Connection establishes
- Can send messages
- Receives response messages with `type: audio_chunk`

---

## 🔄 Integration Test Suite

Create `tests/test_voice_cloning.py`:

```python
import pytest
import asyncio
from pathlib import Path
from httpx import AsyncClient
from main import app

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def test_audio_file():
    """Create a minimal test audio file."""
    import wave
    import struct
    
    # Generate simple sine wave
    sample_rate = 16000
    duration = 3  # seconds
    frequency = 200  # Hz
    
    frames = []
    for i in range(int(sample_rate * duration)):
        value = int(32767.0 * 0.3 * 
                   np.sin(2.0 * np.pi * frequency * i / sample_rate))
        frames.append(struct.pack('<h', value))
    
    # Write to file
    with wave.open("test_audio.wav", "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b''.join(frames))
    
    yield Path("test_audio.wav")
    Path("test_audio.wav").unlink()

@pytest.mark.asyncio
async def test_register_voice(client, test_audio_file):
    """Test voice registration."""
    with open(test_audio_file, "rb") as f:
        response = await client.post(
            "/v1/voices/register",
            files={"file": f, "voice_name": "Test"},
            headers={
                "X-User-ID": "test_user",
                "X-Tenant-ID": "test_tenant"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "voice_id" in data
    return data["voice_id"]

@pytest.mark.asyncio
async def test_list_voices(client):
    """Test listing voices."""
    response = await client.get(
        "/v1/voices/list",
        headers={
            "X-User-ID": "test_user",
            "X-Tenant-ID": "test_tenant"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "voices" in data
    assert "count" in data

@pytest.mark.asyncio
async def test_health_check(client):
    """Test provider health check."""
    response = await client.post(
        "/v1/voices/provider/health",
        headers={
            "X-User-ID": "test_user",
            "X-Tenant-ID": "test_tenant"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
```

Run tests:

```bash
cd services/voice-api
pytest tests/test_voice_cloning.py -v
```

---

## 📊 Performance Testing

### Latency Test

```python
import time
import httpx

# Test voice registration latency
start = time.time()
response = httpx.post(
    "http://localhost:8000/v1/voices/register",
    files={"file": open("test_voice.wav", "rb")},
    headers={"X-User-ID": "perf_test"}
)
latency = (time.time() - start) * 1000

print(f"Voice registration latency: {latency:.1f}ms")
assert latency < 5000, "Registration should complete in <5 seconds"
```

**Expected:**
```
Voice registration latency: 150.2ms ✅
```

### Throughput Test

```bash
#!/bin/bash
# Register 10 voices and measure throughput

echo "Starting throughput test..."
start=$(date +%s%N | cut -b1-13)

for i in {1..10}; do
  curl -s -X POST http://localhost:8000/v1/voices/register \
    -H "X-User-ID: perf_user_$i" \
    -F "file=@test_voice.wav" > /dev/null
done

end=$(date +%s%N | cut -b1-13)
elapsed=$((end - start))
throughput=$(echo "scale=2; 10000 / $elapsed" | bc)

echo "Registered 10 voices in ${elapsed}ms"
echo "Throughput: $throughput voices/second"
```

### Memory Test

```bash
# Monitor memory while running stress test
watch -n 0.5 'ps aux | grep main.py | grep -v grep'

# In another terminal, hammer the server
for i in {1..100}; do
  curl -s http://localhost:8000/v1/voices/list \
    -H "X-User-ID: stress_test" > /dev/null &
done
wait

# Memory should not grow unbounded
```

---

## 📁 Storage Validation

### Check Voice Storage

```bash
# Navigate to voice storage
cd services/voice-api/voices

# List all fingerprints
echo "Registered voices:"
ls -lh fingerprints/ | tail -5

# Check registry
echo "\nVoice registry:"
cat registry.json | jq '.users | keys'

# Calculate total storage
du -sh .
```

**Expected output:**
```
Registered voices:
-rw-r--r-- 1 user group 2.1K Mar 3 22:45 test_user_1_custom_....json
...

Voice registry:
[
  "test_user_1"
]

Total storage: 10M
```

---

## 🔐 Security Validation

### Test Multi-Tenant Isolation

```bash
# Register voice as user_1
VOICE_ID=$(curl -s -X POST http://localhost:8000/v1/voices/register \
  -H "X-User-ID: user_1" \
  -H "X-Tenant-ID: ghostcrm" \
  -F "file=@test_voice.wav" | jq -r '.voice_id')

echo "User 1 voice: $VOICE_ID"

# Try to access as user_2 (should fail or return empty)
curl -s http://localhost:8000/v1/voices/list \
  -H "X-User-ID: user_2" \
  -H "X-Tenant-ID: ghostcrm" | jq '.count'

# Should return 0, not 1 ✅
```

### Test Missing Headers

```bash
# Try without X-User-ID header
curl -s -X POST http://localhost:8000/v1/voices/register \
  -F "file=@test_voice.wav" \
  -H "X-Tenant-ID: ghostcrm"

# Should return 401 Unauthorized or 400 Bad Request ✅
```

---

## 🎯 Pre-Production Checklist

Before deploying to production:

### Code Quality
- [ ] All imports pass
- [ ] No syntax errors: `python -m py_compile *.py`
- [ ] All endpoints tested
- [ ] All error cases handled

### Performance
- [ ] Voice registration: <5 seconds
- [ ] Voice listing: <500ms
- [ ] Health check: <100ms
- [ ] Memory stable: No leaks observed

### Storage
- [ ] Voice directory exists
- [ ] Registry file created
- [ ] Directories have proper permissions
- [ ] Enough disk space: `df -h`

### Security
- [ ] Multi-tenant isolation works
- [ ] Headers properly validated
- [ ] Rate limiting configured (optional)
- [ ] Data not logged accidentally

### Integration
- [ ] Routes registered in main.py
- [ ] WebSocket endpoint accessible
- [ ] TTS provider selection works
- [ ] Streaming pipeline unchanged

### Documentation
- [ ] README.md up to date
- [ ] API endpoints documented
- [ ] Examples work
- [ ] Deployment guide clear

### Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] No test data left in production

---

## ✅ Sign-Off Checklist

**For QA:**
- [ ] Test all voice cloning workflows
- [ ] Verify storage isolation
- [ ] Validate cost comparison accuracy
- [ ] Test error cases

**For DevOps:**
- [ ] Docker image builds
- [ ] Kubernetes manifest ready
- [ ] Environment variables configured
- [ ] Monitoring/logging configured

**For Product:**
- [ ] Feature complete
- [ ] UX validated
- [ ] Marketing ready
- [ ] Competitor analysis accurate

**For Security:**
- [ ] No credentials in code
- [ ] Data properly encrypted
- [ ] Audit logging works
- [ ] Dependencies scanned for CVEs

---

## 🚀 Go-Live Procedure

1. **Backup current production**
   ```bash
   tar -czf voice-api-backup-$(date +%s).tar.gz services/voice-api/
   ```

2. **Deploy new version**
   ```bash
   kubectl apply -f deployment/kubernetes/voice-api.yaml
   ```

3. **Verify deployment**
   ```bash
   curl -s http://your-domain/health | jq '.status'
   ```

4. **Monitor for errors**
   ```bash
   kubectl logs -f deployment/voice-api
   ```

5. **Test critical paths**
   - Voice registration
   - Voice listing
   - WebSocket streaming
   - Cost comparison

6. **Announce to users**
   - Blog post
   - Email announcement
   - Product tour video

---

## 📞 Rollback Plan

If issues occur:

```bash
# 1. Identify the issue
kubectl logs -f deployment/voice-api | grep ERROR

# 2. Rollback to previous version
kubectl rollout undo deployment/voice-api

# 3. Verify rollback
kubectl get pods

# 4. Post-mortem
# Document what went wrong and how to prevent it
```

---

## 🎉 Success Criteria

Your voice cloning feature is ready when:

✅ All tests pass
✅ No errors in logs
✅ Latencies meet targets (<700ms first chunk)
✅ Storage usage acceptable
✅ Multi-tenant isolation works
✅ Security review passed
✅ Team agrees on go-live

---

**Status: Ready to validate!** 🚀
