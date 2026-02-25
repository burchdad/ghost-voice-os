"""
Call Persistence Helper
Simplifies persisting call data to OpenSearch during webhook handling
"""

import logging
from typing import Optional
from core.call_session import CallSession
from core.storage import get_opensearch_client
from core.event_logger import get_event_logger
from core.transcript_store import get_transcript_store

logger = logging.getLogger(__name__)


class CallPersistence:
    """Helper for persisting call data to OpenSearch"""

    def __init__(self):
        """Initialize persistence helper"""
        self.opensearch = get_opensearch_client()
        self.event_logger = get_event_logger()
        self.transcript_store = get_transcript_store()

    async def persist_call_session(self, session: CallSession) -> bool:
        """
        Persist complete call session to OpenSearch
        
        Args:
            session: Call session to persist
            
        Returns:
            True if successful
        """
        try:
            await self.opensearch.index_call(session.to_dict())
            logger.info(f"✅ [PERSIST] Call persisted: {session.session_id}")
            return True
        except Exception as e:
            logger.error(f"❌ [PERSIST] Failed to persist call: {e}")
            return False

    async def persist_transcript(
        self,
        session: CallSession,
        speaker: str,
        text: str,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Persist transcript entry
        
        Args:
            session: Call session
            speaker: Speaker (ai or caller)
            text: Transcript text
            metadata: Optional metadata dict (segments, confidence, etc.)
            
        Returns:
            True if successful
        """
        try:
            from datetime import datetime
            await self.transcript_store.add_transcript_entry(
                session=session,
                speaker=speaker,
                text=text,
                timestamp=datetime.utcnow().isoformat(),
                metadata=metadata
            )
            return True
        except Exception as e:
            logger.error(f"❌ [PERSIST] Failed to persist transcript: {e}")
            return False

    async def log_event(
        self,
        session: CallSession,
        event_type: str,
        event_data: dict
    ) -> bool:
        """
        Log call event
        
        Args:
            session: Call session
            event_type: Type of event
            event_data: Event data
            
        Returns:
            True if successful
        """
        try:
            await self.event_logger.log_call_event(
                session=session,
                event_type=event_type,
                event_data=event_data
            )
            return True
        except Exception as e:
            logger.error(f"❌ [PERSIST] Failed to log event: {e}")
            return False


def get_call_persistence() -> CallPersistence:
    """Factory function for call persistence helper"""
    return CallPersistence()
