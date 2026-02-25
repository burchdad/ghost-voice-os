"""
Telnyx Provider Client
Handles Telnyx API calls for outbound initiation and command execution
"""

import logging
import os
import base64
from typing import Dict, Any, Optional
import httpx
import json

logger = logging.getLogger(__name__)


class TelnyxClient:
    """Telnyx API client for call control"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Telnyx client
        
        Args:
            api_key: Telnyx API key (defaults to TELNYX_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("TELNYX_API_KEY")
        if not self.api_key:
            raise ValueError("TELNYX_API_KEY not configured")
        
        self.base_url = "https://api.telnyx.com/v2"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def initiate_call(
        self,
        to_number: str,
        from_number: str,
        connection_id: str,
        client_state: Dict[str, Any],
        webhook_url: str,
        voice_prompt: str = "Hello, this is an AI assistant.",
    ) -> Dict[str, Any]:
        """
        Initiate outbound call via Telnyx
        
        Args:
            to_number: Destination phone number (E.164 format)
            from_number: Caller ID number (E.164 format)
            connection_id: Telnyx connection ID for call routing
            client_state: Session state (will be passed back in webhooks)
            webhook_url: URL for Telnyx to POST events to
            voice_prompt: Initial greeting/prompt
            
        Returns:
            {
                "call_id": "call_control_id",
                "status": "initiated",
                "provider": "telnyx"
            }
        """
        try:
            # Encode client_state as base64 for Telnyx client_state parameter
            client_state_b64 = base64.b64encode(
                json.dumps(client_state).encode()
            ).decode()
            
            payload = {
                "connection_id": connection_id,
                "to": to_number,
                "from": from_number,
                "webhook_url": webhook_url,
                "webhook_url_method": "POST",
                "custom_headers": [
                    {
                        "name": "X-Webhook-Type",
                        "value": "telnyx"
                    }
                ],
                "client_state": client_state_b64,
                "answerOnBridge": False,
                "answeringMachineDetection": "greeting_end",
                "answeringMachineDetectionConfig": {
                    "beep_detection": "greeting_end_beep_detect"
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/calls",
                    json=payload,
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code not in [200, 201]:
                    logger.error(f"❌ [TELNYX] Call initiation failed: {response.text}")
                    return {
                        "status": "failed",
                        "error": response.text,
                        "provider": "telnyx"
                    }
                
                data = response.json()
                call_id = data.get("data", {}).get("call_control_id")
                
                logger.info(f"✅ [TELNYX] Call initiated: {call_id}")
                return {
                    "call_id": call_id,
                    "status": "initiated",
                    "provider": "telnyx",
                    "raw_response": data
                }
                
        except Exception as e:
            logger.error(f"❌ [TELNYX] Exception during call initiation: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "provider": "telnyx"
            }

    async def send_audio(
        self,
        call_control_id: str,
        audio_url: str,
        loop: bool = False
    ) -> bool:
        """
        Send pre-recorded audio to call
        
        Args:
            call_control_id: Telnyx call control ID
            audio_url: URL of audio file to play
            loop: Whether to loop the audio
            
        Returns:
            True if successful
        """
        try:
            payload = {
                "audio_url": audio_url,
                "loop": loop,
                "overlay": False
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/calls/{call_control_id}/audio",
                    json=payload,
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code not in [200, 204]:
                    logger.error(f"❌ [TELNYX] Audio send failed: {response.text}")
                    return False
                
                logger.info(f"✅ [TELNYX] Audio sent to {call_control_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ [TELNYX] Exception sending audio: {e}")
            return False

    async def gather_dtmf(
        self,
        call_control_id: str,
        max_digits: int = 1,
        timeout_secs: int = 5,
        valid_digits: str = "0123456789#*"
    ) -> bool:
        """
        Start DTMF gathering on call
        
        Args:
            call_control_id: Telnyx call control ID
            max_digits: Maximum digits to collect
            timeout_secs: Timeout before giving up
            valid_digits: Allowed DTMF digits
            
        Returns:
            True if started successfully
        """
        try:
            payload = {
                "max_digits": max_digits,
                "timeout_secs": timeout_secs,
                "valid_digits": valid_digits,
                "terminating_digit": "#",
                "inter_digit_timeout_secs": 5
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/calls/{call_control_id}/gather",
                    json=payload,
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code not in [200, 204]:
                    logger.error(f"❌ [TELNYX] DTMF gather failed: {response.text}")
                    return False
                
                logger.info(f"✅ [TELNYX] DTMF gathering started on {call_control_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ [TELNYX] Exception starting DTMF gather: {e}")
            return False

    async def speak(
        self,
        call_control_id: str,
        text: str,
        language: str = "en-US",
        voice: str = "female"
    ) -> bool:
        """
        Synthesize and speak text on call using Telnyx TTS
        
        Args:
            call_control_id: Telnyx call control ID
            text: Text to speak
            language: Language code
            voice: Voice gender (male/female)
            
        Returns:
            True if started successfully
        """
        try:
            payload = {
                "payload": text,
                "language": language,
                "voice": voice,
                "loop": False
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/calls/{call_control_id}/speak",
                    json=payload,
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code not in [200, 204]:
                    logger.error(f"❌ [TELNYX] Speak failed: {response.text}")
                    return False
                
                logger.info(f"✅ [TELNYX] Speaking on {call_control_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ [TELNYX] Exception during speak: {e}")
            return False

    async def hangup(self, call_control_id: str) -> bool:
        """
        Hang up call
        
        Args:
            call_control_id: Telnyx call control ID
            
        Returns:
            True if successful
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/calls/{call_control_id}",
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code not in [200, 204]:
                    logger.error(f"❌ [TELNYX] Hangup failed: {response.text}")
                    return False
                
                logger.info(f"✅ [TELNYX] Call hung up: {call_control_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ [TELNYX] Exception during hangup: {e}")
            return False


def get_telnyx_client() -> TelnyxClient:
    """Factory function for Telnyx client"""
    return TelnyxClient()
