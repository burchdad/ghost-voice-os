"""
Conversation Engine
Unified LLM and TTS orchestration for call handling
"""

import logging
from typing import Dict, Any, Optional, Tuple
import os
from core.call_session import CallSession

logger = logging.getLogger(__name__)


class ConversationEngine:
    """
    Orchestrates LLM responses and TTS audio generation
    Pluggable architecture supporting multiple LLM and TTS providers
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize conversation engine
        
        Args:
            base_url: Base URL for voice synthesis API
        """
        self.base_url = base_url

    async def generate_response(
        self,
        session: CallSession,
        caller_input: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Generate AI response to caller input
        
        Returns:
            (response_text, audio_url)
        """
        try:
            # Build prompt context
            system_prompt = self._build_system_prompt(session)
            user_message = caller_input or "Start the conversation"
            
            # Get LLM response (placeholder - integrate with OpenAI/Claude)
            response_text = await self._call_llm(
                system_prompt=system_prompt,
                user_message=user_message,
                tenant_id=session.tenant_id,
                context=session.ai_config
            )
            
            # Generate audio from response
            audio_url = await self._synthesize_audio(
                text=response_text,
                session=session
            )
            
            logger.info(f"✅ [CONVERSATION] Generated response for {session.session_id}")
            return response_text, audio_url
            
        except Exception as e:
            logger.error(f"❌ [CONVERSATION] Failed to generate response: {e}")
            return "I'm sorry, I encountered an error. Please try again.", ""

    def _build_system_prompt(self, session: CallSession) -> str:
        """Build system prompt with tenant and session context"""
        base_prompt = session.ai_config.get(
            "prompt",
            "You are a helpful AI assistant for customer support."
        )
        
        personality = session.ai_config.get("personality_mode", "professional")
        prompt = f"{base_prompt}\n\nPersonality: {personality}\n"
        
        if session.lead_data:
            prompt += f"Customer: {session.lead_data.get('name', 'Guest')}\n"
        
        prompt += f"Call turn: {session.turn_count}\n"
        
        return prompt

    async def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
        tenant_id: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Call LLM provider (OpenAI, Claude, etc.)
        Placeholder - implement based on your LLM preference
        
        Args:
            system_prompt: System prompt for LLM
            user_message: User input
            tenant_id: Tenant for multi-tenant routing
            context: AI configuration context
            
        Returns:
            Response text from LLM
        """
        try:
            # TODO: Integrate with your LLM provider
            # For now, return a simple response
            
            # Example with OpenAI (when implemented):
            # import openai
            # response = await openai.ChatCompletion.acreate(
            #     model="gpt-4",
            #     messages=[
            #         {"role": "system", "content": system_prompt},
            #         {"role": "user", "content": user_message}
            #     ],
            #     temperature=0.7,
            #     max_tokens=150
            # )
            # return response.choices[0].message.content
            
            # Placeholder response
            logger.info(f"📞 [LLM] Processing: {user_message[:50]}...")
            return f"Thank you for that input. How can I help you further?"
            
        except Exception as e:
            logger.error(f"❌ [LLM] LLM call failed: {e}")
            raise

    async def _synthesize_audio(
        self,
        text: str,
        session: CallSession
    ) -> str:
        """
        Synthesize text to speech using configured TTS provider
        
        Args:
            text: Text to synthesize
            session: Call session with voice config
            
        Returns:
            URL of synthesized audio
        """
        try:
            # Call local TTS synthesis endpoint
            import httpx
            
            payload = {
                "text": text,
                "voice_id": session.voice_config.get("voice_id", "sarah"),
                "voice_type": session.voice_config.get("voice_type", "primary"),
                "language": session.voice_config.get("language", "en-US")
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v1/voice/synthesize",
                    json=payload,
                    headers={"X-Tenant-Id": session.tenant_id},
                    timeout=15.0
                )
                
                if response.status_code != 200:
                    logger.error(f"❌ [TTS] Synthesis failed: {response.text}")
                    return ""
                
                # Response is audio bytes - in production, store to S3/CDN
                # For now, return a placeholder URL
                logger.info(f"✅ [TTS] Synthesized audio ({len(text)} chars)")
                return f"{self.base_url}/v1/voice/stream/{session.session_id}"
            
        except Exception as e:
            logger.error(f"❌ [TTS] Synthesis exception: {e}")
            return ""

    async def handle_dtmf_input(
        self,
        session: CallSession,
        digits: str
    ) -> Tuple[str, str]:
        """
        Handle DTMF digits from caller
        
        Args:
            session: Call session
            digits: Gathered DTMF digits
            
        Returns:
            (response_text, audio_url)
        """
        try:
            logger.info(f"📞 [DTMF] Received: {digits} for {session.session_id}")
            
            # Map digits to actions or pass to LLM
            response_text = f"You pressed {digits}. Processing your request..."
            audio_url = await self._synthesize_audio(response_text, session)
            
            return response_text, audio_url
            
        except Exception as e:
            logger.error(f"❌ [DTMF] Failed to handle DTMF: {e}")
            return "I didn't understand your input. Please try again.", ""

    async def handle_silence(
        self,
        session: CallSession
    ) -> Tuple[str, str]:
        """
        Handle silence (no input from caller)
        
        Args:
            session: Call session
            
        Returns:
            (response_text, audio_url)
        """
        try:
            logger.info(f"🤐 [SILENCE] Detected on {session.session_id}")
            
            # Generate prompt if caller is silent
            response_text = "Are you still there? Please respond."
            audio_url = await self._synthesize_audio(response_text, session)
            
            session.metrics["silence_count"] += 1
            
            return response_text, audio_url
            
        except Exception as e:
            logger.error(f"❌ [SILENCE] Failed to handle silence: {e}")
            return "", ""

    async def end_call(
        self,
        session: CallSession,
        reason: str = "completed"
    ) -> str:
        """
        Generate closing message when call ends
        
        Args:
            session: Call session
            reason: Reason for ending (completed, failed, timeout, etc.)
            
        Returns:
            Closing message
        """
        try:
            closing_messages = {
                "completed": "Thank you for calling. Have a great day!",
                "failed": "I apologize, but we experienced a technical issue.",
                "timeout": "The call has timed out. Thank you.",
                "hangup": "Thank you for calling. Goodbye!"
            }
            
            message = closing_messages.get(reason, "Thank you for calling.")
            
            logger.info(f"👋 [END_CALL] {session.session_id} ({reason})")
            return message
            
        except Exception as e:
            logger.error(f"❌ [END_CALL] Failed to generate closing: {e}")
            return "Goodbye."


def get_conversation_engine(base_url: Optional[str] = None) -> ConversationEngine:
    """Factory function for conversation engine"""
    base_url = base_url or os.getenv("VOICE_OS_BASE_URL", "http://localhost:8000")
    return ConversationEngine(base_url=base_url)
