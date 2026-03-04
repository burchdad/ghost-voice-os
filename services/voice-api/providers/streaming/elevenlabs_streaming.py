"""
ElevenLabs Streaming TTS Implementation
Real-time text-to-speech with streaming audio output
"""

import asyncio
import logging
from typing import Optional, Dict, Any, AsyncGenerator
import os
import json

try:
    import elevenlabs
    from elevenlabs.client import ElevenLabs
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False

from providers.streaming.tts_base import StreamingTTSProvider

logger = logging.getLogger(__name__)


class ElevenLabsStreamingTTS(StreamingTTSProvider):
    """ElevenLabs streaming text-to-speech provider"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        if not ELEVENLABS_AVAILABLE:
            raise RuntimeError("elevenlabs not installed. Install with: pip install elevenlabs")

        self.api_key = config.get("api_key") or os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError("ElevenLabs API key not found in config or ELEVENLABS_API_KEY env var")

        self.client = ElevenLabs(api_key=self.api_key)
        self.model = config.get("model", "eleven_monolingual_v1")
        self.default_voice_id = config.get("default_voice_id", "21m00Tcm4TlvDq8ikWAM")  # Rachel

        # Voice settings for consistent quality
        self.voice_settings = config.get("voice_settings", {
            "stability": 0.5,
            "similarity_boost": 0.75,
        })

    async def stream_synthesize(
        self,
        text_stream: AsyncGenerator[str, None],
        voice_id: str = "default",
        language: str = "en-US",
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream text chunks to ElevenLabs and yield audio chunks.
        """
        try:
            if voice_id == "default":
                voice_id = self.default_voice_id

            logger.info(f"🔊 ElevenLabs streaming started with voice: {voice_id}")

            # Collect all text to synthesize (ElevenLabs doesn't support streaming input)
            # but we can stream the output
            full_text = ""
            async for text_chunk in text_stream:
                full_text += text_chunk

            if not full_text.strip():
                logger.warning("Empty text for TTS synthesis")
                return

            logger.info(f"Synthesizing text: {full_text[:100]}...")

            # Call ElevenLabs with streaming response
            response = await asyncio.to_thread(
                self._synthesize_with_streaming,
                full_text,
                voice_id,
                language,
                kwargs
            )

            # Stream audio chunks
            chunk_count = 0
            async for audio_chunk in response:
                chunk_count += 1
                yield {
                    "type": "audio_chunk",
                    "audio_data": audio_chunk,
                    "is_final": False,
                    "voice_id": voice_id,
                    "provider": "elevenlabs",
                    "duration_ms": 50,  # Approximate
                }

            logger.info(f"✅ ElevenLabs synthesis complete ({chunk_count} chunks)")

        except Exception as e:
            logger.error(f"❌ ElevenLabs stream_synthesize error: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e),
                "provider": "elevenlabs",
            }

    def _synthesize_with_streaming(
        self, 
        text: str, 
        voice_id: str, 
        language: str, 
        kwargs: Dict[str, Any]
    ) -> AsyncGenerator[bytes, None]:
        """Synchronous wrapper for ElevenLabs streaming synthesis"""
        try:
            response = self.client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id=self.model,
                voice_settings=self.voice_settings,
            )

            # Return an async generator from sync response
            async def stream_response():
                for chunk in response:
                    yield chunk

            return stream_response()

        except Exception as e:
            logger.error(f"ElevenLabs API error: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if ElevenLabs API is accessible"""
        try:
            voices = await asyncio.to_thread(self.client.voices.get_all)
            return len(voices) > 0
        except Exception as e:
            logger.error(f"ElevenLabs health check failed: {e}")
            return False

    async def list_voices(self) -> Dict[str, Any]:
        """List available voices from ElevenLabs"""
        try:
            voices = await asyncio.to_thread(self.client.voices.get_all)
            return {
                "voices": [
                    {
                        "voice_id": voice.voice_id,
                        "name": voice.name,
                        "category": voice.category,
                    }
                    for voice in voices
                ]
            }
        except Exception as e:
            logger.error(f"Error fetching voices: {e}")
            return {"voices": [], "error": str(e)}
