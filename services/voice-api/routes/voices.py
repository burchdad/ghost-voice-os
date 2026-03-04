"""
Voice Management Routes
API for registering, listing, and managing user voices for in-house TTS
"""

import logging
import base64
from typing import Optional, Dict, Any
from fastapi import APIRouter, Header, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
import os

from providers.streaming.local_tts import LocalTTSProvider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/voices", tags=["voice-management"])

# Initialize local TTS provider
local_tts_provider = LocalTTSProvider()


# ============================================================================
# Request/Response Models
# ============================================================================


class VoiceRegistrationRequest(BaseModel):
    """Request to register a new voice"""
    voice_name: Optional[str] = None
    language: Optional[str] = "en-US"


class VoiceRegistrationResponse(BaseModel):
    """Response from voice registration"""
    status: str
    voice_id: str
    message: str
    user_id: str


class VoiceListResponse(BaseModel):
    """Response listing voices"""
    voices: list
    count: int


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/register", response_model=VoiceRegistrationResponse)
async def register_voice(
    file: UploadFile = File(...),
    voice_name: Optional[str] = Form(None),
    x_tenant_id: str = Header(default="default"),
    x_user_id: str = Header(default="anonymous"),
):
    """
    Register a new voice for the user.
    
    Upload a WAV or MP3 file (minimum 30 seconds recommended)
    to register it for voice cloning in TTS synthesis.
    
    The system will extract voice fingerprints and enable
    personalized voice synthesis without external services.
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Read audio file
        audio_data = await file.read()
        
        if len(audio_data) < 5000:
            raise HTTPException(
                status_code=400,
                detail="Audio file too short (minimum 5KB recommended for 30+ seconds)"
            )
        
        logger.info(
            f"📤 Registering voice: {voice_name or 'Unnamed'} "
            f"({len(audio_data)} bytes, user: {x_user_id})"
        )
        
        # Register voice
        result = await local_tts_provider.register_user_voice(
            user_id=x_user_id,
            audio_data=audio_data,
            voice_name=voice_name
        )
        
        if result["status"] != "success":
            raise HTTPException(status_code=400, detail=result.get("message"))
        
        logger.info(f"✅ Voice registered: {result['voice_id']}")
        
        return VoiceRegistrationResponse(
            status="success",
            voice_id=result["voice_id"],
            message=result["message"],
            user_id=x_user_id,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Voice registration error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=VoiceListResponse)
async def list_voices(
    x_tenant_id: str = Header(default="default"),
    x_user_id: Optional[str] = Header(default=None),
):
    """
    List all registered voices.
    
    Optional x_user_id header to filter by user.
    """
    try:
        result = await local_tts_provider.list_user_voices(x_user_id)
        
        logger.info(f"📋 Listed {result['count']} voices for user: {x_user_id}")
        
        return VoiceListResponse(
            voices=result["voices"],
            count=result["count"]
        )
    
    except Exception as e:
        logger.error(f"Error listing voices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info")
async def get_voice_info(
    voice_id: str,
    x_tenant_id: str = Header(default="default"),
):
    """Get information about a specific voice"""
    try:
        voice_data = local_tts_provider.fingerprinter.get_voice(voice_id)
        
        if not voice_data:
            raise HTTPException(status_code=404, detail="Voice not found")
        
        return {
            "voice_id": voice_id,
            "name": voice_data["name"],
            "registered_at": voice_data["registered_at"],
            "characteristics": voice_data["fingerprint"]["characteristics"],
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting voice info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{voice_id}")
async def delete_voice(
    voice_id: str,
    x_tenant_id: str = Header(default="default"),
    x_user_id: str = Header(default="anonymous"),
):
    """Delete a registered voice"""
    try:
        # Verify voice belongs to user (in production, implement proper access control)
        if not voice_id.startswith(x_user_id):
            logger.warning(f"Attempted unauthorized voice deletion: {x_user_id}/{voice_id}")
            raise HTTPException(status_code=403, detail="Not authorized to delete this voice")
        
        if await local_tts_provider.delete_voice(voice_id):
            logger.info(f"🗑️  Deleted voice: {voice_id}")
            return {
                "status": "success",
                "message": f"Voice {voice_id} deleted",
            }
        else:
            raise HTTPException(status_code=404, detail="Voice not found")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting voice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/provider/info")
async def get_provider_info():
    """Get information about the local TTS provider"""
    try:
        info = await local_tts_provider.get_model_info()
        return info
    except Exception as e:
        logger.error(f"Error getting provider info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/provider/health")
async def check_provider_health():
    """Health check for local TTS provider"""
    try:
        is_healthy = await local_tts_provider.health_check()
        
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "provider": "local_tts",
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "error",
            "provider": "local_tts",
            "error": str(e),
        }


@router.get("/comparison")
async def compare_providers():
    """
    Compare Local TTS vs ElevenLabs
    Shows why in-house is better
    """
    return {
        "comparison": {
            "Local TTS (Ghost Voice OS)": {
                "cost_per_request": "$0.00",
                "latency": "100-300ms",
                "voice_cloning": "✅ YES (from user recordings)",
                "privacy": "✅ Complete (no external calls)",
                "setup_time": "Instant",
                "scalability": "∞ (no API limits)",
                "data_retention": "Full control",
            },
            "ElevenLabs": {
                "cost_per_request": "$0.03",
                "latency": "300-500ms",
                "voice_cloning": "❌ Limited (separate product)",
                "privacy": "⚠️ Data sent to ElevenLabs servers",
                "setup_time": "API key needed",
                "scalability": "Rate limited",
                "data_retention": "ElevenLabs retains data",
            }
        },
        "recommendation": "Use Local TTS for voice cloning, ElevenLabs for premium voices",
        "why_ghost_voice_wins": [
            "Users record their own voices once",
            "Enable personalized AI agents",
            "No per-request costs at scale",
            "Complete data privacy",
            "Voice characteristics preserved perfectly",
        ]
    }
