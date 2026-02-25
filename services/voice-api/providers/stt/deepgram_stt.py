"""
Deepgram STT Provider - Enterprise speech recognition
"""

import httpx
from typing import Dict, Any
from .base import STTProvider


class DeepgramSTTProvider(STTProvider):
    """Deepgram API integration"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.base_url = "https://api.deepgram.com/v1"

    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "en-US",
        **kwargs
    ) -> Dict[str, Any]:
        """Transcribe using Deepgram"""
        if not self.api_key:
            return {
                "text": "",
                "confidence": 0.0,
                "language": language,
                "provider": "deepgram",
                "error": "Deepgram API key not configured",
            }

        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Token {self.api_key}",
                    "Content-Type": "audio/wav",
                }
                params = {
                    "model": kwargs.get("model", "nova-2"),
                    "language": language,
                }

                response = await client.post(
                    f"{self.base_url}/listen",
                    headers=headers,
                    params=params,
                    content=audio_data,
                )

                if response.status_code == 200:
                    result = response.json()
                    transcript = result.get("results", {}).get("channels", [{}])[0].get(
                        "alternatives", [{}]
                    )[0].get("transcript", "")
                    confidence = (
                        result.get("results", {})
                        .get("channels", [{}])[0]
                        .get("alternatives", [{}])[0]
                        .get("confidence", 0.0)
                    )

                    return {
                        "text": transcript,
                        "confidence": confidence,
                        "language": language,
                        "provider": "deepgram",
                    }
                else:
                    raise Exception(f"API returned {response.status_code}")

        except Exception as e:
            print(f"❌ Deepgram error: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "language": language,
                "provider": "deepgram",
                "error": str(e),
            }

    async def health_check(self) -> bool:
        """Check if Deepgram API is accessible"""
        if not self.api_key:
            return False

        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Token {self.api_key}"}
                response = await client.get(
                    f"{self.base_url}/status",
                    headers=headers,
                    timeout=5,
                )
                return response.status_code == 200
        except Exception:
            return False
