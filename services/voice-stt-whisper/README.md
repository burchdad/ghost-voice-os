# Voice STT - Whisper Microservice

Speech-to-Text execution layer using OpenAI Whisper for Ghost Voice OS.

## Overview

This microservice handles all audio transcription for Ghost Voice OS. It:

- ✅ Processes audio uploads (WAV, MP3, M4A, FLAC, etc.)
- ✅ Downloads and transcribes audio from URLs
- ✅ Auto-detects language (supports 10+ languages)
- ✅ Runs asynchronously (non-blocking)
- ✅ Sends webhook callbacks with results
- ✅ Multi-tenant support (tenant isolation)

## Architecture

```
voice-api
    ↓ (POST /v1/transcribe: audio_url + callback_url)
stt-service (Whisper)
    ↓ (async background processing)
transcription
    ↓ (POST callback_url with transcript)
voice-api (receives result)
    ↓ (stores in OpenSearch)
transcript_store
```

## API Endpoints

### Health Check

```bash
GET /health
```

Returns service status and model info.

### Get Info

```bash
GET /v1/info
```

Returns service capabilities and supported languages.

### Transcribe Audio

```bash
POST /v1/transcribe
Content-Type: multipart/form-data

Parameters:
file: <binary audio file>  (optional)
audio_url: <string>         (optional, one of file/url required)
session_id: <string>        (required, call session ID)
tenant_id: <string>         (required, tenant ID)
callback_url: <string>      (required, webhook URL for results)
language: <string>          (optional, ISO-639-1 code)
```

Returns:

```json
{
  "status": "processing",
  "job_id": "session123_1234567890.123",
  "session_id": "session123",
  "message": "Transcription queued for processing"
}
```

### Webhook Callback Format

When transcription completes, STT service POSTs to `callback_url` with:

```json
{
  "job_id": "session123_1234567890.123",
  "session_id": "session123",
  "tenant_id": "ghostcrm",
  "status": "completed",
  "timestamp": "2026-02-25T20:30:45.123456",
  "transcript": "Hello, I was interested in your financing options",
  "language": "en",
  "segments": [
    {
      "id": 0,
      "seek": 0,
      "start": 0.0,
      "end": 2.5,
      "text": "Hello, I was interested in your financing options",
      "tokens": [15842, ...],
      "temperature": 0.0,
      "avg_logprob": -0.25,
      "compression_ratio": 1.35,
      "no_speech_prob": 0.001
    }
  ],
  "confidence": "high"
}
```

On error:

```json
{
  "job_id": "session123_1234567890.123",
  "session_id": "session123",
  "tenant_id": "ghostcrm",
  "status": "failed",
  "timestamp": "2026-02-25T20:30:45.123456",
  "error": "Failed to download audio from URL"
}
```

## Configuration

Environment variables:

```bash
WHISPER_MODEL_SIZE=base      # Options: tiny, base, small, medium, large
```

Model sizes:

| Size   | Parameters | VRAM | Speed | Accuracy |
|--------|-----------|------|-------|----------|
| tiny   | 39M       | 1GB  | Fast  | 60%      |
| base   | 74M       | 1GB  | Good  | 80%      |
| small  | 244M      | 2GB  | OK    | 85%      |
| medium | 769M      | 5GB  | Slow  | 90%      |
| large  | 1.5B      | 10GB | Very  | 96%      |

## Examples

### Transcribe from File Upload

```bash
curl -X POST http://localhost:8001/v1/transcribe \
  -F "file=@audio.wav" \
  -F "session_id=call_abc123" \
  -F "tenant_id=ghostcrm" \
  -F "callback_url=http://localhost:8000/v1/webhooks/stt/callback" \
  -F "language=en"
```

### Transcribe from URL

```bash
curl -X POST http://localhost:8001/v1/transcribe \
  -F "audio_url=https://example.com/audio.mp3" \
  -F "session_id=call_abc123" \
  -F "tenant_id=ghostcrm" \
  -F "callback_url=http://localhost:8000/v1/webhooks/stt/callback"
```

### Check Service Status

```bash
curl http://localhost:8001/health | jq .
```

## Running

### Docker

```bash
# Run with Docker Compose (recommended)
docker compose up voice-stt-whisper

# Or standalone
docker build -t voice-stt-whisper services/voice-stt-whisper/
docker run -d -p 8001:8001 \
  -e WHISPER_MODEL_SIZE=base \
  voice-stt-whisper
```

### Local Development

```bash
# Install deps
pip install -r requirements.txt

# Run
python main.py

# Access at http://localhost:8001
```

## Performance Notes

- **Cold start**: Model loads on first request (~20s for base model)
- **Transcription time**: ~20% of audio length (for base model on CPU)
- **Max file size**: Limited by available disk space in /tmp/
- **Max concurrent**: Depends on available VRAM; recommend 1-2 concurrent on CPU

For production:

- Use GPU instance (NVIDIA Tesla or better)
- Implement job queue (Celery, RQ, etc.)
- Add distributed model caching
- Monitor memory usage during peak loads

## Integration with Voice OS

See voice-api `providers/stt/whisper_client.py` for integration example.

The workflow:

1. Telnyx/Twilio webhook triggers in voice-api
2. Audio URL arrives or audio is uploaded
3. voice-api calls STT service with `/v1/transcribe`
4. STT service queues background task
5. Task completes, sends callback to voice-api
6. voice-api stores transcript in OpenSearch
7. Transcript available in call analytics

## Troubleshooting

### Model download fails

```
Error: Failed to download whisper model
```

Solution: Manually download model:

```bash
python -m whisper --model base --download_root ./models
```

### Out of memory

Reduce `WHISPER_MODEL_SIZE` to `tiny` or `base`.

### Transcription incorrect

- Check audio quality
- Try explicit language: `language=en`
- Use larger model size if possible

## License

Part of Ghost Voice OS.
