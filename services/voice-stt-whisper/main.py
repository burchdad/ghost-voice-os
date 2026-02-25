"""
Voice STT Whisper Microservice
Speech-to-Text execution layer using OpenAI Whisper (via faster-whisper)
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
import httpx
from datetime import datetime
from faster_whisper import WhisperModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Ghost Voice OS - STT Service",
    description="Speech-to-Text execution layer using Whisper",
    version="1.0.0"
)

# Global Whisper model (loaded once for performance)
_whisper_model = None

def get_whisper_model():
    """Load or return cached Whisper model"""
    global _whisper_model
    if _whisper_model is None:
        logger.info("🎤 [MODEL] Loading Whisper model (this may take a minute)...")
        model_size = os.getenv("WHISPER_MODEL_SIZE", "base")
        _whisper_model = WhisperModel(model_size, device="cpu", compute_type="default")
        logger.info(f"✅ [MODEL] Whisper {model_size} model loaded")
    return _whisper_model


# ============================================================================
# Startup & Shutdown
# ============================================================================

@app.on_event("startup")
async def startup():
    """Initialize on startup"""
    logger.info("🚀 [STARTUP] Ghost Voice OS STT Service starting...")
    try:
        # Pre-load model on startup
        get_whisper_model()
        logger.info("✅ [STARTUP] STT service ready")
    except Exception as e:
        logger.error(f"❌ [STARTUP] Failed to initialize: {e}")


# ============================================================================
# Health & Info Endpoints
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Ghost Voice OS - STT",
        "version": "1.0.0",
        "model": os.getenv("WHISPER_MODEL_SIZE", "base")
    }


@app.get("/v1/info")
async def service_info():
    """Service information endpoint"""
    return {
        "name": "Ghost Voice OS - STT Microservice",
        "version": "1.0.0",
        "description": "Speech-to-Text using OpenAI Whisper (faster-whisper)",
        "capabilities": [
            "audio_file_upload",
            "audio_url_download",
            "multi_language_transcription",
            "async_processing",
            "webhook_callback"
        ],
        "model": os.getenv("WHISPER_MODEL_SIZE", "base"),
        "languages_supported": [
            "en", "es", "fr", "de", "it", "pt", "nl", "ru", "zh", "ja"
        ]
    }


# ============================================================================
# STT Endpoints
# ============================================================================

@app.post("/v1/transcribe")
async def transcribe_audio(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    audio_url: Optional[str] = Form(None),
    session_id: str = Form(...),
    tenant_id: str = Form(...),
    callback_url: str = Form(...),
    language: Optional[str] = Form(None),
):
    """
    Transcribe audio file or URL
    
    Args:
        file: Audio file upload (wav, mp3, m4a, flac, etc.)
        audio_url: Direct URL to audio file
        session_id: Call session ID for tracking
        tenant_id: Tenant identifier for multi-tenancy
        callback_url: Webhook URL to send results to
        language: ISO-639-1 language code (optional, auto-detect if None)
    
    Returns:
        Job ID for tracking async processing
    """
    try:
        if not file and not audio_url:
            raise HTTPException(status_code=400, detail="Either file or audio_url required")
        
        if file and audio_url:
            raise HTTPException(status_code=400, detail="Provide either file or audio_url, not both")
        
        job_id = f"{session_id}_{datetime.utcnow().timestamp()}"
        logger.info(f"📝 [TRANSCRIBE] Job {job_id} started for session {session_id}")
        
        # Process async in background
        if file:
            background_tasks.add_task(
                _transcribe_file,
                file=file,
                session_id=session_id,
                tenant_id=tenant_id,
                callback_url=callback_url,
                language=language,
                job_id=job_id
            )
        else:
            background_tasks.add_task(
                _transcribe_url,
                audio_url=audio_url,
                session_id=session_id,
                tenant_id=tenant_id,
                callback_url=callback_url,
                language=language,
                job_id=job_id
            )
        
        return {
            "status": "processing",
            "job_id": job_id,
            "session_id": session_id,
            "message": "Transcription queued for processing"
        }
    
    except Exception as e:
        logger.error(f"❌ [TRANSCRIBE] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Background Tasks
# ============================================================================

async def _transcribe_file(
    file: UploadFile,
    session_id: str,
    tenant_id: str,
    callback_url: str,
    language: Optional[str],
    job_id: str
):
    """Background task: transcribe uploaded file"""
    try:
        # Save temp file
        content = await file.read()
        temp_path = f"/tmp/audio_{job_id}.wav"
        
        with open(temp_path, "wb") as f:
            f.write(content)
        
        logger.info(f"🎤 [TRANSCRIBE] Processing file for job {job_id}")
        
        # Transcribe using faster-whisper
        model = get_whisper_model()
        segments, info = model.transcribe(
            temp_path,
            language=language,
            beam_size=5
        )
        
        # Convert segments to list and build transcript
        segments_list = []
        transcript_parts = []
        
        for segment in segments:
            seg_info = {
                "id": segment.id,
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "confidence": segment.confidence if hasattr(segment, 'confidence') else 0.9
            }
            segments_list.append(seg_info)
            transcript_parts.append(segment.text)
        
        transcript_text = " ".join(transcript_parts)
        detected_language = info.language if info else "unknown"
        
        logger.info(f"✅ [TRANSCRIBE] Completed job {job_id}: {len(transcript_text)} chars")
        
        # Send callback
        await _send_callback(
            callback_url=callback_url,
            session_id=session_id,
            tenant_id=tenant_id,
            job_id=job_id,
            transcript=transcript_text,
            language=detected_language,
            segments=segments_list,
            status="completed"
        )
        
        # Cleanup temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    except Exception as e:
        logger.error(f"❌ [TRANSCRIBE] Failed job {job_id}: {e}")
        await _send_callback(
            callback_url=callback_url,
            session_id=session_id,
            tenant_id=tenant_id,
            job_id=job_id,
            status="failed",
            error=str(e)
        )


async def _transcribe_url(
    audio_url: str,
    session_id: str,
    tenant_id: str,
    callback_url: str,
    language: Optional[str],
    job_id: str
):
    """Background task: download and transcribe from URL"""
    try:
        # Download audio
        logger.info(f"📥 [DOWNLOAD] Downloading audio from URL for job {job_id}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(audio_url, timeout=60)
            response.raise_for_status()
        
        temp_path = f"/tmp/audio_{job_id}.wav"
        with open(temp_path, "wb") as f:
            f.write(response.content)
        
        logger.info(f"🎤 [TRANSCRIBE] Processing URL audio for job {job_id}")
        
        # Transcribe using faster-whisper
        model = get_whisper_model()
        segments, info = model.transcribe(
            temp_path,
            language=language,
            beam_size=5
        )
        
        # Convert segments to list and build transcript
        segments_list = []
        transcript_parts = []
        
        for segment in segments:
            seg_info = {
                "id": segment.id,
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "confidence": segment.confidence if hasattr(segment, 'confidence') else 0.9
            }
            segments_list.append(seg_info)
            transcript_parts.append(segment.text)
        
        transcript_text = " ".join(transcript_parts)
        detected_language = info.language if info else "unknown"
        
        logger.info(f"✅ [TRANSCRIBE] Completed job {job_id}: {len(transcript_text)} chars")
        
        # Send callback
        await _send_callback(
            callback_url=callback_url,
            session_id=session_id,
            tenant_id=tenant_id,
            job_id=job_id,
            transcript=transcript_text,
            language=detected_language,
            segments=segments_list,
            status="completed"
        )
        
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    except Exception as e:
        logger.error(f"❌ [TRANSCRIBE] Failed job {job_id}: {e}")
        await _send_callback(
            callback_url=callback_url,
            session_id=session_id,
            tenant_id=tenant_id,
            job_id=job_id,
            status="failed",
            error=str(e)
        )


async def _send_callback(
    callback_url: str,
    session_id: str,
    tenant_id: str,
    job_id: str,
    status: str,
    transcript: Optional[str] = None,
    language: Optional[str] = None,
    segments: Optional[list] = None,
    error: Optional[str] = None
):
    """Send transcription result back to voice-api via webhook"""
    try:
        payload = {
            "job_id": job_id,
            "session_id": session_id,
            "tenant_id": tenant_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if status == "completed":
            payload.update({
                "transcript": transcript,
                "language": language,
                "segments": segments or [],
                "confidence": "high"
            })
        else:
            payload["error"] = error
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                callback_url,
                json=payload,
                headers={
                    "X-STT-Service": "Whisper",
                    "X-Tenant-Id": tenant_id,
                }
            )
            response.raise_for_status()
        
        logger.info(f"✅ [CALLBACK] Sent results for job {job_id} to {callback_url}")
    
    except Exception as e:
        logger.error(f"❌ [CALLBACK] Failed to send results for job {job_id}: {e}")


# ============================================================================
# Status & Admin Endpoints
# ============================================================================

@app.get("/v1/status/{job_id}")
async def get_transcription_status(job_id: str):
    """
    Get status of a transcription job
    Note: This is a simplified implementation. 
    For production, use a proper job queue (Celery, RQ, etc.)
    """
    return {
        "job_id": job_id,
        "status": "unknown",
        "note": "Job status tracking not yet implemented. Check webhook callback for completion."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )
