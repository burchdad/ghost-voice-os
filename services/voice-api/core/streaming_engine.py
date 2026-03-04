"""
Streaming Conversation Engine
Orchestrates streaming STT, LLM, and TTS for low-latency conversations
"""

import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime

from core.call_session import CallSession
from providers.streaming.stt_base import StreamingSTTProvider
from providers.streaming.llm_base import StreamingLLMProvider
from providers.streaming.tts_base import StreamingTTSProvider

logger = logging.getLogger(__name__)


class StreamingConversationEngine:
    """
    Low-latency streaming orchestrator for voice conversations.
    
    Pipeline:
    audio_stream → STT (streaming) → LLM (streaming) → TTS (streaming) → audio_out
    """

    def __init__(
        self,
        stt_provider: StreamingSTTProvider,
        llm_provider: StreamingLLMProvider,
        tts_provider: StreamingTTSProvider,
    ):
        self.stt_provider = stt_provider
        self.llm_provider = llm_provider
        self.tts_provider = tts_provider

    async def process_call_stream(
        self,
        session: CallSession,
        audio_stream: AsyncGenerator[bytes, None],
        system_prompt: Optional[str] = None,
        language: str = "en-US",
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process incoming audio stream end-to-end.

        Yields metadata about pipeline progress and audio chunks.
        """
        try:
            logger.info(
                f"🎯 Starting streaming call processing for session {session.session_id}"
            )

            conversation_state = {
                "turn": 0,
                "transcript_buffer": "",
                "llm_response_buffer": "",
                "total_duration_ms": 0,
            }

            # Phase 1: Stream STT
            transcription_queue = asyncio.Queue()
            llm_input_queue = asyncio.Queue()

            async def stt_task():
                """Convert audio stream to text"""
                logger.info("📍 STT phase starting")
                try:
                    async for transcription in self.stt_provider.stream_transcribe(
                        audio_stream, language=language
                    ):
                        if transcription.get("type") == "error":
                            yield {"type": "error", "phase": "stt", "error": transcription["error"]}
                        elif transcription.get("type") == "final":
                            logger.info(f"✅ Final transcript: {transcription['text']}")
                            conversation_state["transcript_buffer"] = transcription["text"]
                            await transcription_queue.put(transcription)
                            # Send final transcript to client
                            yield {
                                "type": "transcript",
                                "text": transcription["text"],
                                "confidence": transcription.get("confidence", 0),
                                "is_final": True,
                            }
                        else:
                            logger.info(f"📝 Interim: {transcription['text']}")
                            # Send interim transcripts
                            yield {
                                "type": "transcript",
                                "text": transcription["text"],
                                "is_final": False,
                            }
                except Exception as e:
                    logger.error(f"STT error: {e}", exc_info=True)
                    yield {"type": "error", "phase": "stt", "error": str(e)}
                finally:
                    await transcription_queue.put(None)  # Signal completion

            # Phase 2: Stream LLM
            async def llm_task():
                """Generate LLM response from transcript"""
                logger.info("📍 LLM phase waiting for transcript")
                try:
                    # Wait for complete transcript
                    transcript_item = await transcription_queue.get()
                    if transcript_item is None:
                        logger.warning("No transcript received")
                        await llm_input_queue.put(None)
                        return

                    user_input = transcript_item["text"]
                    conversation_state["turn"] += 1

                    # Build system prompt
                    if not system_prompt:
                        system_prompt = self._build_system_prompt(session)

                    logger.info(f"🤖 LLM generating response to: {user_input[:50]}")

                    # Stream LLM response
                    response_text = ""
                    async for llm_chunk in self.llm_provider.stream_generate(
                        prompt=user_input,
                        system_prompt=system_prompt,
                        conversation_history=session.conversation_history or [],
                    ):
                        if llm_chunk.get("type") == "error":
                            yield {"type": "error", "phase": "llm", "error": llm_chunk["content"]}
                        elif llm_chunk.get("type") == "content":
                            response_text += llm_chunk["content"]
                            # Feed to TTS immediately (streaming)
                            await llm_input_queue.put(llm_chunk["content"])
                        elif llm_chunk.get("type") == "stop":
                            logger.info(f"✅ LLM complete: {len(response_text)} chars")

                    conversation_state["llm_response_buffer"] = response_text
                    await llm_input_queue.put(None)  # Signal completion

                except Exception as e:
                    logger.error(f"LLM error: {e}", exc_info=True)
                    yield {"type": "error", "phase": "llm", "error": str(e)}
                    await llm_input_queue.put(None)

            # Phase 3: Stream TTS
            async def tts_task():
                """Convert LLM response to audio"""
                logger.info("📍 TTS phase waiting for LLM output")
                try:
                    # Create text stream from LLM queue
                    async def text_stream_gen():
                        while True:
                            text_chunk = await llm_input_queue.get()
                            if text_chunk is None:
                                break
                            yield text_chunk

                    voice_config = (
                        session.voice_config or {}
                    )
                    voice_id = voice_config.get("voice_id", "default")

                    logger.info(f"🔊 TTS generating audio with voice: {voice_id}")

                    # Stream audio playback
                    chunk_count = 0
                    async for audio_chunk in self.tts_provider.stream_synthesize(
                        text_stream_gen(), voice_id=voice_id, language=language
                    ):
                        chunk_count += 1
                        if audio_chunk.get("type") == "error":
                            yield {
                                "type": "error",
                                "phase": "tts",
                                "error": audio_chunk["error"],
                            }
                        elif audio_chunk.get("type") == "audio_chunk":
                            yield {
                                "type": "audio",
                                "audio_data": audio_chunk["audio_data"],
                                "duration_ms": audio_chunk.get("duration_ms", 50),
                            }

                    logger.info(f"✅ TTS complete ({chunk_count} chunks)")

                except Exception as e:
                    logger.error(f"TTS error: {e}", exc_info=True)
                    yield {"type": "error", "phase": "tts", "error": str(e)}

            # Run all phases concurrently
            stt_gen = stt_task()
            llm_gen = llm_task()
            tts_gen = tts_task()

            # Interleave all generators
            tasks = {
                "stt": asyncio.create_task(stt_gen.__anext__()),
                "llm": asyncio.create_task(llm_gen.__anext__()),
                "tts": asyncio.create_task(tts_gen.__anext__()),
            }

            while tasks:
                done, _ = await asyncio.wait(
                    tasks.values(), return_when=asyncio.FIRST_COMPLETED
                )

                for phase, task in list(tasks.items()):
                    if task in done:
                        try:
                            result = task.result()
                            if result is not None:
                                yield result

                            # Get next item from this phase
                            if phase == "stt":
                                tasks[phase] = asyncio.create_task(stt_gen.__anext__())
                            elif phase == "llm":
                                tasks[phase] = asyncio.create_task(llm_gen.__anext__())
                            elif phase == "tts":
                                tasks[phase] = asyncio.create_task(tts_gen.__anext__())
                        except StopAsyncIteration:
                            del tasks[phase]
                        except Exception as e:
                            logger.error(f"Phase {phase} error: {e}")
                            del tasks[phase]

            logger.info(f"✅ Call stream complete: {conversation_state}")

        except Exception as e:
            logger.error(f"❌ Stream processing error: {e}", exc_info=True)
            yield {"type": "error", "phase": "general", "error": str(e)}

    def _build_system_prompt(self, session: CallSession) -> str:
        """Build system prompt from session config"""
        ai_config = session.ai_config or {}
        prompt = ai_config.get(
            "prompt",
            "You are a helpful AI assistant. Be concise and conversational.",
        )
        personality = ai_config.get("personality_mode", "professional")
        return f"{prompt}\n\nPersonality: {personality}"
