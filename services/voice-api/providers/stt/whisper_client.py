"""
STT Provider Client
Whisper microservice integration for transcription
"""

import logging
import os
import httpx
from typing import Optional, Dict, Any
from core.call_session import CallSession

logger = logging.getLogger(__name__)


class WhisperSTTClient:
    """Client for Whisper STT microservice"""

    def __init__(self, stt_service_url: Optional[str] = None):
        """
        Initialize Whisper STT client
        
        Args:
            stt_service_url: Base URL of STT service
        """
        self.stt_service_url = stt_service_url or os.getenv(
            "STT_SERVICE_URL", 
            "http://localhost:8001"
        )
        logger.info(f"✅ [STT] Whisper client initialized: {self.stt_service_url}")

    async def transcribe_from_url(
        self,
        session: CallSession,
        audio_url: str,
        callback_url: str,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Submit audio URL for transcription
        
        Args:
            session: Call session for tracking
            audio_url: URL to audio file
            callback_url: Webhook URL to receive transcript
            language: ISO-639-1 language code (optional)
        
        Returns:
            Job info dict with job_id and status
        """
        try:
            payload = {
                "audio_url": audio_url,
                "session_id": session.session_id,
                "tenant_id": session.tenant_id,
                "callback_url": callback_url,
            }
            
            if language:
                payload["language"] = language
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.stt_service_url}/v1/transcribe",
                    data=payload,
                    headers={"X-Session-Id": session.session_id}
                )
                response.raise_for_status()
            
            result = response.json()
            logger.info(f"📝 [STT] Job queued: {result.get('job_id')} for session {session.session_id}")
            
            return result
        
        except Exception as e:
            logger.error(f"❌ [STT] Failed to submit transcription: {e}")
            raise

    async def transcribe_from_file(
        self,
        session: CallSession,
        file_path: str,
        callback_url: str,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Submit audio file for transcription
        
        Args:
            session: Call session for tracking
            file_path: Path to audio file
            callback_url: Webhook URL to receive transcript
            language: ISO-639-1 language code (optional)
        
        Returns:
            Job info dict with job_id and status
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Audio file not found: {file_path}")
            
            with open(file_path, "rb") as f:
                files = {"file": f}
                data = {
                    "session_id": session.session_id,
                    "tenant_id": session.tenant_id,
                    "callback_url": callback_url,
                }
                
                if language:
                    data["language"] = language
                
                async with httpx.AsyncClient(timeout=60) as client:
                    response = await client.post(
                        f"{self.stt_service_url}/v1/transcribe",
                        files=files,
                        data=data,
                        headers={"X-Session-Id": session.session_id}
                    )
                    response.raise_for_status()
            
            result = response.json()
            logger.info(f"📝 [STT] File job queued: {result.get('job_id')} for session {session.session_id}")
            
            return result
        
        except Exception as e:
            logger.error(f"❌ [STT] Failed to submit file transcription: {e}")
            raise

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get status of a transcription job
        
        Args:
            job_id: Job ID from transcription submission
        
        Returns:
            Job status dict
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.stt_service_url}/v1/status/{job_id}"
                )
                response.raise_for_status()
            
            return response.json()
        
        except Exception as e:
            logger.error(f"❌ [STT] Failed to get job status: {e}")
            raise

    async def health_check(self) -> bool:
        """
        Check if STT service is healthy
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.stt_service_url}/health")
                response.raise_for_status()
            logger.info("✅ [STT] Service health check passed")
            return True
        
        except Exception as e:
            logger.warning(f"⚠️  [STT] Health check failed: {e}")
            return False


# Global STT client instance
_stt_client: Optional[WhisperSTTClient] = None


def get_stt_client() -> WhisperSTTClient:
    """Get or create global STT client"""
    global _stt_client
    if _stt_client is None:
        _stt_client = WhisperSTTClient()
    return _stt_client
