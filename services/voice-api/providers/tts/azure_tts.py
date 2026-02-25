"""
Azure Speech Services TTS Provider
"""

from typing import Dict, Any
from .base import TTSProvider


class AzureTTSProvider(TTSProvider):
    """Azure Speech Services synthesis"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.region = config.get("region", "eastus")
        self.endpoint = f"https://{self.region}.tts.speech.microsoft.com"

    async def synthesize(
        self,
        text: str,
        voice_id: str = "en-US-AriaNeural",
        language: str = "en-US",
        **kwargs
    ) -> Dict[str, Any]:
        """Synthesize using Azure Speech Services"""
        if not self.api_key:
            return {
                "provider": "azure",
                "error": "Azure API key not configured",
            }

        try:
            import httpx

            headers = {
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-16khz-32kbitrate-mono-mp3",
            }

            ssml = f"""<speak version='1.0' xml:lang='{language}'>
                <voice xml:lang='{language}' name='{voice_id}'>
                    {text}
                </voice>
            </speak>"""

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.endpoint}/cognitiveservices/v1",
                    headers=headers,
                    content=ssml.encode("utf-8"),
                )

                if response.status_code == 200:
                    return {
                        "audio_data": response.content,
                        "voice_id": voice_id,
                        "provider": "azure",
                        "duration_ms": len(response.content) // 4,
                    }
                else:
                    raise Exception(f"API error: {response.status_code}")

        except Exception as e:
            print(f"❌ Azure TTS error: {e}")
            return {
                "provider": "azure",
                "error": str(e),
            }

    async def health_check(self) -> bool:
        """Check Azure Speech Services availability"""
        return bool(self.api_key)

    async def list_voices(self) -> Dict[str, Any]:
        """List available Azure voices"""
        return {
            "voices": [
                {"id": "en-US-AriaNeural", "name": "Aria (Female)"},
                {"id": "en-US-GuyNeural", "name": "Guy (Male)"},
                {"id": "es-ES-AlvaroNeural", "name": "Alvaro (Spanish)"},
            ]
        }
