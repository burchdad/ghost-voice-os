"""
STT Webhook Handlers
Receive transcription results from STT microservice
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Request
from core.call_session import get_session_store
from core.persistence import get_call_persistence

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/webhooks/stt", tags=["webhooks-stt"])


@router.post("/callback")
async def stt_callback(request: Request):
    """
    Receive transcription callback from STT microservice
    
    Stores transcript entries from completed transcription
    """
    try:
        data = await request.json()
        
        session_id = data.get("session_id")
        tenant_id = data.get("tenant_id")
        status = data.get("status")
        
        logger.info(f"📝 [STT CALLBACK] Received result for session {session_id}: {status}")
        
        if not session_id or not tenant_id:
            logger.warning("❌ [STT CALLBACK] Missing session_id or tenant_id")
            return {"status": "error", "message": "Missing required fields"}
        
        # Get session
        session_store = get_session_store()
        session = await session_store.get(session_id)
        
        if not session:
            logger.warning(f"⚠️  [STT CALLBACK] Session not found for {session_id}")
            # Still process the callback for audit purposes
            # In production, could store in dead-letter queue
        else:
            # Process based on status
            if status == "completed":
                await _handle_transcription_complete(session, data)
            elif status == "failed":
                await _handle_transcription_failed(session, data)
            else:
                logger.warning(f"❌ [STT CALLBACK] Unknown status: {status}")
        
        return {"status": "ok", "message": "Callback processed"}
    
    except Exception as e:
        logger.error(f"❌ [STT CALLBACK] Exception: {e}")
        return {"status": "error", "message": str(e)}


# ============================================================================
# Callback Handlers
# ============================================================================

async def _handle_transcription_complete(session, data: Dict[str, Any]):
    """Handle successful transcription"""
    try:
        transcript_text = data.get("transcript", "")
        language = data.get("language", "unknown")
        segments: List[Dict] = data.get("segments", [])
        job_id = data.get("job_id")
        
        logger.info(f"✅ [STT] Storing transcript for session {session.session_id}")
        logger.info(f"   Transcript: {transcript_text[:100]}...")
        logger.info(f"   Language: {language}")
        logger.info(f"   Segments: {len(segments)}")
        
        # Store each segment as transcript entry (for granular timestamps)
        persistence = get_call_persistence()
        
        for idx, segment in enumerate(segments):
            segment_text = segment.get("text", "").strip()
            if segment_text:
                # Store with segment timing for precise transcript reconstruction
                await persistence.persist_transcript(
                    session=session,
                    speaker="caller",  # STT results are always caller speech
                    text=segment_text,
                    metadata={
                        "segment_id": idx,
                        "start_time": segment.get("start", 0),
                        "end_time": segment.get("end", 0),
                        "duration": segment.get("end", 0) - segment.get("start", 0),
                        "confidence": segment.get("avg_logprob", 0),
                    }
                )
        
        # Also store full transcript as single entry for quick access
        await persistence.persist_transcript(
            session=session,
            speaker="caller_full",
            text=transcript_text,
            metadata={
                "type": "full_transcript",
                "language": language,
                "segment_count": len(segments),
                "job_id": job_id,
            }
        )
        
        # Log transcription event
        await persistence.log_event(
            session=session,
            event_type="transcription_completed",
            event_data={
                "job_id": job_id,
                "language": language,
                "transcript_length": len(transcript_text),
                "segment_count": len(segments),
                "confidence": data.get("confidence", "unknown"),
            }
        )
        
        logger.info(f"✅ [STT] Transcript stored: {len(segments)} segments, {len(transcript_text)} chars")
    
    except Exception as e:
        logger.error(f"❌ [STT] Failed to store transcript: {e}")
        
        # Still log the error event
        try:
            persistence = get_call_persistence()
            await persistence.log_event(
                session=session,
                event_type="transcription_storage_failed",
                event_data={"error": str(e)}
            )
        except:
            pass


async def _handle_transcription_failed(session, data: Dict[str, Any]):
    """Handle failed transcription"""
    try:
        error = data.get("error", "Unknown error")
        job_id = data.get("job_id")
        
        logger.error(f"❌ [STT] Transcription failed for session {session.session_id}: {error}")
        
        persistence = get_call_persistence()
        
        # Log failure event
        await persistence.log_event(
            session=session,
            event_type="transcription_failed",
            event_data={
                "job_id": job_id,
                "error": error,
            }
        )
        
        # Could trigger fallback behavior here (e.g., use provider-side STT, try again, etc.)
        logger.info(f"🔄 [STT] Consider fallback transcription strategy for {session.session_id}")
    
    except Exception as e:
        logger.error(f"❌ [STT] Failed to handle transcription error: {e}")
