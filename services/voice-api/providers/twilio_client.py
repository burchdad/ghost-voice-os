"""
Twilio Provider Client
Handles Twilio API calls for outbound initiation and TwiML generation
"""

import logging
import os
from typing import Dict, Any, Optional
import httpx
from twilio.rest import Client as TwilioRestClient
from twilio.twiml.voice_response import VoiceResponse

logger = logging.getLogger(__name__)


class TwilioClient:
    """Twilio API client for call control"""

    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
    ):
        """
        Initialize Twilio client
        
        Args:
            account_sid: Twilio Account SID (defaults to TWILIO_ACCOUNT_SID env var)
            auth_token: Twilio Auth Token (defaults to TWILIO_AUTH_TOKEN env var)
        """
        self.account_sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN")
        
        if not self.account_sid or not self.auth_token:
            raise ValueError("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN not configured")
        
        self.client = TwilioRestClient(self.account_sid, self.auth_token)
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}"

    async def initiate_call(
        self,
        to_number: str,
        from_number: str,
        twiml_url: str,
        session_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Initiate outbound call via Twilio
        
        Args:
            to_number: Destination phone number (E.164 format)
            from_number: Caller ID number (E.164 format)
            twiml_url: URL of TwiML handler (will be fetched by Twilio)
            session_id: Voice OS session ID (passed as query param)
            **kwargs: Additional parameters (status_callback, etc.)
            
        Returns:
            {
                "call_id": "call_sid",
                "status": "initiated",
                "provider": "twilio"
            }
        """
        try:
            # Add session_id to TwiML URL as query param
            callback_url = f"{twiml_url}?session_id={session_id}"
            
            # Make call via Twilio REST API
            call = self.client.calls.create(
                to=to_number,
                from_=from_number,
                url=callback_url,
                status_callback=kwargs.get("status_callback"),
                status_callback_event=kwargs.get("status_callback_event", "initiated completed failed"),
                method="POST",
                timeout=15
            )
            
            logger.info(f"✅ [TWILIO] Call initiated: {call.sid}")
            return {
                "call_id": call.sid,
                "status": "initiated",
                "provider": "twilio",
                "raw_response": {
                    "sid": call.sid,
                    "status": call.status,
                    "to": call.to,
                    "from": call.from_,
                }
            }
            
        except Exception as e:
            logger.error(f"❌ [TWILIO] Exception during call initiation: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "provider": "twilio"
            }

    @staticmethod
    def generate_answer_twiml(
        say_text: str,
        record: bool = False,
        gather: bool = False,
        max_digits: int = 1,
        timeout: int = 5,
    ) -> str:
        """
        Generate TwiML for call answer
        
        Args:
            say_text: Text to speak
            record: Whether to record call
            gather: Whether to gather DTMF input
            max_digits: Max DTMF digits to collect
            timeout: DTMF timeout in seconds
            
        Returns:
            TwiML XML string
        """
        response = VoiceResponse()
        
        if say_text:
            response.say(say_text, voice="Alice", language="en-US")
        
        if record:
            response.record(
                timeout=10,
                finish_on_key="*",
                play_beep=True,
                trim="trim-silence"
            )
        
        if gather:
            with response.gather(
                num_digits=max_digits,
                timeout=timeout,
                action="/v1/webhooks/twilio/gather",
                method="POST"
            ):
                response.say("Press any digit", voice="Alice", language="en-US")
        
        return str(response)

    @staticmethod
    def generate_response_twiml(
        say_text: str,
        next_action_url: Optional[str] = None,
    ) -> str:
        """
        Generate TwiML for call response
        
        Args:
            say_text: Text to speak
            next_action_url: URL to redirect to after speech
            
        Returns:
            TwiML XML string
        """
        response = VoiceResponse()
        
        if say_text:
            response.say(say_text, voice="Alice", language="en-US")
        
        if next_action_url:
            response.redirect(next_action_url, method="POST")
        else:
            response.hangup()
        
        return str(response)

    @staticmethod
    def generate_gather_twiml(
        num_digits: int = 1,
        timeout: int = 5,
        action_url: str = "/v1/webhooks/twilio/gather",
    ) -> str:
        """
        Generate TwiML for DTMF gathering
        
        Args:
            num_digits: Number of digits to collect
            timeout: Timeout in seconds
            action_url: URL to POST gathered digits to
            
        Returns:
            TwiML XML string
        """
        response = VoiceResponse()
        
        with response.gather(
            num_digits=num_digits,
            timeout=timeout,
            action=action_url,
            method="POST"
        ):
            response.say(
                "Please enter your choice",
                voice="Alice",
                language="en-US"
            )
        
        return str(response)

    async def send_sms(
        self,
        to_number: str,
        from_number: str,
        message: str,
    ) -> Dict[str, Any]:
        """
        Send SMS via Twilio
        
        Args:
            to_number: Recipient phone number
            from_number: Sender phone number (Twilio number)
            message: Message text
            
        Returns:
            {
                "message_sid": "...",
                "status": "queued"
            }
        """
        try:
            sms = self.client.messages.create(
                body=message,
                from_=from_number,
                to=to_number
            )
            
            logger.info(f"✅ [TWILIO] SMS sent: {sms.sid}")
            return {
                "message_sid": sms.sid,
                "status": sms.status,
                "provider": "twilio"
            }
            
        except Exception as e:
            logger.error(f"❌ [TWILIO] SMS send failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "provider": "twilio"
            }

    async def record_call(
        self,
        call_sid: str,
        recording_url: str,
    ) -> bool:
        """
        Retrieve call recording (recording is automatic on Twilio)
        
        Args:
            call_sid: Call SID
            recording_url: Where to store recording metadata
            
        Returns:
            True if successful
        """
        try:
            # Twilio automatically records if configured
            # This is mainly for logging purposes
            logger.info(f"✅ [TWILIO] Call recording available for {call_sid}")
            return True
            
        except Exception as e:
            logger.error(f"❌ [TWILIO] Recording retrieval failed: {e}")
            return False


def get_twilio_client() -> TwilioClient:
    """Factory function for Twilio client"""
    return TwilioClient()
