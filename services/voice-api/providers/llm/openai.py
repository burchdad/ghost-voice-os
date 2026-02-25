"""
OpenAI LLM Provider - GPT-4, GPT-3.5-turbo
"""

from typing import Optional, Dict, Any, List
from .base import LLMProvider


class OpenAILLMProvider(LLMProvider):
    """OpenAI API integration"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.model = config.get("model", "gpt-4")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response using OpenAI API"""
        if not self.api_key:
            return {
                "provider": "openai",
                "error": "OpenAI API key not configured",
            }

        try:
            import openai

            openai.api_key = self.api_key

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            if conversation_history:
                messages.extend(conversation_history)

            messages.append({"role": "user", "content": prompt})

            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=messages,
                max_tokens=kwargs.get("max_tokens", 500),
                temperature=kwargs.get("temperature", 0.7),
            )

            return {
                "response": response.choices[0].message.content,
                "tokens_used": response.usage.total_tokens,
                "model": self.model,
                "provider": "openai",
            }

        except Exception as e:
            print(f"❌ OpenAI error: {e}")
            return {
                "provider": "openai",
                "error": str(e),
            }

    async def health_check(self) -> bool:
        """Check OpenAI API availability"""
        return bool(self.api_key)

    async def get_model_info(self) -> Dict[str, Any]:
        """Get OpenAI model information"""
        return {
            "model": self.model,
            "provider": "openai",
            "type": "cloud",
        }
