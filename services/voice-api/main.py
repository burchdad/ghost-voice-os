"""
Ghost Voice OS - FastAPI Backend
Main application entry point
Provides multi-tenant voice synthesis and telephony APIs
"""

import logging
import os
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any

from core.tenant_loader import load_tenant, list_available_tenants
from providers.tts.elevenlabs import get_elevenlabs_provider
from routes import calls, telnyx, twilio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Ghost Voice OS",
    description="White-label Voice OS platform",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(calls.router)
app.include_router(telnyx.router)
app.include_router(twilio.router)


# ============================================================================
# Models
# ============================================================================

class SynthesizeRequest(BaseModel):
    """Request to synthesize text to speech"""
    text: str
    voice_id: Optional[str] = "sarah"
    language: Optional[str] = "en-US"
    voice_type: Optional[str] = "primary"


class TenantInfoResponse(BaseModel):
    """Tenant information response"""
    tenant_id: str
    name: str
    branding: Dict[str, Any]
    providers: Dict[str, str]
    features: Dict[str, bool]


# ============================================================================
# Utility Functions
# ============================================================================

def get_tenant_from_header(x_tenant_id: str = Header(default="default")) -> str:
    """Extract and validate tenant ID from header"""
    return x_tenant_id


def get_provider_instance(provider_type: str, tenant_id: str):
    """Get provider instance based on configuration"""
    tenant = load_tenant(tenant_id)
    provider_name = tenant.get_provider(provider_type)

    if provider_type == "tts":
        if provider_name == "elevenlabs":
            return get_elevenlabs_provider()
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported TTS provider: {provider_name}"
            )

    raise HTTPException(status_code=400, detail=f"Unknown provider type: {provider_type}")


# ============================================================================
# Health & Info Endpoints
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Ghost Voice OS",
        "version": "1.0.0",
        "tenants": len(list_available_tenants())
    }


@app.get("/v1/info")
async def service_info():
    """Service information"""
    return {
        "name": "Ghost Voice OS",
        "version": "1.0.0",
        "description": "White-label voice synthesis and telephony platform",
        "available_tenants": list_available_tenants()
    }


@app.get("/v1/tenants")
async def list_tenants():
    """List all available tenants"""
    return {"tenants": list_available_tenants()}


@app.get("/v1/tenants/{tenant_id}")
async def get_tenant_info(tenant_id: str) -> TenantInfoResponse:
    """Get tenant configuration"""
    try:
        tenant = load_tenant(tenant_id)
        return TenantInfoResponse(
            tenant_id=tenant.tenant_id,
            name=tenant.name,
            branding=tenant.branding,
            providers=tenant.providers,
            features=tenant.features
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tenant not found: {tenant_id}")


# ============================================================================
# Voice Synthesis Endpoints
# ============================================================================

@app.post("/v1/voice/synthesize")
async def synthesize_voice(
    request: SynthesizeRequest,
    x_tenant_id: str = Header(default="default")
):
    """
    Synthesize text to speech
    Uses tenant's configured TTS provider with fallback chain
    """
    try:
        tenant = load_tenant(x_tenant_id)
        logger.info(
            f"🎯 [SYNTHESIZE] Tenant: {x_tenant_id}, Text: '{request.text[:50]}...'"
        )

        # Get configured TTS provider
        provider = get_provider_instance("tts", x_tenant_id)

        # Synthesize audio
        audio_io = await provider.synthesize(
            text=request.text,
            voice_id=request.voice_id or "sarah",
            language=request.language or "en-US"
        )

        logger.info(f"✅ [SYNTHESIZE] Success for tenant: {x_tenant_id}")

        return StreamingResponse(
            audio_io,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=audio.mp3"}
        )

    except FileNotFoundError:
        logger.error(f"❌ [SYNTHESIZE] Tenant not found: {x_tenant_id}")
        raise HTTPException(status_code=404, detail=f"Tenant not found: {x_tenant_id}")
    except Exception as e:
        logger.error(f"❌ [SYNTHESIZE] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/voice/synthesize-custom")
async def synthesize_custom_voice(
    request: SynthesizeRequest,
    x_tenant_id: str = Header(default="default")
):
    """
    Synthesize using custom tenant voice
    This endpoint would support tenant's uploaded voice samples
    """
    try:
        tenant = load_tenant(x_tenant_id)
        logger.info(f"🎯 [CUSTOM SYNTHESIZE] Tenant: {x_tenant_id}")

        # TODO: Check if tenant has custom voice uploaded
        # For now, fall back to ElevenLabs

        provider = get_provider_instance("tts", x_tenant_id)
        audio_io = await provider.synthesize(
            text=request.text,
            voice_id=request.voice_id or "sarah",
            language=request.language or "en-US"
        )

        return StreamingResponse(
            audio_io,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=audio.mp3"}
        )

    except Exception as e:
        logger.error(f"❌ [CUSTOM SYNTHESIZE] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Voice Upload Endpoints (Placeholder)
# ============================================================================

@app.post("/v1/voice/upload")
async def upload_voice(
    request: Request,
    x_tenant_id: str = Header(default="default")
):
    """
    Upload custom voice sample
    Placeholder - full implementation in next phase
    """
    return {
        "status": "ok",
        "message": "Voice upload not yet implemented",
        "tenant_id": x_tenant_id
    }




# ============================================================================
# Call Management Endpoints
# ============================================================================
# Handled by routes/calls.py router (registered above)

# ============================================================================
# Webhook Endpoints
# ============================================================================
# Handled by routes/telnyx.py and routes/twilio.py routers (registered above)


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status": "error"}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"❌ [ERROR] Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "status": "error"}
    )


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("🚀 [STARTUP] Ghost Voice OS starting...")
    tenants = list_available_tenants()
    logger.info(f"✅ [STARTUP] Loaded {len(tenants)} tenant(s): {tenants}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 [SHUTDOWN] Ghost Voice OS shutting down...")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")
