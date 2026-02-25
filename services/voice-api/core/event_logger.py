"""
Event Logger
Centralized logging of call events to OpenSearch
"""

import logging
from typing import Dict, Any
from datetime import datetime
from core.storage import get_opensearch_client
from core.call_session import CallSession

logger = logging.getLogger(__name__)


class EventLogger:
    """Logs call events to OpenSearch for analytics and compliance"""

    def __init__(self):
        """Initialize event logger"""
        self.opensearch = get_opensearch_client()

    async def log_call_event(
        self,
        session: CallSession,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> bool:
        """
        Log a call event
        
        Args:
            session: Call session
            event_type: Type of event (call_initiated, call_answered, etc.)
            event_data: Event-specific data
            
        Returns:
            True if successful
        """
        try:
            await self.opensearch.index_event(
                session_id=session.session_id,
                provider_call_id=session.provider_call_id,
                tenant_id=session.tenant_id,
                event_type=event_type,
                timestamp=datetime.utcnow().isoformat(),
                turn=session.turn_count,
                data=event_data
            )
            return True
        except Exception as e:
            logger.error(f"❌ [EVENT_LOG] Failed to log event: {e}")
            return False

    async def log_call_state_change(
        self,
        session: CallSession,
        old_state: str,
        new_state: str
    ) -> bool:
        """Log state transitions"""
        return await self.log_call_event(
            session,
            "state_change",
            {
                "from": old_state,
                "to": new_state,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    async def log_call_answered(self, session: CallSession) -> bool:
        """Log call answered event"""
        return await self.log_call_event(
            session,
            "call_answered",
            {"to": session.to_number, "from": session.from_number}
        )

    async def log_machine_detection(
        self,
        session: CallSession,
        result: str
    ) -> bool:
        """Log answering machine detection"""
        return await self.log_call_event(
            session,
            "machine_detection",
            {"result": result}
        )

    async def log_dtmf_received(
        self,
        session: CallSession,
        digits: str
    ) -> bool:
        """Log DTMF input"""
        return await self.log_call_event(
            session,
            "dtmf_received",
            {"digits": digits}
        )

    async def log_speaking(
        self,
        session: CallSession,
        speaker: str,
        duration_ms: int
    ) -> bool:
        """Log speaking event"""
        return await self.log_call_event(
            session,
            "speaking",
            {"speaker": speaker, "duration_ms": duration_ms}
        )

    async def log_call_ended(
        self,
        session: CallSession,
        reason: str,
        duration_seconds: int
    ) -> bool:
        """Log call end event"""
        return await self.log_call_event(
            session,
            "call_ended",
            {
                "reason": reason,
                "duration_seconds": duration_seconds,
                "total_turns": session.turn_count,
                "recording_url": session.recording_url
            }
        )

    async def log_error(
        self,
        session: CallSession,
        error_type: str,
        error_message: str
    ) -> bool:
        """Log error during call"""
        return await self.log_call_event(
            session,
            "error",
            {
                "error_type": error_type,
                "error_message": error_message
            }
        )


def get_event_logger() -> EventLogger:
    """Factory function for event logger"""
    return EventLogger()
