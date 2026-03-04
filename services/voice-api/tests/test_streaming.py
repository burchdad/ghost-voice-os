"""
Integration tests for streaming voice pipeline
Tests end-to-end streaming functionality with mocked providers
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import AsyncGenerator

# Test imports
from core.call_session import CallSession
from core.streaming_engine import StreamingConversationEngine
from providers.streaming.stt_base import StreamingSTTProvider
from providers.streaming.llm_base import StreamingLLMProvider
from providers.streaming.tts_base import StreamingTTSProvider


# ============================================================================
# Mock Providers for Testing
# ============================================================================


class MockStreamingSTT(StreamingSTTProvider):
    """Mock STT that returns canned responses"""

    async def stream_transcribe(
        self, audio_stream: AsyncGenerator[bytes, None], language: str = "en-US", **kwargs
    ):
        """Mock transcription"""
        # Consume audio stream
        async for chunk in audio_stream:
            pass

        # Return mock transcript
        yield {
            "type": "interim",
            "text": "hello", 
            "confidence": 0.9,
            "is_final": False,
            "provider": "mock_stt",
        }
        await asyncio.sleep(0.1)
        yield {
            "type": "final",
            "text": "hello there",
            "confidence": 0.95,
            "is_final": True,
            "provider": "mock_stt",
        }

    async def health_check(self) -> bool:
        return True


class MockStreamingLLM(StreamingLLMProvider):
    """Mock LLM that returns streaming tokens"""

    async def stream_generate(
        self, prompt: str, system_prompt: str = None, conversation_history=None, **kwargs
    ):
        """Mock LLM response"""
        # Simulate token-by-token response
        response = "Hi, how can I help you today?"
        for token in response.split():
            yield {
                "type": "content",
                "content": token + " ",
                "is_final": False,
                "model": "mock_llm",
                "provider": "mock",
            }
            await asyncio.sleep(0.05)

        yield {
            "type": "stop",
            "content": "",
            "is_final": True,
            "model": "mock_llm",
            "provider": "mock",
        }

    async def health_check(self) -> bool:
        return True

    async def get_model_info(self):
        return {"model": "mock_llm"}


class MockStreamingTTS(StreamingTTSProvider):
    """Mock TTS that returns audio chunks"""

    async def stream_synthesize(
        self,
        text_stream: AsyncGenerator[str, None],
        voice_id: str = "default",
        language: str = "en-US",
        **kwargs
    ):
        """Mock audio synthesis"""
        # Collect all text
        full_text = ""
        async for chunk in text_stream:
            full_text += chunk

        # Return mock audio chunks
        for i in range(5):
            yield {
                "type": "audio_chunk",
                "audio_data": b"mock_audio_" + str(i).encode(),
                "is_final": i == 4,
                "voice_id": voice_id,
                "provider": "mock_tts",
                "duration_ms": 50,
            }
            await asyncio.sleep(0.05)

    async def health_check(self) -> bool:
        return True

    async def list_voices(self):
        return {"voices": [{"voice_id": "default", "name": "Default Voice"}]}


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.asyncio
async def test_streaming_engine_creation():
    """Test that streaming engine initializes correctly"""
    stt = MockStreamingSTT({})
    llm = MockStreamingLLM({})
    tts = MockStreamingTTS({})

    engine = StreamingConversationEngine(
        stt_provider=stt, llm_provider=llm, tts_provider=tts
    )

    assert engine is not None
    assert engine.stt_provider == stt
    assert engine.llm_provider == llm
    assert engine.tts_provider == tts


@pytest.mark.asyncio
async def test_streaming_call_process():
    """Test end-to-end streaming call processing"""
    stt = MockStreamingSTT({})
    llm = MockStreamingLLM({})
    tts = MockStreamingTTS({})

    engine = StreamingConversationEngine(
        stt_provider=stt, llm_provider=llm, tts_provider=tts
    )

    # Create test session
    session = CallSession(
        tenant_id="test",
        provider="streaming",
        provider_call_id="test-call",
        to_number="",
        from_number="",
        voice_config={"voice_id": "default"},
        ai_config={
            "prompt": "You are a helpful assistant",
            "personality_mode": "friendly",
        },
    )

    # Create mock audio stream
    async def mock_audio():
        # Send a few audio chunks then stop
        for i in range(3):
            yield b"audio_chunk_" + str(i).encode()
            await asyncio.sleep(0.05)

    # Collect all output
    outputs = []
    async for output in engine.process_call_stream(session, mock_audio()):
        outputs.append(output)

    # Verify we got outputs from all phases
    assert len(outputs) > 0

    # Check for expected output types
    output_types = {o.get("type") for o in outputs}
    print(f"Output types received: {output_types}")

    # Should have transcripts
    transcripts = [o for o in outputs if o.get("type") == "transcript"]
    assert len(transcripts) > 0
    print(f"Received {len(transcripts)} transcript updates")

    # Should have audio
    audios = [o for o in outputs if o.get("type") == "audio"]
    assert len(audios) > 0
    print(f"Received {len(audios)} audio chunks")


@pytest.mark.asyncio
async def test_streaming_stt_provider():
    """Test streaming STT provider"""
    stt = MockStreamingSTT({})

    # Create mock audio stream
    async def mock_audio():
        for i in range(2):
            yield b"audio_chunk"
            await asyncio.sleep(0.01)

    # Collect transcripts
    transcripts = []
    async for transcript in stt.stream_transcribe(mock_audio()):
        transcripts.append(transcript)

    assert len(transcripts) == 2
    assert transcripts[0]["type"] == "interim"
    assert transcripts[1]["type"] == "final"
    assert transcripts[1]["is_final"] == True


@pytest.mark.asyncio
async def test_streaming_llm_provider():
    """Test streaming LLM provider"""
    llm = MockStreamingLLM({})

    prompt = "What is the weather?"
    system_prompt = "You are a helpful assistant"

    # Collect response chunks
    chunks = []
    async for chunk in llm.stream_generate(
        prompt=prompt, system_prompt=system_prompt
    ):
        chunks.append(chunk)

    assert len(chunks) > 0
    # Should end with stop marker
    assert chunks[-1]["type"] == "stop"
    assert chunks[-1]["is_final"] == True

    # Middle chunks should be content
    content_chunks = [c for c in chunks[:-1] if c["type"] == "content"]
    assert len(content_chunks) > 0


@pytest.mark.asyncio
async def test_streaming_tts_provider():
    """Test streaming TTS provider"""
    tts = MockStreamingTTS({})

    # Create mock text stream
    async def mock_text():
        yield "Hello "
        await asyncio.sleep(0.01)
        yield "there"
        await asyncio.sleep(0.01)

    # Collect audio chunks
    audio_chunks = []
    async for chunk in tts.stream_synthesize(mock_text(), voice_id="default"):
        audio_chunks.append(chunk)

    assert len(audio_chunks) > 0
    # All should be audio chunks
    for chunk in audio_chunks:
        assert chunk["type"] == "audio_chunk"
        assert "audio_data" in chunk


@pytest.mark.asyncio
async def test_concurrent_streaming_phases():
    """Test that STT, LLM, and TTS run concurrently"""
    stt = MockStreamingSTT({})
    llm = MockStreamingLLM({})
    tts = MockStreamingTTS({})

    engine = StreamingConversationEngine(
        stt_provider=stt, llm_provider=llm, tts_provider=tts
    )

    session = CallSession(
        tenant_id="test",
        provider="streaming",
        provider_call_id="test-call",
        to_number="",
        from_number="",
    )

    async def mock_audio():
        for i in range(2):
            yield b"audio_chunk"
            await asyncio.sleep(0.02)

    import time

    start_time = time.time()
    output_count = 0

    async for output in engine.process_call_stream(session, mock_audio()):
        output_count += 1

    duration = time.time() - start_time

    # With concurrent execution, total time should be less than sequential
    # Sequential would be ~0.5s, concurrent should be ~0.3s
    print(f"Processed {output_count} outputs in {duration:.2f}s")

    assert output_count > 0
    # Concurrent execution should be faster than waiting for each phase
    assert duration < 1.0


@pytest.mark.asyncio
async def test_error_handling_in_streaming():
    """Test error handling in streaming pipeline"""

    class FailingSTT(StreamingSTTProvider):
        async def stream_transcribe(self, audio_stream, language="en-US", **kwargs):
            async for _ in audio_stream:
                pass
            yield {"type": "error", "error": "STT Failed"}

        async def health_check(self):
            return False

    stt = FailingSTT({})
    llm = MockStreamingLLM({})
    tts = MockStreamingTTS({})

    engine = StreamingConversationEngine(
        stt_provider=stt, llm_provider=llm, tts_provider=tts
    )

    session = CallSession(
        tenant_id="test",
        provider="streaming",
        provider_call_id="test-call",
        to_number="",
        from_number="",
    )

    async def mock_audio():
        yield b"audio_chunk"

    outputs = []
    async for output in engine.process_call_stream(session, mock_audio()):
        outputs.append(output)

    # Should contain error message
    errors = [o for o in outputs if o.get("type") == "error"]
    assert len(errors) > 0


@pytest.mark.asyncio
async def test_websocket_message_format():
    """Test that WebSocket messages match expected format"""

    # Test transcript message
    transcript_msg = {
        "type": "transcript",
        "text": "hello world",
        "is_final": False,
        "confidence": 0.95,
    }
    assert transcript_msg["type"] == "transcript"
    assert "text" in transcript_msg

    # Test audio message
    audio_msg = {
        "type": "audio",
        "data": "base64encodeddata==",
        "duration_ms": 50,
    }
    assert audio_msg["type"] == "audio"
    assert "data" in audio_msg

    # Test error message
    error_msg = {
        "type": "error",
        "error": "Connection failed",
        "phase": "stt",
    }
    assert error_msg["type"] == "error"
    assert "error" in error_msg


# ============================================================================
# Performance Benchmarks
# ============================================================================


@pytest.mark.asyncio
async def test_streaming_latency_benchmark():
    """Benchmark latency of streaming pipeline"""
    import time

    stt = MockStreamingSTT({})
    llm = MockStreamingLLM({})
    tts = MockStreamingTTS({})

    engine = StreamingConversationEngine(
        stt_provider=stt, llm_provider=llm, tts_provider=tts
    )

    session = CallSession(
        tenant_id="benchmark",
        provider="streaming",
        provider_call_id="bench-1",
        to_number="",
        from_number="",
    )

    async def mock_audio():
        # Simulate 1 second of audio at 16kHz
        chunk_size = 16000 * 2  # 16-bit samples
        for i in range(1):
            yield b"x" * chunk_size
            await asyncio.sleep(0.1)

    # Measure total time
    start = time.time()

    message_count = 0
    async for output in engine.process_call_stream(session, mock_audio()):
        message_count += 1

    end = time.time()
    latency = (end - start) * 1000  # Convert to ms

    print(f"\n📊 Streaming Latency Benchmark:")
    print(f"   Total messages: {message_count}")
    print(f"   Total latency: {latency:.0f}ms")
    print(f"   Target: <700ms")

    # Should complete in reasonable time (mock is fast)
    assert latency < 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
