"""
Calls Routes
/v1/calls/* endpoints for unified call management
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Header, HTTPException, Body
from pydantic import BaseModel
import os

from core.call_session import CallSession, CallState, get_session_store
from providers.telnyx_client import get_telnyx_client
from providers.twilio_client import get_twilio_client
from core.tenant_loader import load_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/calls", tags=["calls"])


# ============================================================================
# Request Models
# ============================================================================

class InitiateCallRequest(BaseModel):
    """Request to initiate an AI call"""
    to_number: str
    from_number: str
    provider: str  # "telnyx" or "twilio"
    script: Optional[str] = None
    voice_config: Optional[Dict[str, Any]] = None
    lead_data: Optional[Dict[str, Any]] = None
    connection_id: Optional[str] = None  # Telnyx connection ID
    status_callback_url: Optional[str] = None


class InitiateCallResponse(BaseModel):
    """Response from call initiation"""
    call_id: str
    session_id: str
    status: str
    provider: str
    to_number: str
    from_number: str


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/initiate", response_model=InitiateCallResponse)
async def initiate_call(
    request: InitiateCallRequest,
    x_tenant_id: str = Header(default="default")
):
    """
    Initiate outbound AI call via Telnyx or Twilio
    
    Unified endpoint that handles both providers.
    Creates a CallSession and routes to appropriate provider.
    """
    try:
        # Validate tenant
        tenant = load_tenant(x_tenant_id)
        logger.info(f"📞 [INITIATE] Call from {request.from_number} to {request.to_number} (tenant: {x_tenant_id})")
        
        # Validate provider
        provider = request.provider.lower()
        if provider not in ["telnyx", "twilio"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid provider. Must be 'telnyx' or 'twilio'"
            )
        
        # Create call session
        session = CallSession(
            tenant_id=x_tenant_id,
            provider=provider,
            provider_call_id="pending",  # Will be set after provider call
            to_number=request.to_number,
            from_number=request.from_number,
            voice_config=request.voice_config,
            ai_config={
                "prompt": request.script or "Hello, this is an AI assistant.",
                "personality_mode": "professional",
                "max_turns": 10
            },
            lead_data=request.lead_data or {},
            callback_urls={
                "status_callback": request.status_callback_url or ""
            }
        )
        
        # Get callback URL for provider
        base_url = os.getenv("VOICE_OS_BASE_URL", "http://localhost:8000")
        webhook_url = f"{base_url}/v1/webhooks/{provider}/{session.session_id}"
        
        # Route to appropriate provider
        if provider == "telnyx":
            result = await initiate_telnyx_call(
                session=session,
                webhook_url=webhook_url,
                connection_id=request.connection_id,
                tenant=tenant
            )
        else:  # twilio
            result = await initiate_twilio_call(
                session=session,
                webhook_url=webhook_url,
                tenant=tenant
            )
        
        if result.get("status") == "failed":
            raise HTTPException(
                status_code=500,
                detail=f"Call initiation failed: {result.get('error', 'Unknown error')}"
            )
        
        # Update session with actual call ID from provider
        session.provider_call_id = result.get("call_id", "")
        session.advance_state(CallState.INITIATED)
        
        # Store session in Redis
        session_store = get_session_store()
        await session_store.store(session)
        
        logger.info(f"✅ [INITIATE] Call session created: {session.session_id}")
        
        return InitiateCallResponse(
            call_id=session.provider_call_id,
            session_id=session.session_id,
            status="initiated",
            provider=provider,
            to_number=request.to_number,
            from_number=request.from_number
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [INITIATE] Exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def initiate_telnyx_call(
    session: CallSession,
    webhook_url: str,
    connection_id: Optional[str],
    tenant: Any
) -> Dict[str, Any]:
    """Route call to Telnyx"""
    
    if not connection_id:
        raise HTTPException(
            status_code=400,
            detail="connection_id required for Telnyx calls"
        )
    
    try:
        client = get_telnyx_client()
        
        # Prepare client_state for webhook callback
        client_state = {
            "tenant_id": session.tenant_id,
            "session_id": session.session_id,
            "voice_config": session.voice_config,
            "ai_config": session.ai_config,
            "lead_data": session.lead_data
        }
        
        result = await client.initiate_call(
            to_number=session.to_number,
            from_number=session.from_number,
            connection_id=connection_id,
            client_state=client_state,
            webhook_url=webhook_url,
            voice_prompt=session.ai_config.get("prompt", "Hello")
        )
        
        return result
        
    except Exception as e:
        logger.error(f"❌ [TELNYX_INIT] {e}")
        return {"status": "failed", "error": str(e)}


async def initiate_twilio_call(
    session: CallSession,
    webhook_url: str,
    tenant: Any
) -> Dict[str, Any]:
    """Route call to Twilio"""
    
    try:
        client = get_twilio_client()
        
        result = await client.initiate_call(
            to_number=session.to_number,
            from_number=session.from_number,
            twiml_url=webhook_url,
            session_id=session.session_id,
            status_callback=session.callback_urls.get("status_callback")
        )
        
        return result
        
    except Exception as e:
        logger.error(f"❌ [TWILIO_INIT] {e}")
        return {"status": "failed", "error": str(e)}


@router.get("/status/{session_id}")
async def get_call_status(
    session_id: str,
    x_tenant_id: str = Header(default="default")
):
    """Get current status of a call session"""
    try:
        session_store = get_session_store()
        
        # For now, we need provider_call_id to look up session
        # In Phase 2, we'll query by session_id from OpenSearch
        raise HTTPException(
            status_code=501,
            detail="Use /v1/calls/status/{provider_call_id} endpoint"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [STATUS] Exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/end/{provider_call_id}")
async def end_call(
    provider_call_id: str,
    x_tenant_id: str = Header(default="default")
):
    """Manually end a call"""
    try:
        session_store = get_session_store()
        session = await session_store.get(provider_call_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Call session not found")
        
        if session.tenant_id != x_tenant_id:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        # Route hangup to appropriate provider
        if session.provider == "telnyx":
            client = get_telnyx_client()
            await client.hangup(session.provider_call_id)
        else:  # twilio
            # Twilio doesn't have a direct API to hang up initiated calls
            # The call must be ended via TwiML response
            logger.info(f"⚠️  [END] Twilio calls must be ended via TwiML")
        
        session.advance_state(CallState.ENDED)
        await session_store.store(session)
        
        logger.info(f"✅ [END] Call ended: {provider_call_id}")
        
        return {
            "status": "ended",
            "provider_call_id": provider_call_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [END] Exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))
