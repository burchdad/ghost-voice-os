"""
Apple STT Provider - Communicates with voice-stt-apple microservice
Uses WebSocket for real-time audio streaming
Falls back to Whisper if Apple STT unavailable
"""

import httpx
import asyncio
from typing import Dict, Any, Optional
from .base import STTProvider


class AppleSTTProvider(STTProvider):
    """Apple Speech Framework integration via microservice"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.service_url = config.get("service_url", "http://localhost:8001")
        self.timeout = config.get("timeout", 30)
        self.fallback_to_whisper = config.get("fallback_to_whisper", True)
        self.client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client"""
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=self.timeout)
        return self.client

    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "en-US",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Transcribe using Apple Speech Framework

        Args:
            audio_data: WAV or M4A audio bytes
            language: Language code
            **kwargs: Additional options

        Returns:
            Transcription result with confidence score
        """
        try:
            client = await self._get_client()

            # Send audio to Apple STT microservice
            files = {"audio": ("audio.wav", audio_data, "audio/wav")}
            data = {
                "language": language,
                "optimization": kwargs.get("optimization", "default"),
            }

            response = await client.post(
                f"{self.service_url}/v1/transcribe",
                files=files,
                data=data,
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    "text": result.get("transcript", ""),
                    "confidence": result.get("confidence", 0.0),
                    "language": language,
                    "provider": "apple_stt",
                }
            else:
                if self.fallback_to_whisper:
                    print(
                        f"⚠️ Apple STT failed ({response.status_code}), falling back to Whisper"
                    )
                    return await self._fallback_to_whisper(audio_data, language)
                else:
                    raise Exception(f"Apple STT error: {response.status_code}")

        except Exception as e:
            print(f"❌ Apple STT error: {e}")
            if self.fallback_to_whisper:
                return await self._fallback_to_whisper(audio_data, language)
            else:
                return {
                    "text": "",
                    "confidence": 0.0,
                    "language": language,
                    "provider": "apple_stt",
                    "error": str(e),
                }

    async def _fallback_to_whisper(
        self, audio_data: bytes, language: str
    ) -> Dict[str, Any]:
        """Fallback to Whisper STT if available"""
        try:
            # Import here to avoid hard dependency
            import whisper

            model = whisper.load_model("base")
            result = whisper.transcribe(audio_data, language=language)
            return {
                "text": result.get("text", ""),
                "confidence": 0.8,
                "language": language,
                "provider": "whisper_fallback",
            }
        except ImportError:
            return {
                "text": "",
                "confidence": 0.0,
                "language": language,
                "provider": "apple_stt",
                "error": "Apple STT unavailable and Whisper not installed",
            }

    async def health_check(self) -> bool:
        """Check if Apple STT microservice is healthy"""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.service_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"⚠️ Apple STT health check failed: {e}")
            return False

    async def close(self):
        """Close HTTP client"""
        if self.client:
            await self.client.aclose()
