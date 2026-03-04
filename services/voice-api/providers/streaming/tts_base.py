"""
Base Streaming TTS Provider Interface
All streaming TTS providers must implement this interface
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, AsyncGenerator


class StreamingTTSProvider(ABC):
    """Abstract base class for Streaming Text-to-Speech providers"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    async def stream_synthesize(
        self,
        text_stream: AsyncGenerator[str, None],
        voice_id: str = "default",
        language: str = "en-US",
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream text chunks and yield audio in real-time.

        Args:
            text_stream: Async generator yielding text chunks
            voice_id: Voice identifier
            language: Language code
            **kwargs: Provider-specific options

        Yields:
            {
                "type": "audio_chunk" | "metadata",
                "audio_data": bytes (audio frame),
                "timestamp": 1234567890,
                "is_final": False | True,
                "voice_id": "...",
                "provider": "elevenlabs",
                "duration_ms": 50  (approximate duration of this chunk)
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
