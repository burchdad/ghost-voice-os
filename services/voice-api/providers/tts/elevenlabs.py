"""
ElevenLabs TTS Provider
Handles text-to-speech synthesis via ElevenLabs API
"""

import os
import httpx
import logging
from typing import Optional
from io import BytesIO

logger = logging.getLogger(__name__)

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"

# Voice ID mapping (update with your actual ElevenLabs voice IDs)
VOICE_MAPPING = {
    "sarah": "EXAVITQu4vr4xnSDxMaL",
    "maria": "ErXwobaYiN019PkySvjV",
    "jessica": "cgSgspJ2msm6clMCkdW9",
    "michael": "flq6f7yk4E4fJM5XTYuZ",
    "carlos": "onwK4e9ZLuTAKqWW03F9",
    "david": "pNInz6obpgDQGcFmaJgB",
}


class ElevenLabsProvider:
    """ElevenLabs text-to-speech provider"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or ELEVENLABS_API_KEY
        self.base_url = ELEVENLABS_BASE_URL

        if not self.api_key:
            logger.warning("❌ [ELEVENLABS] API key not configured")

    async def synthesize(
        self, text: str, voice_id: str = "sarah", language: str = "en-US"
    ) -> BytesIO:
        """
        Synthesize text to speech
        Returns audio data as BytesIO object
        """
        if not self.api_key:
            raise ValueError("ElevenLabs API key not configured")

        # Map voice type to ElevenLabs voice ID
        elevenlabs_voice_id = VOICE_MAPPING.get(voice_id, VOICE_MAPPING["sarah"])

        logger.info(
            f"🎤 [ELEVENLABS] Synthesizing: '{text[:50]}...' with voice: {voice_id}"
        )

        url = f"{self.base_url}/text-to-speech/{elevenlabs_voice_id}/stream"

        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key,
        }

        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.75,
                "similarity_boost": 0.8,
                "style": 0.3,
                "use_speaker_boost": True,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)

                if not response.is_success:
                    error_text = response.text
                    logger.error(
                        f"❌ [ELEVENLABS] API Error: {response.status_code} - {error_text}"
                    )
                    raise Exception(f"ElevenLabs API error: {response.status_code}")

                # Return audio data as BytesIO
                audio_data = BytesIO(response.content)
                audio_data.seek(0)

                logger.info(f"✅ [ELEVENLABS] Generated audio: {len(response.content)} bytes")
                return audio_data

        except httpx.RequestError as e:
            logger.error(f"❌ [ELEVENLABS] Request error: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ [ELEVENLABS] Synthesis error: {e}")
            raise

    async def synthesize_and_save(
        self, text: str, voice_id: str, output_path: str, language: str = "en-US"
    ) -> str:
        """
        Synthesize and save to file
        Returns the file path
        """
        audio_io = await self.synthesize(text, voice_id, language)

        with open(output_path, "wb") as f:
            f.write(audio_io.getvalue())

        logger.info(f"✅ [ELEVENLABS] Saved to: {output_path}")
        return output_path

    def get_available_voices(self) -> dict:
        """Get available voices"""
        return VOICE_MAPPING.copy()

    def map_voice_type(self, voice_type: str) -> str:
        """Map a voice type to an ElevenLabs voice ID"""
        voice_map = {
            "primary": "sarah",
            "sales": "jessica",
            "support": "sarah",
            "spanish": "maria",
            "custom": "sarah",
        }
        return VOICE_MAPPING.get(voice_map.get(voice_type, "sarah"), VOICE_MAPPING["sarah"])


# Singleton instance
_provider = None


def get_elevenlabs_provider() -> ElevenLabsProvider:
    """Get or create ElevenLabs provider instance"""
    global _provider
    if _provider is None:
        _provider = ElevenLabsProvider()
    return _provider
