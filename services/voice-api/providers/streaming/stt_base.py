"""
Base Streaming STT Provider Interface
All streaming STT providers must implement this interface
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, AsyncGenerator
import asyncio


class StreamingSTTProvider(ABC):
    """Abstract base class for Streaming Speech-to-Text providers"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    async def stream_transcribe(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        language: str = "en-US",
        interim_results: bool = True,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream audio chunks and yield transcription updates in real-time.

        Args:
            audio_stream: Async generator yielding audio chunks (bytes)
            language: Language code (e.g., 'en-US')
            interim_results: If True, yield partial transcriptions
            **kwargs: Provider-specific options

        Yields:
            {
                "type": "interim" | "final",
                "text": "partial or final transcript",
                "confidence": 0.95,
                "is_final": False | True,
                "timestamp": 1234567890,
                "language": "en-US",
                "provider": "deepgram"
            }
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is healthy"""
        pass


class StreamingSTTBuffer:
    """Buffer for collecting streaming STT results"""

    def __init__(self, chunk_size: int = 20480, sample_rate: int = 16000):
        self.chunk_size = chunk_size
        self.sample_rate = sample_rate
        self.buffer = bytearray()
        self.lock = asyncio.Lock()

    async def add_chunk(self, chunk: bytes) -> Optional[bytes]:
        """
        Add audio chunk to buffer and return ready-to-send chunk if available.

        Returns:
            bytes if buffer has enough data, None otherwise
        """
        async with self.lock:
            self.buffer.extend(chunk)
            if len(self.buffer) >= self.chunk_size:
                chunk_to_send = bytes(self.buffer[: self.chunk_size])
                self.buffer = self.buffer[self.chunk_size :]
                return chunk_to_send
        return None

    async def flush(self) -> Optional[bytes]:
        """Get remaining data from buffer"""
        async with self.lock:
            if self.buffer:
                result = bytes(self.buffer)
                self.buffer = bytearray()
                return result
        return None
