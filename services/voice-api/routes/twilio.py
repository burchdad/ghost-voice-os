"""
Twilio Webhooks & TwiML Handlers
/v1/webhooks/twilio/* endpoints for handling Twilio events and generating TwiML
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, Header, HTTPException, Form
from fastapi.responses import Response
from urllib.parse import parse_qs
from core.call_session import CallSession, CallState, get_session_store
from core.conversation_engine import get_conversation_engine
from providers.twilio_client import get_twilio_client
from security.webhook_verification import get_webhook_verifier
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/webhooks/twilio", tags=["webhooks-twilio"])


# ============================================================================
# TwiML Endpoints (Called by Twilio during call)
# ============================================================================

@router.post("/answer")
async def twilio_answer(
    request: Request,
    CallSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
):
    """
    Handle incoming call answer
    Returns TwiML to play greeting and initiate conversation
    """
    try:
        logger.info(f"📞 [ANSWER] Call answered: {CallSid} from {From} to {To}")
        
        # Verify Twilio signature
        twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        body = await request.body()
        twilio_signature = request.headers.get("X-Twilio-Signature", "")
        
        request_url = str(request.url)
        post_data = await request.form()
        
        verifier = get_webhook_verifier()
        # Note: Simplified - in production, properly parse form data
        # if not verifier.verify_twilio_signature(twilio_auth_token, request_url, dict(post_data), twilio_signature):
        #     logger.warning("❌ [TWILIO] Signature verification failed")
        
        # Get or create session for this call
        session_store = get_session_store()
        session = await session_store.get(CallSid)
        
        if not session:
            # Create new session from form data
            session = CallSession(
                tenant_id="default",  # TODO: Extract from query params or custom headers
                provider="twilio",
                provider_call_id=CallSid,
                to_number=To,
                from_number=From,
            )
        
        session.advance_state(CallState.ANSWERED)
        session.add_event("call_answered", {"CallSid": CallSid})
        
        # Generate greeting
        engine = get_conversation_engine()
        response_text, audio_url = await engine.generate_response(
            session=session,
            caller_input=None
        )
        
        session.add_transcript_entry("ai", response_text)
        session.increment_turn()
        
        await session_store.store(session)
        
        # Generate TwiML response
        twiml = get_twilio_client().generate_answer_twiml(
            say_text=response_text,
            record=True,
            gather=True,
            max_digits=1,
            timeout=5
        )
        
        logger.info(f"✅ [ANSWER] TwiML generated for {CallSid}")
        
        return Response(content=twiml, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"❌ [ANSWER] Exception: {e}")
        # Return fallback TwiML
        twiml = '<Response><Say>I encountered an error. Try again later.</Say><Hangup/></Response>'
        return Response(content=twiml, media_type="application/xml")


@router.post("/gather")
async def twilio_gather(
    request: Request,
    CallSid: str = Form(...),
    Digits: str = Form(default=""),
):
    """
    Handle DTMF input from gather
    Processes digits and returns next TwiML action
    """
    try:
        logger.info(f"📞 [GATHER] DTMF received: {Digits} (call: {CallSid})")
        
        # Get session
        session_store = get_session_store()
        session = await session_store.get(CallSid)
        
        if not session:
            logger.warning(f"⚠️  [GATHER] Session not found for {CallSid}")
            twiml = '<Response><Say>Session expired. Goodbye.</Say><Hangup/></Response>'
            return Response(content=twiml, media_type="application/xml")
        
        session.add_event("dtmf_received", {"digits": Digits})
        
        # Handle DTMF
        engine = get_conversation_engine()
        response_text, audio_url = await engine.handle_dtmf_input(session, Digits)
        
        session.add_transcript_entry("caller", f"[DTMF: {Digits}]")
        session.add_transcript_entry("ai", response_text)
        session.increment_turn()
        
        # Check if we should continue or end
        if session.turn_count >= session.ai_config.get("max_turns", 10):
            # Max turns reached, end call
            closing_msg = await engine.end_call(session, "completed")
            await session_store.store(session)
            
            twiml = f'<Response><Say>{closing_msg}</Say><Hangup/></Response>'
            return Response(content=twiml, media_type="application/xml")
        
        # Generate next turn
        twiml = get_twilio_client().generate_response_twiml(
            say_text=response_text,
            next_action_url="/v1/webhooks/twilio/gather"
        )
        
        await session_store.store(session)
        
        logger.info(f"✅ [GATHER] Processed DTMF, continuing conversation")
        
        return Response(content=twiml, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"❌ [GATHER] Exception: {e}")
        twiml = '<Response><Say>An error occurred. Goodbye.</Say><Hangup/></Response>'
        return Response(content=twiml, media_type="application/xml")


@router.post("/status")
async def twilio_status(
    request: Request,
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    Timestamp: Optional[str] = Form(default=None),
):
    """
    Handle call status callbacks from Twilio
    Updates session state as call progresses
    """
    try:
        logger.info(f"📞 [STATUS] Call status: {CallStatus} ({CallSid})")
        
        # Get session
        session_store = get_session_store()
        session = await session_store.get(CallSid)
        
        if not session:
            logger.info(f"ℹ️  [STATUS] Session not found for {CallSid} - creating new")
            session = CallSession(
                tenant_id="default",
                provider="twilio",
                provider_call_id=CallSid,
                to_number="",
                from_number="",
            )
        
        # Map Twilio status to CallState
        status_map = {
            "queued": CallState.INITIATED,
            "ringing": CallState.RINGING,
            "in-progress": CallState.ANSWERED,
            "completed": CallState.ENDED,
            "busy": CallState.FAILED,
            "failed": CallState.FAILED,
            "no-answer": CallState.FAILED,
            "canceled": CallState.ENDED,
        }
        
        new_state = status_map.get(CallStatus)
        if new_state:
            session.advance_state(new_state)
            session.add_event("status_change", {"twilio_status": CallStatus})
        
        await session_store.store(session)
        
        logger.info(f"✅ [STATUS] Updated session state to {session.state.value}")
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"❌ [STATUS] Exception: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/recording")
async def twilio_recording(
    request: Request,
    CallSid: str = Form(...),
    RecordingUrl: str = Form(default=""),
):
    """
    Handle recording callback from Twilio
    Stores recording metadata in session
    """
    try:
        logger.info(f"📞 [RECORDING] Recording received for {CallSid}")
        
        session_store = get_session_store()
        session = await session_store.get(CallSid)
        
        if not session:
            logger.warning(f"⚠️  [RECORDING] Session not found for {CallSid}")
            return {"status": "ok"}  # Still return 200
        
        session.recording_url = RecordingUrl
        session.add_event("recording_available", {"url": RecordingUrl})
        
        await session_store.store(session)
        
        logger.info(f"✅ [RECORDING] Recording stored: {RecordingUrl}")
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"❌ [RECORDING] Exception: {e}")
        return {"status": "error", "message": str(e)}


# ============================================================================
# Simple IVR Endpoints (Legacy Support)
# ============================================================================

@router.post("/simple-answer")
async def twilio_simple_answer(
    request: Request,
    CallSid: str = Form(...),
):
    """
    Simple TwiML response without AI
    Used for basic IVR flows
    """
    try:
        logger.info(f"📞 [SIMPLE] Simple answer for {CallSid}")
        
        twiml = """
        <Response>
            <Say voice="alice">Hello! Thank you for calling. Please select an option.</Say>
            <Gather numDigits="1" action="/v1/webhooks/twilio/gather" method="POST">
                <Say voice="alice">Press 1 for sales, 2 for support, 3 to repeat this menu.</Say>
            </Gather>
        </Response>
        """
        
        return Response(content=twiml, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"❌ [SIMPLE] Exception: {e}")
        return Response(
            content='<Response><Say>Error occurred.</Say><Hangup/></Response>',
            media_type="application/xml"
        )


@router.get("/health")
async def twilio_webhook_health():
    """Health check for Twilio webhook endpoint"""
    return {
        "status": "ok",
        "service": "twilio-webhooks",
        "version": "1.0.0"
    }
