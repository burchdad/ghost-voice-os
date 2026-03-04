"""
Base Streaming LLM Provider Interface
All streaming LLM providers implement this for agent responses
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, AsyncGenerator


class StreamingLLMProvider(ABC):
    """Abstract base class for Streaming Large Language Model providers"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate LLM response with streaming output.

        Args:
            prompt: User input
            system_prompt: System instructions
            conversation_history: Previous messages
            **kwargs: Provider-specific options

        Yields:
            {
                "type": "content" | "error" | "stop",
                "content": "text chunk or error message",
                "is_final": False | True,
                "timestamp": 1234567890,
                "model": "gpt-4",
                "provider": "openai"
            }
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is healthy"""
        pass

    @abstractmethod
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded model"""
        pass
