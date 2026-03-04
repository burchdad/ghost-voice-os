"""
WebSocket Routes for Streaming Voice
Real-time bidirectional audio and control channels
"""

import logging
import json
from typing import Optional, Dict, Any
import asyncio
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Header
from fastapi.responses import JSONResponse

from core.call_session import CallSession, CallState
from core.streaming_engine import StreamingConversationEngine
from core.tenant_loader import load_tenant
from providers.streaming.deepgram_streaming import DeepgramStreamingSTT
from providers.streaming.openai_streaming import OpenAIStreamingLLM
from providers.streaming.elevenlabs_streaming import ElevenLabsStreamingTTS
from providers.streaming.local_tts import LocalTTSProvider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/stream", tags=["streaming"])


class StreamingCallManager:
    """Manages active streaming calls via WebSocket"""

    def __init__(self):
        self.active_calls: Dict[str, Dict[str, Any]] = {}

    def create_session(self, session_id: str, websocket: WebSocket, session: CallSession) -> None:
        """Register new streaming session"""
        self.active_calls[session_id] = {
            "websocket": websocket,
            "session": session,
            "started_at": datetime.utcnow(),
            "audio_received": 0,
            "audio_sent": 0,
        }
        logger.info(f"✅ Created streaming session: {session_id}")

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get active session"""
        return self.active_calls.get(session_id)

    def close_session(self, session_id: str) -> None:
        """Close and cleanup session"""
        if session_id in self.active_calls:
            call_data = self.active_calls.pop(session_id)
            duration = (
                datetime.utcnow() - call_data["started_at"]
            ).total_seconds()
            logger.info(
                f"📊 Closed session {session_id} "
                f"(duration: {duration:.1f}s, "
                f"audio in: {call_data['audio_received']}b, "
                f"audio out: {call_data['audio_sent']}b)"
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get streaming stats"""
        return {
            "active_streams": len(self.active_calls),
            "total_audio_received": sum(
                call["audio_received"] for call in self.active_calls.values()
            ),
            "total_audio_sent": sum(
                call["audio_sent"] for call in self.active_calls.values()
            ),
        }


# Global manager
manager = StreamingCallManager()


def get_tts_provider(provider_name: str = "local_tts", voice_id: str = None):
    """
    Get TTS provider instance.
    
    Supports:
    - "local_tts": In-house voice cloning (costs $0, supports user voices)
    - "elevenlabs": Premium external service (costs $0.03/request)
    """
    if provider_name == "elevenlabs":
        logger.info(f"Using ElevenLabs TTS (premium, costs $0.03/request)")
        return ElevenLabsStreamingTTS({"default_voice_id": voice_id or "21m00Tcm4TlvDq8ikWAM"})
    else:
        # Default to local TTS (in-house, free, supports voice cloning)
        logger.info(f"Using Local TTS Provider (free, supports voice cloning)")
        return LocalTTSProvider()


@router.websocket("/ws/call/{session_id}")
async def websocket_call_endpoint(
    websocket: WebSocket,
    session_id: str,
    x_tenant_id: str = Header(default="default"),
    tts_provider: str = "local_tts",
    voice_id: str = "default",
):
    """
    WebSocket endpoint for streaming voice calls with provider selection.

    Connect with: 
    ws://localhost:8000/v1/stream/ws/call/{session_id}?tts_provider=local_tts&voice_id=user_001_custom

    Query Parameters:
    - tts_provider: "local_tts" (free, voice cloning) or "elevenlabs" (premium)
    - voice_id: Which voice to use (for local_tts, use registered voice ID)

    Message format (client → server):
    {
        "type": "audio",
        "data": "<base64 encoded audio chunk>"
    }

    Message format (server → client):
    {
        "type": "transcript" | "audio" | "metadata" | "error",
        ...
    }
    """
    await websocket.accept()
    logger.info(f"🔌 WebSocket connected for session: {session_id} (TTS: {tts_provider})")

    call_data = None
    try:
        # Create mock session for demo (in production, load from DB)
        session = CallSession(
            tenant_id=x_tenant_id,
            provider="websocket",
            provider_call_id=session_id,
            to_number="",
            from_number="",
            voice_config={"voice_id": voice_id, "tts_provider": tts_provider},
            ai_config={
                "prompt": "You are a helpful AI assistant. Keep responses concise.",
                "personality_mode": "friendly",
            },
        )

        manager.create_session(session_id, websocket, session)
        call_data = manager.get_session(session_id)

        # Initialize streaming providers
        stt_provider = DeepgramStreamingSTT({"model": "nova-2"})
        llm_provider = OpenAIStreamingLLM({"model": "gpt-4"})
        
        # Select TTS provider based on user choice
        tts = get_tts_provider(tts_provider, voice_id)

        # Create conversation engine
        engine = StreamingConversationEngine(
            stt_provider=stt_provider,
            llm_provider=llm_provider,
            tts_provider=tts,
            tts_provider=tts_provider,
        )

        # Audio stream from client
        async def audio_stream_generator():
            """Convert WebSocket messages to audio stream"""
            try:
                while True:
                    message = await websocket.receive_json()

                    if message.get("type") == "audio":
                        import base64
                        audio_data = base64.b64decode(message["data"])
                        call_data["audio_received"] += len(audio_data)
                        logger.info(f"📥 Received audio chunk: {len(audio_data)} bytes")
                        yield audio_data

                    elif message.get("type") == "control":
                        control = message.get("command")
                        if control == "stop":
                            logger.info("⏹️  Call stopped by client")
                            break
                        elif control == "pause":
                            logger.info("⏸️  Call paused")
                            await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Audio stream error: {e}")

        # Process streaming pipeline
        async for output in engine.process_call_stream(
            session=session, audio_stream=audio_stream_generator()
        ):
            try:
                if output.get("type") == "audio":
                    # Send audio back to client
                    import base64
                    audio_b64 = base64.b64encode(output["audio_data"]).decode()
                    call_data["audio_sent"] += len(output["audio_data"])

                    await websocket.send_json(
                        {
                            "type": "audio",
                            "data": audio_b64,
                            "duration_ms": output.get("duration_ms", 50),
                        }
                    )
                    logger.debug(f"📤 Sent audio: {len(output['audio_data'])} bytes")

                elif output.get("type") == "transcript":
                    # Send transcript to client
                    await websocket.send_json(
                        {
                            "type": "transcript",
                            "text": output["text"],
                            "is_final": output.get("is_final", False),
                            "confidence": output.get("confidence", 0),
                        }
                    )
                    logger.info(f"📝 Sent transcript: {output['text'][:50]}")

                elif output.get("type") == "error":
                    # Send error to client
                    await websocket.send_json(
                        {
                            "type": "error",
                            "error": output["error"],
                            "phase": output.get("phase", "unknown"),
                        }
                    )
                    logger.error(f"❌ Error in {output.get('phase')}: {output['error']}")

                elif output.get("type") == "metadata":
                    # Send metadata/status updates
                    await websocket.send_json(
                        {
                            "type": "metadata",
                            "data": output,
                        }
                    )

            except Exception as e:
                logger.error(f"Error sending output: {e}")
                await websocket.send_json({"type": "error", "error": str(e)})

    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected: {session_id}")

    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "error": str(e)})
        except:
            pass

    finally:
        if call_data:
            manager.close_session(session_id)
        try:
            await websocket.close()
        except:
            pass


@router.get("/stats")
async def get_streaming_stats():
    """Get real-time streaming statistics"""
    return manager.get_stats()


@router.post("/stream/config")
async def configure_stream(
    config: Dict[str, Any], x_tenant_id: str = Header(default="default")
):
    """
    Configure streaming pipeline parameters.

    Body:
    {
        "stt_provider": "deepgram" | "whisper",
        "llm_provider": "openai" | "claude",
        "tts_provider": "elevenlabs" | "local",
        "language": "en-US",
        "sample_rate": 16000
    }
    """
    try:
        return {
            "status": "configured",
            "config": config,
            "tenant_id": x_tenant_id,
        }
    except Exception as e:
        return {"error": str(e)}, 400
