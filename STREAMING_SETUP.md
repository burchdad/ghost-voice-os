# Getting Started with Streaming Voice API

## Quick Start

### 1. Install Dependencies

```bash
cd services/voice-api
pip install -r requirements.txt
```

### 2. Set Environment Variables

```bash
export DEEPGRAM_API_KEY=your_key
export OPENAI_API_KEY=your_key
export ELEVENLABS_API_KEY=your_key
```

### 3. Run Server

```bash
python main.py
# Server runs on http://localhost:8000
```

### 4. Connect Client (Browser)

```html
<!DOCTYPE html>
<html>
<head>
    <script src="node_modules/@ghost-voice/streaming-client/dist/index.js"></script>
</head>
<body>
    <button onclick="startCall()">Start Call</button>
    <button onclick="stopCall()">Stop Call</button>
    <div id="transcript"></div>
    
    <script>
        let client;
        
        async function startCall() {
            client = new StreamingVoiceClient({
                wsUrl: 'ws://localhost:8000/v1/stream/ws/call/demo-123',
                sampleRate: 16000
            });
            
            await client.connect();
            await client.startRecording();
            
            // Real-time transcript
            client.on('transcript', (msg) => {
                document.getElementById('transcript').innerText = msg.text;
            });
            
            // Errors
            client.on('error', (error) => {
                console.error('Error:', error);
            });
        }
        
        async function stopCall() {
            await client.stop();
        }
    </script>
</body>
</html>
```

## Architecture Overview

The streaming pipeline has three parallel phases:

### Phase 1: Speech-to-Text (STT)
- **Provider:** Deepgram
- **Latency:** 100-300ms
- **Output:** Interim and final transcripts

### Phase 2: Language Model (LLM)
- **Provider:** OpenAI GPT-4
- **Latency:** 50-200ms (starts immediately after transcript)
- **Output:** Token-by-token responses

### Phase 3: Text-to-Speech (TTS)
- **Provider:** ElevenLabs
- **Latency:** 100-300ms
- **Output:** Audio chunks for playback

## Latency Profile

```
Time
│
0ms  │ [User speaks "hello"]
     │ └─ Audio stream starts
     │
100ms│    STT processing...
     │    └─ First interim transcript arrives
     │
200ms│      LLM processing...
     │      └─ First token from response
     │
300ms│        TTS processing...
     │        └─ First audio chunk ready
     │
500ms│         Audio plays back
     │         └─ User hears AI start speaking
     │
```

## Testing

### Run Unit Tests

```bash
pytest tests/test_streaming.py -v
```

### Run All Tests

```bash
pytest tests/ -v --cov=core,providers,routes
```

### Manual Testing

Open `examples/streaming-demo.html` in a browser to test the full pipeline.

## API Endpoints

### WebSocket: Stream Voice Call
```
ws://localhost:8000/v1/stream/ws/call/{session_id}
```

### REST: Get Stream Stats
```bash
curl http://localhost:8000/v1/stream/stats
```

Response:
```json
{
  "active_streams": 3,
  "total_audio_received": 516096,
  "total_audio_sent": 1048576
}
```

### REST: Configure Stream
```bash
curl -X POST http://localhost:8000/v1/stream/config \
  -H "Content-Type: application/json" \
  -d '{
    "stt_provider": "deepgram",
    "llm_provider": "openai",
    "tts_provider": "elevenlabs",
    "language": "en-US",
    "sample_rate": 16000
  }'
```

## Provider Configuration

### STT Provider (Deepgram)

```python
stt_provider = DeepgramStreamingSTT({
    "api_key": "your_api_key",
    "model": "nova-2",  # Latest model
    "language": "en-US"
})
```

### LLM Provider (OpenAI)

```python
llm_provider = OpenAIStreamingLLM({
    "api_key": "your_api_key",
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 500
})
```

### TTS Provider (ElevenLabs)

```python
tts_provider = ElevenLabsStreamingTTS({
    "api_key": "your_api_key",
    "default_voice_id": "21m00Tcm4TlvDq8ikWAM",  # Rachel
    "model": "eleven_monolingual_v1",
    "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.75
    }
})
```

## Monitoring

### Latency Metrics

```bash
# Check logs for timing information
docker logs voice-api | grep -E "STT|LLM|TTS"
```

### Streaming Statistics

```bash
# Real-time stats
watch -n 1 'curl -s http://localhost:8000/v1/stream/stats | jq'
```

## Troubleshooting

### WebSocket Connection Failed
- Check server is running: `curl http://localhost:8000/health`
- Check firewall allows WebSocket traffic
- Verify CORS headers are correct

### No Transcripts Appearing
- Check Deepgram API key is valid
- Verify microphone permissions granted
- Check for errors: `client.on('error', console.error)`

### Audio Not Playing
- Check browser audio context permissions
- Verify ElevenLabs API key is valid
- Check audio output device is working

### High Latency (>1s)
- Check network latency to providers (Deepgram, OpenAI, ElevenLabs)
- Monitor CPU usage on server
- Check LLM response is not too long (response_max_tokens)

## Deployment

### Docker

```bash
docker build -t voice-api:latest .
docker run -p 8000:8000 \
  -e DEEPGRAM_API_KEY=xxx \
  -e OPENAI_API_KEY=xxx \
  -e ELEVENLABS_API_KEY=xxx \
  voice-api:latest
```

### Kubernetes

```bash
kubectl apply -f deployment/kubernetes/voice-api.yaml
```

## Next Steps

1. ✅ Complete streaming implementation
2. 📊 Add WebRTC support for ultra-low latency
3. 🔐 Implement end-to-end encryption
4. 📈 Add advanced analytics
5. 🌍 Multi-language support
6. 🎤 Local model support (Whisper, ORCA)

## Support

For issues or questions:
- Check [STREAMING_IMPLEMENTATION.md](../STREAMING_IMPLEMENTATION.md) for architecture details
- Review [test_streaming.py](../services/voice-api/tests/test_streaming.py) for examples
- Check logs: `docker logs voice-api -f`
