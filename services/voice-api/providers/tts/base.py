"""
Base TTS Provider Interface
All TTS providers must implement this interface
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class TTSProvider(ABC):
    """Abstract base class for Text-to-Speech providers"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_id: str = "default",
        language: str = "en-US",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Synthesize text to speech

        Args:
            text: Text to synthesize
            voice_id: Voice identifier
            language: Language code
            **kwargs: Provider-specific options

        Returns:
            {
                "audio_url": "https://...",
                "audio_data": bytes (optional),
                "voice_id": "...",
                "provider": "elevenlabs",
                "duration_ms": 3000
            }
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is healthy"""
        pass

    @abstractmethod
    async def list_voices(self) -> Dict[str, Any]:
        """List available voices"""
        pass
