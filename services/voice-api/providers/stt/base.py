"""
Base STT Provider Interface
All STT providers must implement this interface
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class STTProvider(ABC):
    """Abstract base class for Speech-to-Text providers"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "en-US",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Transcribe audio to text

        Args:
            audio_data: Audio bytes
            language: Language code (e.g., 'en-US')
            **kwargs: Provider-specific options

        Returns:
            {
                "text": "transcribed text",
                "confidence": 0.95,
                "language": "en-US",
                "provider": "apple_stt"
            }
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is healthy"""
        pass
