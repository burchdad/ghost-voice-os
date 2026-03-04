"""
Deepgram Streaming STT Implementation
Real-time speech-to-text with streaming capabilities
"""

import asyncio
import logging
from typing import Optional, Dict, Any, AsyncGenerator
import os
import json

try:
    from deepgram import DeepgramClient, LiveTranscriptionEvents
    DEEPGRAM_AVAILABLE = True
except ImportError:
    DEEPGRAM_AVAILABLE = False

from providers.streaming.stt_base import StreamingSTTProvider

logger = logging.getLogger(__name__)


class DeepgramStreamingSTT(StreamingSTTProvider):
    """Deepgram streaming speech-to-text provider"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        if not DEEPGRAM_AVAILABLE:
            raise RuntimeError("deepgram-sdk not installed. Install with: pip install deepgram-sdk")

        self.api_key = config.get("api_key") or os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            raise ValueError("Deepgram API key not found in config or DEEPGRAM_API_KEY env var")

        self.client = DeepgramClient(api_key=self.api_key)
        self.model = config.get("model", "nova-2")
        self.language = config.get("language", "en-US")

    async def stream_transcribe(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        language: str = "en-US",
        interim_results: bool = True,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream audio chunks to Deepgram and yield transcription updates.
        """
        try:
            # Prepare Deepgram options
            options = {
                "model": self.model,
                "language": language or self.language,
                "interim_results": interim_results,
                "encoding": "linear16",
                "sample_rate": 16000,
            }

            # Add custom options from kwargs
            for key in ["punctuation", "profanity_filter", "numerals"]:
                if key in kwargs:
                    options[key] = kwargs[key]

            logger.info(f"🎤 Deepgram streaming started with options: {options}")

            # Create live transcription connection
            dg_connection = self.client.listen.live.v(
                {
                    "model": options["model"],
                    "language": options["language"],
                    "interim_results": options["interim_results"],
                    "encoding": options["encoding"],
                    "sample_rate": options["sample_rate"],
                }
            )

            # Set up event handlers
            transcript_queue = asyncio.Queue()
            error_occurred = False
            error_message = None

            def on_message(self, result, **kwargs):
                """Handle transcription results"""
                try:
                    if result.speech_final:
                        # Final transcript
                        transcript = result.channel.alternatives[0].transcript
                        confidence = result.channel.alternatives[0].confidence
                        asyncio.create_task(
                            transcript_queue.put({
                                "type": "final",
                                "text": transcript,
                                "confidence": confidence,
                                "is_final": True,
                                "provider": "deepgram",
                            })
                        )
                    else:
                        # Interim transcript
                        transcript = result.channel.alternatives[0].transcript
                        confidence = result.channel.alternatives[0].confidence
                        asyncio.create_task(
                            transcript_queue.put({
                                "type": "interim",
                                "text": transcript,
                                "confidence": confidence,
                                "is_final": False,
                                "provider": "deepgram",
                            })
                        )
                except Exception as e:
                    logger.error(f"Error in on_message: {e}")

            def on_error(self, error, **kwargs):
                """Handle connection errors"""
                nonlocal error_occurred, error_message
                error_occurred = True
                error_message = str(error)
                logger.error(f"🔴 Deepgram error: {error}")

            def on_close(self, close, **kwargs):
                """Handle connection close"""
                logger.info("🔵 Deepgram connection closed")

            # Attach event handlers
            dg_connection.on(LiveTranscriptionEvents.Open, lambda x: logger.info("✅ Deepgram connection opened"))
            dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
            dg_connection.on(LiveTranscriptionEvents.Error, on_error)
            dg_connection.on(LiveTranscriptionEvents.Close, on_close)

            # Start the connection
            if not await asyncio.wait_for(dg_connection.start(), timeout=5.0):
                raise RuntimeError("Failed to start Deepgram connection")

            # Send audio and collect transcripts
            async def send_audio():
                try:
                    async for chunk in audio_stream:
                        if error_occurred:
                            break
                        await dg_connection.send(chunk)
                        await asyncio.sleep(0.01)  # Small delay between chunks
                except Exception as e:
                    logger.error(f"Error sending audio: {e}")
                finally:
                    await asyncio.sleep(0.1)
                    await dg_connection.finish()

            # Send audio in background
            send_task = asyncio.create_task(send_audio())

            # Yield results until connection closes
            while not send_task.done() or not transcript_queue.empty():
                try:
                    result = await asyncio.wait_for(
                        transcript_queue.get(),
                        timeout=1.0
                    )
                    yield result
                except asyncio.TimeoutError:
                    if send_task.done():
                        break
                    continue
                except Exception as e:
                    logger.error(f"Error yielding result: {e}")
                    break

            await send_task

            if error_occurred:
                yield {
                    "type": "error",
                    "error": error_message,
                    "provider": "deepgram",
                }

        except Exception as e:
            logger.error(f"❌ Deepgram stream_transcribe error: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e),
                "provider": "deepgram",
            }

    async def health_check(self) -> bool:
        """Check if Deepgram API is accessible"""
        try:
            # Simple health check - try to list available models
            # Deepgram doesn't have a explicit health endpoint, so we verify API key works
            await asyncio.sleep(0)  # Async checkpoint
            return bool(self.api_key)
        except Exception as e:
            logger.error(f"Deepgram health check failed: {e}")
            return False
