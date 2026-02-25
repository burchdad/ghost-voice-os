"""
Base Telephony Provider Interface
All telephony providers (Twilio, Telnyx) implement this
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class TelephonyProvider(ABC):
    """Abstract base class for telephony providers"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    async def initiate_call(
        self,
        to_number: str,
        from_number: str,
        voice_prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Initiate an outbound call

        Args:
            to_number: Destination phone number
            from_number: Caller ID
            voice_prompt: Initial TTS prompt
            **kwargs: Provider-specific options

        Returns:
            {
                "call_id": "...",
                "status": "initiated",
                "provider": "twilio"
            }
        """
        pass

    @abstractmethod
    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming webhook from provider"""
        pass

    @abstractmethod
    async def send_sms(
        self, to_number: str, message: str, from_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send SMS message"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is healthy"""
        pass
