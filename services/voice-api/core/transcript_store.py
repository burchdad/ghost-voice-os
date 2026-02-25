"""
Transcript Store
Persistent storage and retrieval of call transcripts with full-text search
"""

import logging
from typing import List, Dict, Any
from core.storage import get_opensearch_client
from core.call_session import CallSession

logger = logging.getLogger(__name__)


class TranscriptStore:
    """Handles transcript storage and retrieval"""

    def __init__(self):
        """Initialize transcript store"""
        self.opensearch = get_opensearch_client()

    async def add_transcript_entry(
        self,
        session: CallSession,
        speaker: str,
        text: str,
        timestamp: str
    ) -> bool:
        """
        Add transcript entry to storage
        
        Args:
            session: Call session
            speaker: Speaker (ai or caller)
            text: Transcript text
            timestamp: ISO timestamp
            
        Returns:
            True if successful
        """
        try:
            await self.opensearch.index_transcript_entry(
                session_id=session.session_id,
                provider_call_id=session.provider_call_id,
                tenant_id=session.tenant_id,
                speaker=speaker,
                text=text,
                timestamp=timestamp,
                turn=session.turn_count
            )
            return True
        except Exception as e:
            logger.error(f"❌ [TRANSCRIPT] Failed to add entry: {e}")
            return False

    async def get_call_transcript(
        self,
        provider_call_id: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieve full transcript for a call
        
        Args:
            provider_call_id: Provider call ID
            
        Returns:
            List of transcript entries in order
        """
        try:
            entries = await self.opensearch.get_call_transcript(provider_call_id)
            logger.info(f"✅ [TRANSCRIPT] Retrieved {len(entries)} entries for {provider_call_id}")
            return entries
        except Exception as e:
            logger.error(f"❌ [TRANSCRIPT] Failed to retrieve transcript: {e}")
            return []

    async def search_transcripts(
        self,
        tenant_id: str,
        query: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Full-text search transcripts across all calls for a tenant
        
        Args:
            tenant_id: Tenant ID
            query: Search query
            limit: Result limit
            
        Returns:
            List of matching transcript entries
        """
        try:
            results = await self.opensearch.search_transcripts(
                tenant_id=tenant_id,
                query=query,
                limit=limit
            )
            logger.info(f"✅ [TRANSCRIPT] Search found {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"❌ [TRANSCRIPT] Search failed: {e}")
            return []

    async def export_call_transcript(
        self,
        provider_call_id: str,
        format: str = "json"
    ) -> str:
        """
        Export call transcript in specified format
        
        Args:
            provider_call_id: Provider call ID
            format: Export format (json, txt, csv)
            
        Returns:
            Formatted transcript
        """
        try:
            entries = await self.get_call_transcript(provider_call_id)
            
            if format == "json":
                import json
                return json.dumps(entries, indent=2)
            
            elif format == "txt":
                lines = []
                for entry in entries:
                    speaker = entry.get("speaker", "unknown").upper()
                    text = entry.get("text", "")
                    timestamp = entry.get("timestamp", "")
                    lines.append(f"[{timestamp}] {speaker}: {text}")
                return "\n".join(lines)
            
            elif format == "csv":
                import csv
                import io
                output = io.StringIO()
                writer = csv.DictWriter(
                    output,
                    fieldnames=["timestamp", "speaker", "text", "turn"]
                )
                writer.writeheader()
                for entry in entries:
                    writer.writerow({
                        "timestamp": entry.get("timestamp", ""),
                        "speaker": entry.get("speaker", ""),
                        "text": entry.get("text", ""),
                        "turn": entry.get("turn", "")
                    })
                return output.getvalue()
            
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            logger.error(f"❌ [TRANSCRIPT] Export failed: {e}")
            return ""

    async def get_conversation_summary(
        self,
        provider_call_id: str
    ) -> Dict[str, Any]:
        """
        Generate summary of call transcript
        
        Args:
            provider_call_id: Provider call ID
            
        Returns:
            Summary statistics
        """
        try:
            entries = await self.get_call_transcript(provider_call_id)
            
            ai_turns = len([e for e in entries if e.get("speaker") == "ai"])
            caller_turns = len([e for e in entries if e.get("speaker") == "caller"])
            total_words = sum(
                len(e.get("text", "").split()) for e in entries
            )
            
            return {
                "total_entries": len(entries),
                "ai_turns": ai_turns,
                "caller_turns": caller_turns,
                "total_words": total_words,
                "avg_words_per_turn": round(total_words / len(entries), 2) if entries else 0
            }
            
        except Exception as e:
            logger.error(f"❌ [TRANSCRIPT] Summary generation failed: {e}")
            return {}


def get_transcript_store() -> TranscriptStore:
    """Factory function for transcript store"""
    return TranscriptStore()
