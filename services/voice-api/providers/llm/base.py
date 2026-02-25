"""
Base LLM Provider Interface
All LLM providers implement this for agent responses
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class LLMProvider(ABC):
    """Abstract base class for Large Language Model providers"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate LLM response

        Args:
            prompt: User input
            system_prompt: System instructions
            conversation_history: Previous messages
            **kwargs: Provider-specific options

        Returns:
            {
                "response": "generated text",
                "tokens_used": 150,
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
