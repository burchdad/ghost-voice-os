"""
OpenAI Streaming LLM Implementation
GPT responses with streaming token-by-token output
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, AsyncGenerator
import os

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from providers.streaming.llm_base import StreamingLLMProvider

logger = logging.getLogger(__name__)


class OpenAIStreamingLLM(StreamingLLMProvider):
    """OpenAI streaming LLM provider (GPT-4, GPT-3.5, etc.)"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        if not OPENAI_AVAILABLE:
            raise RuntimeError("openai not installed. Install with: pip install openai")

        self.api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found in config or OPENAI_API_KEY env var")

        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = config.get("model", "gpt-4")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 500)

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream LLM response token by token.
        """
        try:
            logger.info(f"🤖 OpenAI streaming generation started (model: {self.model})")

            # Build messages list
            messages = []

            # Add system prompt if provided
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history)

            # Add current prompt
            messages.append({"role": "user", "content": prompt})

            # Override with kwargs if provided
            model = kwargs.get("model", self.model)
            temperature = kwargs.get("temperature", self.temperature)
            max_tokens = kwargs.get("max_tokens", self.max_tokens)

            logger.info(f"Messages count: {len(messages)}")

            # Stream response
            full_response = ""
            async with await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            ) as stream:
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content

                        yield {
                            "type": "content",
                            "content": content,
                            "is_final": False,
                            "model": model,
                            "provider": "openai",
                        }

            logger.info(f"✅ OpenAI response complete ({len(full_response)} chars)")

            # Send final marker
            yield {
                "type": "stop",
                "content": "",
                "is_final": True,
                "model": model,
                "provider": "openai",
            }

        except Exception as e:
            logger.error(f"❌ OpenAI stream_generate error: {e}", exc_info=True)
            yield {
                "type": "error",
                "content": str(e),
                "provider": "openai",
            }

    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible"""
        try:
            # Make a minimal API call to verify credentials
            response = await self.client.models.list()
            return True
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False

    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the configured model"""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "provider": "openai",
        }
