"""
Llama.cpp LLM Provider - Local LLM inference
"""

from typing import Optional, Dict, Any, List
from .base import LLMProvider


class LlamaCppProvider(LLMProvider):
    """Llama.cpp local LLM inference"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model_path = config.get("model_path")
        self.n_ctx = config.get("n_ctx", 2048)
        self.cpp = None

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response using Llama.cpp"""
        try:
            if self.cpp is None:
                from llama_cpp import Llama

                self.cpp = Llama(self.model_path, n_ctx=self.n_ctx)

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            if conversation_history:
                messages.extend(conversation_history)

            messages.append({"role": "user", "content": prompt})

            response = self.cpp.create_chat_completion(
                messages=messages,
                max_tokens=kwargs.get("max_tokens", 500),
            )

            return {
                "response": response["choices"][0]["message"]["content"],
                "tokens_used": response["usage"]["total_tokens"],
                "model": self.model_path,
                "provider": "llama_cpp",
            }

        except Exception as e:
            print(f"❌ Llama.cpp error: {e}")
            return {
                "provider": "llama_cpp",
                "error": str(e),
            }

    async def health_check(self) -> bool:
        """Check if model is loaded"""
        return self.model_path is not None and self.cpp is not None

    async def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "model_path": self.model_path,
            "n_ctx": self.n_ctx,
            "provider": "llama_cpp",
            "type": "local",
        }
