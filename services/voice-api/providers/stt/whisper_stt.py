"""
Whisper STT Provider - OpenAI's open-source speech recognition
"""

from typing import Dict, Any
from .base import STTProvider


class WhisperSTTProvider(STTProvider):
    """OpenAI Whisper speech recognition"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model_name = config.get("model_name", "base")
        self.model = None

    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "en-US",
        **kwargs
    ) -> Dict[str, Any]:
        """Transcribe using Whisper"""
        try:
            import whisper

            if self.model is None:
                self.model = whisper.load_model(self.model_name)

            result = self.model.transcribe(audio_data, language=language)

            return {
                "text": result.get("text", ""),
                "confidence": 0.85,
                "language": language,
                "provider": "whisper",
            }
        except Exception as e:
            print(f"❌ Whisper error: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "language": language,
                "provider": "whisper",
                "error": str(e),
            }

    async def health_check(self) -> bool:
        """Check if Whisper is available"""
        try:
            import whisper

            return True
        except ImportError:
            return False
