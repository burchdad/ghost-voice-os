# Voice Cloning Quick Start Guide
## Get Your AI Speaking With Your Voice in 5 Minutes

---

## ⚡ Prerequisites

- Local TTS Provider installed (`providers/streaming/local_tts.py`)
- Voice routes registered (`routes/voices.py`)
- Ghost Voice OS server running
- Audio file (WAV recommended, 30+ seconds)

---

## 🎬 5-Minute Setup

### Step 1: Start the Server

```bash
cd services/voice-api
python main.py
```

Expected output:
```
Uvicorn running on http://127.0.0.1:8000
```

### Step 2: Prepare Your Voice Recording

Get an audio file (WAV, MP3, or M4A):
- Duration: 30+ seconds (more is better)
- Content: Natural speech, multiple sentences
- Quality: Clear without background noise

Example using macOS:
```bash
# Record 30 seconds of your voice
afplay -h  # Check your audio config
# Then record using Voice Memos app or:
# sox -d test_voice.wav
```

### Step 3: Register Your Voice

```bash
curl -X POST http://localhost:8000/v1/voices/register \
  -H "X-User-ID: your_user_id" \
  -H "X-Tenant-ID: ghostcrm" \
  -F "file=@test_voice.wav" \
  -F "voice_name=My Custom Voice"
```

**Response:**
```json
{
  "status": "success",
  "voice_id": "your_user_id_custom_20260303_224515",
  "message": "Voice registered! Use this ID for synthesis",
  "voice_details": {
    "voice_name": "My Custom Voice",
    "registered_at": "2026-03-03T22:45:15",
    "file_size": 1250000
  }
}
```

💾 **Save the `voice_id` - you'll need it next**

### Step 4: Use Your Voice in a Call

Connect via WebSocket with your voice ID:

```javascript
// Simple WebSocket client
const voiceId = "your_user_id_custom_20260303_224515";
const ws = new WebSocket(
  `ws://localhost:8000/v1/stream/ws/call/test-session-1?tts_provider=local_tts&voice_id=${voiceId}`
);

ws.onopen = () => {
  console.log("Connected!");
  // Send: { "type": "conversation_message", "content": "Hello, this is my voice!" }
  ws.send(JSON.stringify({
    type: "conversation_message",
    content: "Hello, this is my voice!"
  }));
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === "audio_chunk") {
    // Play audio chunk
    console.log("Received audio chunk");
  }
};
```

### Step 5: Test via REST API

```bash
# List your voices
curl http://localhost:8000/v1/voices/list \
  -H "X-User-ID: your_user_id" \
  -H "X-Tenant-ID: ghostcrm"
```

Response:
```json
{
  "user_id": "your_user_id",
  "voices": [
    {
      "voice_id": "your_user_id_custom_20260303_224515",
      "name": "My Custom Voice",
      "registered_at": "2026-03-03T22:45:15"
    }
  ],
  "count": 1
}
```

---

## 🎙️ Complete API Reference

### Register a Voice

```
POST /v1/voices/register

Headers:
  X-User-ID: <user_id>
  X-Tenant-ID: <tenant_id>

Body (multipart/form-data):
  file: <audio_file>
  voice_name: <display_name>

Response:
{
  "status": "success",
  "voice_id": "...",
  "voice_details": {...}
}
```

### List User Voices

```
GET /v1/voices/list

Headers:
  X-User-ID: <user_id>
  X-Tenant-ID: <tenant_id>

Response:
{
  "user_id": "...",
  "voices": [...],
  "count": 1
}
```

### Get Voice Info

```
GET /v1/voices/info?voice_id=<voice_id>

Headers:
  X-User-ID: <user_id>
  X-Tenant-ID: <tenant_id>

Response:
{
  "voice_id": "...",
  "name": "...",
  "registered_at": "...",
  "characteristics": {
    "pitch": 0.85,
    "clarity": 0.92,
    "stability": 0.88
  }
}
```

### Delete a Voice

```
DELETE /v1/voices/{voice_id}

Headers:
  X-User-ID: <user_id>
  X-Tenant-ID: <tenant_id>

Response:
{
  "status": "success",
  "message": "Voice deleted"
}
```

### Compare with ElevenLabs

```
GET /v1/voices/comparison

Response:
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
    "1k_requests": {"monthly": 30, "annual": 360},
    "50k_requests": {"monthly": 1500, "annual": 18000},
    "500k_requests": {"monthly": 15000, "annual": 180000},
    "5m_requests": {"monthly": 150000, "annual": 1800000}
  }
}
```

### Check Provider Health

```
POST /v1/voices/provider/health

Response:
{
  "status": "healthy",
  "timestamp": "...",
  "voice_storage": {
    "total_voices": 3,
    "total_size_mb": 125.4
  }
}
```

---

## 🐍 Python Example (Complete)

```python
import requests
import json
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
USER_ID = "demo_user_123"
TENANT_ID = "ghostcrm"
VOICE_FILE = Path("my_voice.wav")
VOICE_NAME = "My Custom Voice"

headers = {
    "X-User-ID": USER_ID,
    "X-Tenant-ID": TENANT_ID
}

# 1. Register voice
print("📝 Registering voice...")
with open(VOICE_FILE, "rb") as f:
    files = {"file": f, "voice_name": (None, VOICE_NAME)}
    response = requests.post(
        f"{BASE_URL}/v1/voices/register",
        headers=headers,
        files=files
    )

if response.status_code == 200:
    voice_data = response.json()
    voice_id = voice_data["voice_id"]
    print(f"✅ Voice registered: {voice_id}")
else:
    print(f"❌ Registration failed: {response.text}")
    exit(1)

# 2. List voices
print("\n📋 Listing voices...")
response = requests.get(
    f"{BASE_URL}/v1/voices/list",
    headers=headers
)
voices = response.json()["voices"]
print(f"✅ Found {len(voices)} voice(s)")
for voice in voices:
    print(f"   - {voice['name']} ({voice['voice_id']})")

# 3. Get voice info
print(f"\n📊 Getting voice info...")
response = requests.get(
    f"{BASE_URL}/v1/voices/info",
    params={"voice_id": voice_id},
    headers=headers
)
info = response.json()
print(f"✅ Voice characteristics:")
for key, value in info.get("characteristics", {}).items():
    print(f"   - {key}: {value:.2f}")

# 4. Compare with ElevenLabs
print("\n💰 Cost comparison...")
response = requests.get(f"{BASE_URL}/v1/voices/comparison")
comparison = response.json()
savings_1k = comparison["savings_at_scale"]["1k_requests"]["annual"]
print(f"✅ Annual savings @ 1K requests: ${savings_1k}")

# 5. Health check
print("\n🏥 Provider health...")
response = requests.post(f"{BASE_URL}/v1/voices/provider/health", headers=headers)
health = response.json()
print(f"✅ Status: {health['status']}")
print(f"   Total voices: {health['voice_storage']['total_voices']}")

print("\n🎉 Setup complete! Your voice is ready to use.")
```

---

## 🌐 JavaScript/Node Example

```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

const BASE_URL = 'http://localhost:8000';
const USER_ID = 'demo_user_123';
const TENANT_ID = 'ghostcrm';
const VOICE_FILE = 'my_voice.wav';
const VOICE_NAME = 'My Custom Voice';

const headers = {
  'X-User-ID': USER_ID,
  'X-Tenant-ID': TENANT_ID
};

async function setupVoice() {
  try {
    // 1. Register voice
    console.log('📝 Registering voice...');
    const form = new FormData();
    form.append('file', fs.createReadStream(VOICE_FILE));
    form.append('voice_name', VOICE_NAME);

    const registerRes = await axios.post(
      `${BASE_URL}/v1/voices/register`,
      form,
      { headers: { ...headers, ...form.getHeaders() } }
    );

    const voiceId = registerRes.data.voice_id;
    console.log(`✅ Voice registered: ${voiceId}`);

    // 2. List voices
    console.log('\n📋 Listing voices...');
    const listRes = await axios.get(
      `${BASE_URL}/v1/voices/list`,
      { headers }
    );
    console.log(`✅ Found ${listRes.data.voices.length} voice(s)`);

    // 3. Use in WebSocket
    console.log('\n🔌 Connecting to streaming endpoint...');
    console.log(
      `ws://localhost:8000/v1/stream/ws/call/demo-1?tts_provider=local_tts&voice_id=${voiceId}`
    );

    return voiceId;
  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
}

setupVoice();
```

---

## 📱 React Component Example

```jsx
import React, { useState } from 'react';

export function VoiceCloning() {
  const [voiceFile, setVoiceFile] = useState(null);
  const [voiceId, setVoiceId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [voices, setVoices] = useState([]);

  const registerVoice = async (e) => {
    e.preventDefault();
    if (!voiceFile) return alert('Select an audio file');

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', voiceFile);
      formData.append('voice_name', voiceFile.name);

      const res = await fetch(
        'http://localhost:8000/v1/voices/register',
        {
          method: 'POST',
          headers: {
            'X-User-ID': 'demo_user',
            'X-Tenant-ID': 'ghostcrm'
          },
          body: formData
        }
      );

      const data = await res.json();
      setVoiceId(data.voice_id);
      alert(`✅ Voice registered: ${data.voice_id}`);
      listVoices();
    } catch (err) {
      alert(`❌ Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const listVoices = async () => {
    try {
      const res = await fetch(
        'http://localhost:8000/v1/voices/list',
        {
          headers: {
            'X-User-ID': 'demo_user',
            'X-Tenant-ID': 'ghostcrm'
          }
        }
      );
      const data = await res.json();
      setVoices(data.voices);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div>
      <h2>🎙️ Voice Cloning</h2>
      
      <form onSubmit={registerVoice}>
        <input
          type="file"
          accept="audio/*"
          onChange={(e) => setVoiceFile(e.target.files?.[0])}
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Registering...' : 'Register Voice'}
        </button>
      </form>

      {voiceId && <p>✅ Voice ID: {voiceId}</p>}

      <h3>Your Voices</h3>
      <ul>
        {voices.map(v => (
          <li key={v.voice_id}>{v.name}</li>
        ))}
      </ul>
    </div>
  );
}
```

---

## ✅ Verification Checklist

After setup, verify everything works:

- [ ] Server starts without errors
- [ ] Can register a voice
- [ ] `voice_id` is returned
- [ ] Can list voices
- [ ] Voice appears in list
- [ ] Can get voice info
- [ ] Characteristics display
- [ ] Can compare with ElevenLabs
- [ ] Cost savings show correctly
- [ ] Health check passes

---

## 🐛 Troubleshooting

### "Voice ID not returned"
- Check audio file format (WAV recommended)
- Ensure file size > 100KB
- Check server logs for errors

### "Audio file too small"
- Record at least 30 seconds
- Minimum 100KB file size
- Use clear, natural speech

### "Permission denied"
- Check X-User-ID and X-Tenant-ID headers
- Verify user exists in system

### "No space left on device"
- Clean up old voice files
- Delete test voices: DELETE /v1/voices/{id}
- Check disk space: `df -h`

---

## 🚀 Next Steps

1. **Register your voice**: Follow Step 1-3 above
2. **Test synthesis**: Connect via WebSocket with your voice_id
3. **Integrate with app**: Use voice_id in your UI/flows
4. **Monitor usage**: Check provider health regularly
5. **Optimize**: Use caching if needed

---

## 📞 Support

For issues:
1. Check server logs: `tail -f ~/.voice_api.log`
2. Test endpoint: `curl http://localhost:8000/health`
3. Verify audio file: `file my_voice.wav`
4. Check available space: `df -h`

---

## 🎯 Final Check

You're ready when you hear AI speaking in **YOUR voice**. 🎙️

That's the whole magic. Enjoy! ✨
