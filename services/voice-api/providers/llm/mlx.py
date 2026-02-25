"""
MLX LLM Provider - Apple Silicon optimized LLM
"""

from typing import Optional, Dict, Any, List
from .base import LLMProvider


class MLXProvider(LLMProvider):
    """MLX framework for Apple Silicon LLMs"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model_name = config.get("model_name", "mlx-community/Llama-2-7b-chat")
        self.model = None
        self.tokenizer = None

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response using MLX"""
        try:
            if self.model is None:
                from mlx_lm import load, generate as mlx_generate

                self.model, self.tokenizer = load(self.model_name)

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            if conversation_history:
                messages.extend(conversation_history)

            messages.append({"role": "user", "content": prompt})

            # Format for MLX
            prompt_text = "\n".join(
                [f"{m['role']}: {m['content']}" for m in messages]
            )

            response = mlx_generate(
                self.model,
                self.tokenizer,
                prompt_text,
                temp=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 500),
            )

            return {
                "response": response,
                "model": self.model_name,
                "provider": "mlx",
            }

        except Exception as e:
            print(f"❌ MLX error: {e}")
            return {
                "provider": "mlx",
                "error": str(e),
            }

    async def health_check(self) -> bool:
        """Check if MLX is available"""
        try:
            import mlx_lm

            return True
        except ImportError:
            return False

    async def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "model_name": self.model_name,
            "provider": "mlx",
            "type": "local_apple_silicon",
        }
