"""
OpenSearch Storage Layer
Handles persistent storage of calls, transcripts, and metrics
"""

import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from opensearchpy import OpenSearch, NotFoundError
import json

logger = logging.getLogger(__name__)


class OpenSearchClient:
    """OpenSearch client for persistent storage of call data"""

    def __init__(self, url: Optional[str] = None):
        """
        Initialize OpenSearch connection
        
        Args:
            url: OpenSearch URL (defaults to OPENSEARCH_URL env var)
        """
        self.url = url or os.getenv("OPENSEARCH_URL", "http://localhost:9200")
        
        # Parse URL for host/port
        url_parts = self.url.replace("http://", "").replace("https://", "").split(":")
        host = url_parts[0]
        port = int(url_parts[1]) if len(url_parts) > 1 else 9200
        
        self.client = OpenSearch(
            hosts=[{"host": host, "port": port}],
            http_auth=None,  # Modify for production
            use_ssl=False,  # Modify for production
            verify_certs=False,
            ssl_show_warn=False
        )
        
        # Initialize indices
        self._initialize_indices()

    def _initialize_indices(self):
        """Create OpenSearch indices if they don't exist"""
        try:
            # Calls index
            if not self.client.indices.exists(index="calls"):
                self.client.indices.create(
                    index="calls",
                    body={
                        "mappings": {
                            "properties": {
                                "session_id": {"type": "keyword"},
                                "tenant_id": {"type": "keyword"},
                                "provider": {"type": "keyword"},
                                "provider_call_id": {"type": "keyword"},
                                "to_number": {"type": "keyword"},
                                "from_number": {"type": "keyword"},
                                "state": {"type": "keyword"},
                                "turn_count": {"type": "integer"},
                                "created_at": {"type": "date"},
                                "updated_at": {"type": "date"},
                                "ended_at": {"type": "date"},
                                "duration_seconds": {"type": "integer"},
                                "recording_url": {"type": "keyword"},
                                "metrics": {"type": "object"}
                            }
                        },
                        "settings": {
                            "number_of_shards": 1,
                            "number_of_replicas": 0
                        }
                    }
                )
                logger.info("✅ [OPENSEARCH] Created 'calls' index")
            
            # Transcripts index
            if not self.client.indices.exists(index="transcripts"):
                self.client.indices.create(
                    index="transcripts",
                    body={
                        "mappings": {
                            "properties": {
                                "session_id": {"type": "keyword"},
                                "provider_call_id": {"type": "keyword"},
                                "tenant_id": {"type": "keyword"},
                                "speaker": {"type": "keyword"},
                                "text": {"type": "text"},
                                "timestamp": {"type": "date"},
                                "turn": {"type": "integer"}
                            }
                        },
                        "settings": {
                            "number_of_shards": 1,
                            "number_of_replicas": 0
                        }
                    }
                )
                logger.info("✅ [OPENSEARCH] Created 'transcripts' index")
            
            # Events index
            if not self.client.indices.exists(index="call-events"):
                self.client.indices.create(
                    index="call-events",
                    body={
                        "mappings": {
                            "properties": {
                                "session_id": {"type": "keyword"},
                                "provider_call_id": {"type": "keyword"},
                                "tenant_id": {"type": "keyword"},
                                "event_type": {"type": "keyword"},
                                "timestamp": {"type": "date"},
                                "turn": {"type": "integer"},
                                "data": {"type": "object"}
                            }
                        },
                        "settings": {
                            "number_of_shards": 1,
                            "number_of_replicas": 0
                        }
                    }
                )
                logger.info("✅ [OPENSEARCH] Created 'call-events' index")
                
        except Exception as e:
            logger.error(f"❌ [OPENSEARCH] Index initialization failed: {e}")

    async def index_call(self, call_data: Dict[str, Any]) -> bool:
        """
        Index a call record
        
        Args:
            call_data: Call session data
            
        Returns:
            True if successful
        """
        try:
            doc_id = call_data.get("provider_call_id", call_data.get("session_id"))
            
            self.client.index(
                index="calls",
                id=doc_id,
                body=call_data,
                refresh=True
            )
            
            logger.info(f"✅ [OPENSEARCH] Indexed call: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ [OPENSEARCH] Failed to index call: {e}")
            return False

    async def index_transcript_entry(
        self,
        session_id: str,
        provider_call_id: str,
        tenant_id: str,
        speaker: str,
        text: str,
        timestamp: str,
        turn: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Index a transcript entry
        
        Args:
            session_id: Voice OS session ID
            provider_call_id: Provider call ID (Telnyx/Twilio)
            tenant_id: Tenant ID
            speaker: Speaker (ai or caller)
            text: Transcript text
            timestamp: ISO timestamp
            turn: Conversation turn number
            metadata: Optional metadata dict (segments, confidence, etc.)
            
        Returns:
            True if successful
        """
        try:
            doc = {
                "session_id": session_id,
                "provider_call_id": provider_call_id,
                "tenant_id": tenant_id,
                "speaker": speaker,
                "text": text,
                "timestamp": timestamp,
                "turn": turn
            }
            
            # Add optional metadata
            if metadata:
                doc.update(metadata)
            
            self.client.index(
                index="transcripts",
                body=doc,
                refresh=True
            )
            
            logger.info(f"✅ [OPENSEARCH] Indexed transcript entry for {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ [OPENSEARCH] Failed to index transcript: {e}")
            return False

    async def index_event(
        self,
        session_id: str,
        provider_call_id: str,
        tenant_id: str,
        event_type: str,
        timestamp: str,
        turn: int,
        data: Dict[str, Any]
    ) -> bool:
        """
        Index a call event (machine detection, speaking started, DTMF, etc.)
        
        Args:
            session_id: Voice OS session ID
            provider_call_id: Provider call ID
            tenant_id: Tenant ID
            event_type: Type of event
            timestamp: ISO timestamp
            turn: Conversation turn
            data: Event-specific data
            
        Returns:
            True if successful
        """
        try:
            doc = {
                "session_id": session_id,
                "provider_call_id": provider_call_id,
                "tenant_id": tenant_id,
                "event_type": event_type,
                "timestamp": timestamp,
                "turn": turn,
                "data": data
            }
            
            self.client.index(
                index="call-events",
                body=doc,
                refresh=True
            )
            
            logger.info(f"✅ [OPENSEARCH] Indexed event '{event_type}' for {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ [OPENSEARCH] Failed to index event: {e}")
            return False

    async def search_transcripts(
        self,
        tenant_id: str,
        query: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Full-text search transcripts
        
        Args:
            tenant_id: Filter by tenant
            query: Search query text
            limit: Result limit
            
        Returns:
            List of matching transcripts
        """
        try:
            body = {
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"text": query}},
                            {"term": {"tenant_id": tenant_id}}
                        ]
                    }
                },
                "size": limit,
                "sort": [{"timestamp": {"order": "desc"}}]
            }
            
            response = self.client.search(index="transcripts", body=body)
            
            hits = response.get("hits", {}).get("hits", [])
            results = [hit["_source"] for hit in hits]
            
            logger.info(f"✅ [OPENSEARCH] Found {len(results)} transcripts matching '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"❌ [OPENSEARCH] Transcript search failed: {e}")
            return []

    async def get_call_transcript(self, provider_call_id: str) -> List[Dict[str, Any]]:
        """
        Get all transcript entries for a call
        
        Args:
            provider_call_id: Provider call ID
            
        Returns:
            List of transcript entries
        """
        try:
            body = {
                "query": {
                    "term": {"provider_call_id": provider_call_id}
                },
                "sort": [{"turn": {"order": "asc"}}, {"timestamp": {"order": "asc"}}],
                "size": 1000
            }
            
            response = self.client.search(index="transcripts", body=body)
            
            hits = response.get("hits", {}).get("hits", [])
            results = [hit["_source"] for hit in hits]
            
            logger.info(f"✅ [OPENSEARCH] Retrieved {len(results)} transcript entries")
            return results
            
        except Exception as e:
            logger.error(f"❌ [OPENSEARCH] Failed to retrieve transcript: {e}")
            return []

    async def get_call_events(self, provider_call_id: str) -> List[Dict[str, Any]]:
        """
        Get all events for a call
        
        Args:
            provider_call_id: Provider call ID
            
        Returns:
            List of events
        """
        try:
            body = {
                "query": {
                    "term": {"provider_call_id": provider_call_id}
                },
                "sort": [{"timestamp": {"order": "asc"}}],
                "size": 1000
            }
            
            response = self.client.search(index="call-events", body=body)
            
            hits = response.get("hits", {}).get("hits", [])
            results = [hit["_source"] for hit in hits]
            
            logger.info(f"✅ [OPENSEARCH] Retrieved {len(results)} events")
            return results
            
        except Exception as e:
            logger.error(f"❌ [OPENSEARCH] Failed to retrieve events: {e}")
            return []

    async def get_tenant_calls(
        self,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get recent calls for a tenant
        
        Args:
            tenant_id: Tenant ID
            limit: Number of results
            offset: Pagination offset
            
        Returns:
            List of calls
        """
        try:
            body = {
                "query": {
                    "term": {"tenant_id": tenant_id}
                },
                "sort": [{"created_at": {"order": "desc"}}],
                "size": limit,
                "from": offset
            }
            
            response = self.client.search(index="calls", body=body)
            
            hits = response.get("hits", {}).get("hits", [])
            results = [hit["_source"] for hit in hits]
            total = response.get("hits", {}).get("total", {}).get("value", 0)
            
            logger.info(f"✅ [OPENSEARCH] Retrieved {len(results)}/{total} calls for {tenant_id}")
            return results
            
        except Exception as e:
            logger.error(f"❌ [OPENSEARCH] Failed to retrieve tenant calls: {e}")
            return []

    async def get_call_metrics(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get aggregated metrics for a tenant
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Aggregated metrics
        """
        try:
            body = {
                "query": {
                    "term": {"tenant_id": tenant_id}
                },
                "aggs": {
                    "total_calls": {"value_count": {"field": "session_id"}},
                    "avg_duration": {"avg": {"field": "duration_seconds"}},
                    "total_turns": {"sum": {"field": "turn_count"}},
                    "calls_by_state": {"terms": {"field": "state", "size": 10}},
                    "calls_by_provider": {"terms": {"field": "provider", "size": 10}}
                }
            }
            
            response = self.client.search(index="calls", body=body)
            aggs = response.get("aggregations", {})
            
            metrics = {
                "total_calls": aggs.get("total_calls", {}).get("value", 0),
                "avg_duration_seconds": round(aggs.get("avg_duration", {}).get("value", 0), 2),
                "total_turns": int(aggs.get("total_turns", {}).get("value", 0)),
                "by_state": aggs.get("calls_by_state", {}).get("buckets", []),
                "by_provider": aggs.get("calls_by_provider", {}).get("buckets", [])
            }
            
            logger.info(f"✅ [OPENSEARCH] Computed metrics for {tenant_id}")
            return metrics
            
        except Exception as e:
            logger.error(f"❌ [OPENSEARCH] Failed to compute metrics: {e}")
            return {}


# Global OpenSearch instance
_opensearch_client: Optional[OpenSearchClient] = None


def get_opensearch_client() -> OpenSearchClient:
    """Get or create global OpenSearch client"""
    global _opensearch_client
    if _opensearch_client is None:
        _opensearch_client = OpenSearchClient()
    return _opensearch_client
