# Ghost Voice OS

> Production-grade conversational AI platform with multi-tenant support, Apple STT integration, and modular provider architecture.

**Equivalent to:** Retell.ai • Bland.ai • Vapi.ai • Twilio Conversational Stack

## 🎯 Features

- ✅ **Multi-Tenant Architecture** - Config-driven tenant isolation
- ✅ **Apple STT Integration** - macOS native speech recognition via dedicated microservice
- ✅ **Modular Provider System** - Swap STT/TTS/LLM providers at runtime
- ✅ **FastAPI Core** - Production-grade async Python framework
- ✅ **Docker Swarm Ready** - Multi-node Linux + macOS cluster support
- ✅ **Kubernetes Support** - Future-ready manifests included
- ✅ **TypeScript SDK** - Official client library for JavaScript/TypeScript
- ✅ **Voice Platform Modularity** - Phone providers (Twilio, Telnyx) abstracted

## 📦 What's Included

```
ghost-voice-os/
├── services/
│   ├── voice-api/              # FastAPI orchestration service
│   ├── voice-stt-apple/        # macOS native STT microservice (Swift)
│   └── voice-worker/           # Background job processor
├── packages/
│   ├── voice-core/             # Platform-agnostic logic
│   └── voice-client-sdk/       # TypeScript SDK
├── deployment/
│   ├── docker-compose.yml      # Development setup
│   ├── swarm/stack.yml         # Multi-node production
│   └── kubernetes/             # Future K8s support
└── tenants/                    # Multi-tenant configurations
```

## 🚀 Quick Start

### Development (Local)

```bash
# 1. Clone and setup
git clone https://github.com/ghost-voice-os/ghost-voice-os
cd ghost-voice-os

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Start with Docker Compose
bash scripts/dev.sh

# Services will be available at:
# - voice-api:        http://localhost:8000
# - OpenSearch UI:    http://localhost:5601
```

### Production (Docker Swarm)

```bash
# 1. Initialize Docker Swarm on manager node
docker swarm init

# 2. Add worker nodes
docker swarm join --token ...

# 3. Label nodes for workload distribution
docker node update --label-add type=mac mac-mini-1
docker node update --label-add storage=true storage-node-1

# 4. Deploy stack
bash scripts/start.sh
```

### Kubernetes (Future)

```bash
kubectl apply -f deployment/kubernetes/voice-api.yaml
kubectl apply -f deployment/kubernetes/redis.yaml
kubectl apply -f deployment/kubernetes/opensearch.yaml
```

## 🏗️ Architecture

### Service Topology

```
GhostCRM / Other Clients
    ↓ (via SDK)
voice-api (FastAPI, 3+ replicas)
    ├── redis (session cache)
    ├── postgres (call logs, voices)
    ├── opensearch (analytics)
    └── external providers:
        ├── apple-stt (Mac only)
        ├── elevenlabs (TTS)
        ├── openai (LLM)
        └── twilio/telnyx (telephony)
```

### Provider Architecture

All providers implement abstract base classes:

- **STT Providers** - Apple STT, Whisper, Deepgram
- **TTS Providers** - ElevenLabs, Azure, Google Cloud, Local
- **LLM Providers** - OpenAI, Llama.cpp, MLX
- **Telephony Providers** - Twilio, Telnyx

Add new providers by extending base classes:

```python
from providers.stt.base import STTProvider

class MySTTProvider(STTProvider):
    async def transcribe(self, audio_data, language, **kwargs):
        # Your implementation
        pass
```

## 🔧 Configuration

### Tenant Configuration

Each tenant has a JSON config file in `tenants/`:

```json
{
  "id": "ghostcrm",
  "name": "GhostCRM",
  "providers": {
    "stt": {
      "primary": "apple_stt",
      "fallback": ["whisper"]
    },
    "tts": {
      "primary": "elevenlabs",
      "fallback": ["azure_tts"]
    },
    "llm": {
      "primary": "openai",
      "model": "gpt-4"
    },
    "telephony": {
      "primary": "twilio"
    }
  },
  "quotas": {
    "synthesis_requests_per_day": 10000,
    "transcription_requests_per_day": 10000,
    "api_calls_per_minute": 100
  },
  "features": {
    "voice_upload": true,
    "voice_synthesis": true,
    "call_recording": true,
    "analytics": true
  }
}
```

## 📡 API Endpoints

### Health & Status

```bash
# Health check
curl http://localhost:8000/health

# Service info
curl http://localhost:8000/v1/info

# List tenants
curl http://localhost:8000/v1/tenants \
  -H "X-API-Key: your-api-key"
```

### Voice Operations

```bash
# Synthesize speech
curl -X POST http://localhost:8000/v1/voice/synthesize \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: ghostcrm" \
  -d '{
    "text": "Hello world",
    "voice_id": "sarah",
    "provider": "elevenlabs"
  }'

# Transcribe audio
curl -X POST http://localhost:8000/v1/voice/transcribe \
  -F "audio=@recording.wav" \
  -H "X-Tenant-Id: ghostcrm"
```

### Telephony

```bash
# Initiate call
curl -X POST http://localhost:8000/v1/calls/initiate \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: ghostcrm" \
  -d '{
    "to_number": "+1-555-0123",
    "from_number": "+1-555-0456",
    "voice_prompt": "Hello, this is Ghost Voice OS"
  }'
```

## 🔌 TypeScript SDK Usage

```typescript
import { VoiceOSClient } from '@ghost-voice-os/voice-client-sdk';

const client = new VoiceOSClient({
  baseUrl: 'http://localhost:8000',
  tenantId: 'ghostcrm',
  apiKey: 'your-api-key'
});

// Synthesize
const audio = await client.synthesize({
  text: 'Hello world',
  voiceId: 'sarah',
  language: 'en-US'
});

// Transcribe
const transcript = await client.transcribe({
  audioFile: audioBlob,
  language: 'en-US'
});

// Initiate call
const call = await client.initiateCall({
  toNumber: '+1-555-0123',
  fromNumber: '+1-555-0456',
  voicePrompt: 'Hello'
});
```

## 📊 Monitoring & Observability

### Metrics

OpenSearch dashboard available at `http://localhost:5601`

Metrics collected:
- Synthesis requests/latency
- Transcription accuracy
- Call duration/success rate
- Provider health
- API response times
- Error rates

### Logging

All services log to stdout (Docker/K8s friendly):

```bash
# View API logs
docker-compose logs -f voice-api

# View all services
docker-compose logs -f
```

## 🛠️ Development

### Running Tests

```bash
pytest tests/ -v
pytest tests/ --cov=services
```

### Code Quality

```bash
# Format code
black services/

# Sort imports
isort services/

# Lint
flake8 services/

# Type check
mypy services/
```

### Building Custom Images

```bash
# Build API
docker build -t ghost-voice-os:latest ./services/voice-api

# Build Apple STT (requires macOS)
cd services/voice-stt-apple
swift build -c release
```

## 🔐 Security

- API key authentication on all endpoints
- Tenant isolation enforced at database level
- TLS support for all external communications
- Audio data encryption at rest (configurable)
- Rate limiting per tenant (configurable)

## 📚 Documentation

- [API Reference](./docs/api.md)
- [Provider Guide](./docs/providers.md)
- [Deployment Guide](./docs/deployment.md)
- [Architecture](./docs/architecture.md)

## 🤝 Contributing

```bash
# Setup development environment
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Create feature branch
git checkout -b feature/my-feature

# Commit and push
git commit -am "Add my feature"
git push origin feature/my-feature
```

## 📄 License

MIT License - see LICENSE file

## 🎯 Roadmap

- ✅ Multi-tenant architecture
- ✅ Docker Swarm deployment
- 🔄 Kubernetes support (in progress)
- 🔄 Google Cloud AI provider
- 🔄 Banking-grade compliance (SOC2, HIPAA)
- 📅 Real-time call transcription
- 📅 Agent builder UI
- 📅 Analytics dashboard

## 💬 Support

- 📧 Email: support@ghost-voice-os.com
- 💬 Discord: https://discord.gg/ghost-voice-os
- 📋 Issues: https://github.com/ghost-voice-os/ghost-voice-os/issues

---

**Built for production.** 🚀

Production-ready out of the box. Scale from 1 call/day to 1M calls/day with configuration changes only.
