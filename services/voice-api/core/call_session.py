"""
Call Session Model & Redis Store
Unified state machine for Telnyx and Twilio calls
"""

import json
import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import redis
import os

logger = logging.getLogger(__name__)


class CallState(str, Enum):
    """Call lifecycle states"""
    INITIATED = "initiated"
    RINGING = "ringing"
    ANSWERED = "answered"
    SPEAKING = "speaking"
    GATHERING = "gathering"
    RESPONDING = "responding"
    ENDED = "ended"
    FAILED = "failed"


class CallSession:
    """Unified call session model for both Telnyx and Twilio"""

    def __init__(
        self,
        tenant_id: str,
        provider: str,
        provider_call_id: str,
        to_number: str,
        from_number: str,
        voice_config: Optional[Dict[str, Any]] = None,
        ai_config: Optional[Dict[str, Any]] = None,
        lead_data: Optional[Dict[str, Any]] = None,
        callback_urls: Optional[Dict[str, str]] = None,
    ):
        self.session_id = str(uuid.uuid4())
        self.tenant_id = tenant_id
        self.provider = provider  # "telnyx" or "twilio"
        self.provider_call_id = provider_call_id
        self.to_number = to_number
        self.from_number = from_number
        
        self.voice_config = voice_config or {
            "voice_id": "default",
            "voice_type": "primary",
            "language": "en-US"
        }
        
        self.ai_config = ai_config or {
            "prompt": "Hello, this is an AI assistant.",
            "personality_mode": "professional",
            "max_turns": 10
        }
        
        self.lead_data = lead_data or {}
        self.callback_urls = callback_urls or {}
        
        self.state = CallState.INITIATED
        self.turn_count = 0
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = self.created_at
        self.ended_at: Optional[str] = None
        
        # Transcript and events
        self.transcript: list = []
        self.events: list = []
        self.recording_url: Optional[str] = None
        self.metrics = {
            "duration_seconds": 0,
            "silence_count": 0,
            "interruption_count": 0,
            "sentiment": None
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to serializable dict"""
        return {
            "session_id": self.session_id,
            "tenant_id": self.tenant_id,
            "provider": self.provider,
            "provider_call_id": self.provider_call_id,
            "to_number": self.to_number,
            "from_number": self.from_number,
            "voice_config": self.voice_config,
            "ai_config": self.ai_config,
            "lead_data": self.lead_data,
            "callback_urls": self.callback_urls,
            "state": self.state.value,
            "turn_count": self.turn_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "ended_at": self.ended_at,
            "transcript": self.transcript,
            "events": self.events,
            "recording_url": self.recording_url,
            "metrics": self.metrics,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "CallSession":
        """Create session from dict"""
        session = CallSession(
            tenant_id=data["tenant_id"],
            provider=data["provider"],
            provider_call_id=data["provider_call_id"],
            to_number=data["to_number"],
            from_number=data["from_number"],
            voice_config=data.get("voice_config"),
            ai_config=data.get("ai_config"),
            lead_data=data.get("lead_data"),
            callback_urls=data.get("callback_urls"),
        )
        
        session.session_id = data.get("session_id", session.session_id)
        session.state = CallState(data.get("state", "initiated"))
        session.turn_count = data.get("turn_count", 0)
        session.created_at = data.get("created_at", session.created_at)
        session.updated_at = data.get("updated_at", session.updated_at)
        session.ended_at = data.get("ended_at")
        session.transcript = data.get("transcript", [])
        session.events = data.get("events", [])
        session.recording_url = data.get("recording_url")
        session.metrics = data.get("metrics", session.metrics)
        
        return session

    def add_transcript_entry(self, speaker: str, text: str):
        """Add entry to call transcript"""
        self.transcript.append({
            "timestamp": datetime.utcnow().isoformat(),
            "speaker": speaker,  # "caller" or "ai"
            "text": text,
            "turn": self.turn_count
        })

    def add_event(self, event_type: str, data: Dict[str, Any]):
        """Log call event"""
        self.events.append({
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type,
            "data": data,
            "turn": self.turn_count
        })

    def advance_state(self, new_state: CallState):
        """Update call state"""
        logger.info(f"[SESSION] {self.session_id}: {self.state.value} → {new_state.value}")
        self.state = new_state
        self.updated_at = datetime.utcnow().isoformat()

    def increment_turn(self):
        """Move to next conversation turn"""
        self.turn_count += 1


class RedisCallSessionStore:
    """Redis-backed store for call sessions"""

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize Redis connection"""
        redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = redis.from_url(redis_url)
        self.ttl_seconds = 3600 * 4  # 4 hour TTL for call sessions

    def _make_key(self, provider_call_id: str) -> str:
        """Generate Redis key for session"""
        return f"call_session:{provider_call_id}"

    async def store(self, session: CallSession) -> bool:
        """Store session in Redis"""
        try:
            key = self._make_key(session.provider_call_id)
            data = json.dumps(session.to_dict())
            self.redis_client.setex(key, self.ttl_seconds, data)
            logger.info(f"✅ [STORE] Stored session {session.session_id} for {session.provider_call_id}")
            return True
        except Exception as e:
            logger.error(f"❌ [STORE] Failed to store session: {e}")
            return False

    async def get(self, provider_call_id: str) -> Optional[CallSession]:
        """Retrieve session from Redis"""
        try:
            key = self._make_key(provider_call_id)
            data = self.redis_client.get(key)
            if not data:
                logger.warning(f"⚠️  [GET] Session not found for {provider_call_id}")
                return None
            
            session = CallSession.from_dict(json.loads(data))
            logger.info(f"✅ [GET] Retrieved session {session.session_id}")
            return session
        except Exception as e:
            logger.error(f"❌ [GET] Failed to retrieve session: {e}")
            return None

    async def delete(self, provider_call_id: str) -> bool:
        """Delete session from Redis"""
        try:
            key = self._make_key(provider_call_id)
            self.redis_client.delete(key)
            logger.info(f"✅ [DELETE] Deleted session for {provider_call_id}")
            return True
        except Exception as e:
            logger.error(f"❌ [DELETE] Failed to delete session: {e}")
            return False

    async def update_transcript(self, provider_call_id: str, speaker: str, text: str) -> bool:
        """Add transcript entry"""
        try:
            session = await self.get(provider_call_id)
            if not session:
                return False
            
            session.add_transcript_entry(speaker, text)
            await self.store(session)
            return True
        except Exception as e:
            logger.error(f"❌ [TRANSCRIPT] Failed to update: {e}")
            return False

    async def update_event(self, provider_call_id: str, event_type: str, data: Dict[str, Any]) -> bool:
        """Add event entry"""
        try:
            session = await self.get(provider_call_id)
            if not session:
                return False
            
            session.add_event(event_type, data)
            await self.store(session)
            return True
        except Exception as e:
            logger.error(f"❌ [EVENT] Failed to log event: {e}")
            return False


# Global session store instance
_session_store: Optional[RedisCallSessionStore] = None


def get_session_store() -> RedisCallSessionStore:
    """Get or create global session store"""
    global _session_store
    if _session_store is None:
        _session_store = RedisCallSessionStore()
    return _session_store
