"""
Telnyx Webhooks & Event Handlers
/v1/webhooks/telnyx/* endpoint for handling Telnyx events
"""

import logging
import base64
import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, Header, HTTPException
from core.call_session import CallSession, CallState, get_session_store
from core.conversation_engine import get_conversation_engine
from providers.telnyx_client import get_telnyx_client
from security.webhook_verification import get_webhook_verifier
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/webhooks/telnyx", tags=["webhooks-telnyx"])


# ============================================================================
# Webhook Event Handlers
# ============================================================================

@router.post("/")
async def telnyx_webhook(request: Request):
    """
    Main Telnyx webhook endpoint
    Routes to specific handlers based on event type
    """
    try:
        # Get request body
        body = await request.body()
        body_str = body.decode('utf-8')
        
        # Verify webhook signature
        telnyx_signature = request.headers.get("Telnyx-Signature", "")
        if not telnyx_signature:
            logger.warning("❌ [TELNYX] Missing Telnyx-Signature header")
            # In production, reject unsigned webhooks
            # For now, continue for testing
        else:
            verifier = get_webhook_verifier()
            api_key = os.getenv("TELNYX_API_KEY", "")
            if not verifier.verify_telnyx_signature(api_key, body_str, telnyx_signature):
                logger.warning("❌ [TELNYX] Signature verification failed")
                # In production, return 403
                # For now, continue
        
        # Parse webhook data
        data = json.loads(body_str)
        event_data = data.get("data", {})
        event_type = event_data.get("event_type", "unknown")
        call_control_id = event_data.get("call_control_id", "")
        
        logger.info(f"📞 [TELNYX] Webhook event: {event_type} (call: {call_control_id})")
        
        # Get session
        session_store = get_session_store()
        session = await session_store.get(call_control_id)
        
        if not session:
            logger.warning(f"⚠️  [TELNYX] Session not found for {call_control_id}")
            # Try to extract session info from event
            client_state_b64 = event_data.get("client_state", "")
            if client_state_b64:
                try:
                    session = _parse_client_state(client_state_b64, call_control_id)
                    session.provider_call_id = call_control_id
                    await session_store.store(session)
                except Exception as e:
                    logger.error(f"❌ [TELNYX] Failed to parse client_state: {e}")
                    return {"status": "error", "message": "Session not found"}
        
        # Route to handler based on event type
        handlers = {
            "call.initiated": handle_call_initiated,
            "call.answered": handle_call_answered,
            "call.machine_detection_ended": handle_machine_detection,
            "call.speaking_started": handle_speaking_started,
            "call.dtmf_received": handle_dtmf_received,
            "call.hangup": handle_call_hangup,
            "call.failed": handle_call_failed,
        }
        
        handler = handlers.get(event_type)
        if handler:
            await handler(session, event_data)
        else:
            logger.info(f"ℹ️  [TELNYX] Unhandled event type: {event_type}")
        
        return {"status": "ok"}
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ [TELNYX] JSON parse error: {e}")
        return {"status": "error", "message": "Invalid JSON"}
    except Exception as e:
        logger.error(f"❌ [TELNYX] Webhook error: {e}")
        return {"status": "error", "message": str(e)}


# ============================================================================
# Event Handlers
# ============================================================================

async def handle_call_initiated(session: CallSession, event_data: Dict[str, Any]):
    """Handle call.initiated event"""
    try:
        logger.info(f"📞 [EVENT] Call initiated: {session.provider_call_id}")
        session.advance_state(CallState.INITIATED)
        session.add_event("call_initiated", event_data)
        
        session_store = get_session_store()
        await session_store.store(session)
        
    except Exception as e:
        logger.error(f"❌ [EVENT] Error in initiated handler: {e}")


async def handle_call_answered(session: CallSession, event_data: Dict[str, Any]):
    """Handle call.answered event"""
    try:
        logger.info(f"📞 [EVENT] Call answered: {session.provider_call_id}")
        session.advance_state(CallState.ANSWERED)
        session.add_event("call_answered", event_data)
        
        # Generate initial greeting
        engine = get_conversation_engine()
        response_text, audio_url = await engine.generate_response(
            session=session,
            caller_input=None
        )
        
        session.add_transcript_entry("ai", response_text)
        
        # Send audio to call
        client = get_telnyx_client()
        await client.send_audio(
            call_control_id=session.provider_call_id,
            audio_url=audio_url or "https://example.com/audio.mp3"
        )
        
        session.advance_state(CallState.SPEAKING)
        
        session_store = get_session_store()
        await session_store.store(session)
        
    except Exception as e:
        logger.error(f"❌ [EVENT] Error in answered handler: {e}")


async def handle_machine_detection(session: CallSession, event_data: Dict[str, Any]):
    """Handle call.machine_detection_ended event"""
    try:
        detection_result = event_data.get("machine_detection_result", "")
        logger.info(f"📞 [EVENT] Machine detection: {detection_result}")
        
        session.add_event("machine_detection", {
            "result": detection_result,
            "raw": event_data
        })
        
        if detection_result == "answered_human":
            # Proceed with human greeting
            await handle_call_answered(session, event_data)
        elif detection_result == "answered_machine":
            # Play voicemail message
            logger.info("📞 [EVENT] Answering machine detected, playing voicemail")
            # TODO: Handle voicemail scenario
        else:
            # No answer or timeout
            logger.info("📞 [EVENT] No answer or timeout")
            session.advance_state(CallState.ENDED)
        
        session_store = get_session_store()
        await session_store.store(session)
        
    except Exception as e:
        logger.error(f"❌ [EVENT] Error in machine detection handler: {e}")


async def handle_speaking_started(session: CallSession, event_data: Dict[str, Any]):
    """Handle call.speaking_started event (caller speaking)"""
    try:
        logger.info(f"🎤 [EVENT] Speaking started: {session.provider_call_id}")
        session.advance_state(CallState.GATHERING)
        session.add_event("speaking_started", event_data)
        
        # Start recording/transcribing caller speech
        # TODO: Integrate with STT provider
        
        session_store = get_session_store()
        await session_store.store(session)
        
    except Exception as e:
        logger.error(f"❌ [EVENT] Error in speaking handler: {e}")


async def handle_dtmf_received(session: CallSession, event_data: Dict[str, Any]):
    """Handle call.dtmf_received event"""
    try:
        digits = event_data.get("digits", "")
        logger.info(f"📞 [EVENT] DTMF received: {digits}")
        
        session.add_event("dtmf_received", {"digits": digits})
        
        # Handle DTMF input
        engine = get_conversation_engine()
        response_text, audio_url = await engine.handle_dtmf_input(session, digits)
        
        session.add_transcript_entry("caller", f"[DTMF: {digits}]")
        session.add_transcript_entry("ai", response_text)
        
        # Send response
        client = get_telnyx_client()
        await client.send_audio(
            call_control_id=session.provider_call_id,
            audio_url=audio_url or "https://example.com/audio.mp3"
        )
        
        session.increment_turn()
        session_store = get_session_store()
        await session_store.store(session)
        
    except Exception as e:
        logger.error(f"❌ [EVENT] Error in DTMF handler: {e}")


async def handle_call_hangup(session: CallSession, event_data: Dict[str, Any]):
    """Handle call.hangup event"""
    try:
        reason = event_data.get("reason", "unknown")
        logger.info(f"👋 [EVENT] Call hung up: {session.provider_call_id} ({reason})")
        
        session.advance_state(CallState.ENDED)
        session.ended_at = event_data.get("occurred_at")
        session.add_event("call_hangup", {"reason": reason})
        
        # Get recording URL if available
        recordings = event_data.get("recordings", [])
        if recordings:
            session.recording_url = recordings[0].get("url")
        
        session_store = get_session_store()
        await session_store.store(session)
        
    except Exception as e:
        logger.error(f"❌ [EVENT] Error in hangup handler: {e}")


async def handle_call_failed(session: CallSession, event_data: Dict[str, Any]):
    """Handle call.failed event"""
    try:
        error_message = event_data.get("error", {}).get("message", "Unknown error")
        logger.error(f"❌ [EVENT] Call failed: {session.provider_call_id} - {error_message}")
        
        session.advance_state(CallState.FAILED)
        session.ended_at = event_data.get("occurred_at")
        session.add_event("call_failed", {"error": error_message})
        
        session_store = get_session_store()
        await session_store.store(session)
        
    except Exception as e:
        logger.error(f"❌ [EVENT] Error in failed handler: {e}")


# ============================================================================
# Helper Functions
# ============================================================================

def _parse_client_state(client_state_b64: str, call_control_id: str) -> CallSession:
    """Reconstruct session from base64-encoded client_state"""
    decoded = base64.b64decode(client_state_b64.encode()).decode()
    state_data = json.loads(decoded)
    
    session = CallSession(
        tenant_id=state_data.get("tenant_id", "default"),
        provider="telnyx",
        provider_call_id=call_control_id,
        to_number=state_data.get("to_number", ""),
        from_number=state_data.get("from_number", ""),
        voice_config=state_data.get("voice_config"),
        ai_config=state_data.get("ai_config"),
        lead_data=state_data.get("lead_data"),
        callback_urls=state_data.get("callback_urls")
    )
    
    return session
