# Ghost Voice OS - FastAPI Service
# Run this service to start the Voice OS backend

Start with:
```bash
python -m pip install -r requirements.txt
python main.py
```

Service will be available at http://localhost:8000

## API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Endpoints

### Health & Info
- `GET /health` - Health check
- `GET /v1/info` - Service info
- `GET /v1/tenants` - List all tenants
- `GET /v1/tenants/{tenant_id}` - Get tenant info

### Voice Synthesis
- `POST /v1/voice/synthesize` - Synthesize text-to-speech
- `POST /v1/voice/synthesize-custom` - Synthesize with custom voice

### Multi-Tenant
Request headers:
- `X-Tenant-Id: ghostcrm` (or any configured tenant)

Example request:
```bash
curl -X POST http://localhost:8000/v1/voice/synthesize \
  -H "X-Tenant-Id: ghostcrm" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, this is a test", "voice_id": "sarah"}'
```

## Configuration
- Add tenants in the `tenants/` directory
- Configure providers in tenant JSON files
- Set environment variables for API keys
