"""
Local TTS Provider - Uses system TTS (fast fallback)
"""

from typing import Dict, Any
from .base import TTSProvider


class LocalTTSProvider(TTSProvider):
    """Local TTS using pyttsx3 or espeak"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.engine = None

    async def synthesize(
        self,
        text: str,
        voice_id: str = "default",
        language: str = "en-US",
        **kwargs
    ) -> Dict[str, Any]:
        """Synthesize using local TTS engine"""
        try:
            import pyttsx3
            import io

            if self.engine is None:
                self.engine = pyttsx3.init()

            # Save to bytes buffer
            output_buffer = io.BytesIO()

            # Configure engine
            self.engine.setProperty("rate", 150)  # Speed of speech
            self.engine.setProperty("volume", 1.0)  # Volume 0-1

            # Save audio to buffer
            audio_file = "/tmp/tts_output.wav"
            self.engine.save_to_file(text, audio_file)
            self.engine.runAndWait()

            with open(audio_file, "rb") as f:
                audio_data = f.read()

            return {
                "audio_data": audio_data,
                "voice_id": voice_id,
                "provider": "local_tts",
                "duration_ms": len(text) * 60,  # Estimate
            }

        except Exception as e:
            print(f"❌ Local TTS error: {e}")
            return {
                "provider": "local_tts",
                "error": str(e),
            }

    async def health_check(self) -> bool:
        """Local TTS is always available"""
        try:
            import pyttsx3

            return True
        except ImportError:
            return False

    async def list_voices(self) -> Dict[str, Any]:
        """List available local voices"""
        return {
            "voices": [
                {"id": "default", "name": "Default"},
                {"id": "female", "name": "Female"},
                {"id": "male", "name": "Male"},
            ]
        }
