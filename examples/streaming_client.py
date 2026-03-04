#!/usr/bin/env python3
"""
Streaming Voice API - Python Example
Demonstrates how to use the streaming API from a Python application
"""

import asyncio
import base64
import json
import websockets
from pathlib import Path


class StreamingVoiceExample:
    """Example client for Ghost Voice OS streaming API"""

    def __init__(self, ws_url: str, audio_file: str = None):
        """
        Initialize streaming client.
        
        Args:
            ws_url: WebSocket URL (e.g., ws://localhost:8000/v1/stream/ws/call/example-123)
            audio_file: Path to audio file to stream (for testing)
        """
        self.ws_url = ws_url
        self.audio_file = audio_file
        self.results = {
            "transcripts": [],
            "audio_chunks": [],
            "errors": [],
            "metadata": []
        }

    async def connect_and_stream(self):
        """Connect to streaming endpoint and send audio"""
        print(f"🔌 Connecting to {self.ws_url}")
        
        try:
            async with websockets.connect(self.ws_url) as websocket:
                print("✅ Connected to streaming server")
                
                # Start receiving task
                receive_task = asyncio.create_task(
                    self._receive_messages(websocket)
                )
                
                # Start sending task
                send_task = asyncio.create_task(
                    self._send_audio(websocket)
                )
                
                # Wait for both to complete
                await asyncio.gather(send_task, receive_task)
                
        except Exception as e:
            print(f"❌ Connection error: {e}")
            self.results["errors"].append(str(e))

    async def _send_audio(self, websocket):
        """Send audio chunks to server"""
        print("📤 Starting audio stream...")
        
        try:
            # Generate mock audio chunks (in production, read from microphone)
            if self.audio_file and Path(self.audio_file).exists():
                # Read actual audio file
                print(f"📁 Reading audio from {self.audio_file}")
                with open(self.audio_file, 'rb') as f:
                    audio_data = f.read()
                    
                    # Send in chunks
                    chunk_size = 4096
                    for i in range(0, len(audio_data), chunk_size):
                        chunk = audio_data[i:i+chunk_size]
                        
                        # Encode as base64
                        encoded = base64.b64encode(chunk).decode()
                        
                        # Send message
                        message = json.dumps({
                            "type": "audio",
                            "data": encoded
                        })
                        
                        await websocket.send(message)
                        print(f"  📦 Sent chunk {i//chunk_size + 1}: {len(chunk)} bytes")
                        
                        # Small delay between chunks
                        await asyncio.sleep(0.05)
            else:
                # Generate synthetic audio (silence with noise pattern)
                print("🎵 Generating synthetic audio...")
                import random
                
                for i in range(10):  # Send 10 chunks
                    # Create fake audio (mostly silence)
                    chunk = bytes([random.randint(0, 255) for _ in range(4096)])
                    encoded = base64.b64encode(chunk).decode()
                    
                    message = json.dumps({
                        "type": "audio",
                        "data": encoded
                    })
                    
                    await websocket.send(message)
                    print(f"  📦 Sent chunk {i+1}: 4096 bytes")
                    await asyncio.sleep(0.1)
            
            # Signal end of audio
            print("⏹️  Audio stream complete, sending stop signal")
            await websocket.send(json.dumps({
                "type": "control",
                "command": "stop"
            }))
            
        except Exception as e:
            print(f"❌ Error sending audio: {e}")
            self.results["errors"].append(f"Send error: {str(e)}")

    async def _receive_messages(self, websocket):
        """Receive messages from server"""
        print("👂 Listening for responses...")
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    self._handle_message(data)
                except json.JSONDecodeError:
                    print(f"⚠️  Invalid JSON received: {message[:100]}")
                    
        except websockets.exceptions.ConnectionClosed:
            print("🔌 Connection closed")
        except Exception as e:
            print(f"❌ Error receiving messages: {e}")
            self.results["errors"].append(f"Receive error: {str(e)}")

    def _handle_message(self, data: dict):
        """Handle incoming message"""
        msg_type = data.get("type")
        
        if msg_type == "transcript":
            text = data.get("text", "")
            is_final = data.get("is_final", False)
            confidence = data.get("confidence", 0)
            
            marker = "✅ FINAL" if is_final else "📝 INTERIM"
            confidence_str = f"{confidence*100:.0f}%" if confidence else "N/A"
            
            print(f"{marker} [{confidence_str}]: {text}")
            
            self.results["transcripts"].append({
                "text": text,
                "is_final": is_final,
                "confidence": confidence
            })
            
        elif msg_type == "audio":
            audio_data = data.get("data", "")
            duration_ms = data.get("duration_ms", 0)
            
            if audio_data:
                try:
                    audio_bytes = base64.b64decode(audio_data)
                    print(f"🔊 Received audio: {len(audio_bytes)} bytes ({duration_ms}ms)")
                    self.results["audio_chunks"].append({
                        "bytes": len(audio_bytes),
                        "duration_ms": duration_ms
                    })
                except Exception as e:
                    print(f"⚠️  Error decoding audio: {e}")
            
        elif msg_type == "error":
            error = data.get("error", "Unknown error")
            phase = data.get("phase", "unknown")
            
            print(f"🔴 ERROR in {phase}: {error}")
            self.results["errors"].append({
                "phase": phase,
                "error": error
            })
            
        elif msg_type == "metadata":
            print(f"ℹ️  Metadata: {data.get('data', {})}")
            self.results["metadata"].append(data.get('data'))
            
        else:
            print(f"❓ Unknown message type: {msg_type}")

    def print_summary(self):
        """Print summary of streaming session"""
        print("\n" + "="*60)
        print("📊 STREAMING SESSION SUMMARY")
        print("="*60)
        
        # Transcripts
        print(f"\n📝 Transcripts ({len(self.results['transcripts'])} updates):")
        for i, t in enumerate(self.results["transcripts"], 1):
            final = "[FINAL]" if t["is_final"] else "[INTERIM]"
            confidence = f"{t.get('confidence', 0)*100:.0f}%" if t.get('confidence') else "N/A"
            print(f"  {i}. {final} ({confidence}): {t['text'][:60]}")
        
        # Audio
        total_audio = sum(a["bytes"] for a in self.results["audio_chunks"])
        total_audio_duration = sum(a["duration_ms"] for a in self.results["audio_chunks"])
        print(f"\n🔊 Audio Chunks ({len(self.results['audio_chunks'])} chunks):")
        print(f"  Total bytes: {total_audio:,} bytes")
        print(f"  Total duration: {total_audio_duration}ms")
        print(f"  Average chunk: {total_audio//max(1, len(self.results['audio_chunks'])):,} bytes")
        
        # Errors
        if self.results["errors"]:
            print(f"\n❌ Errors ({len(self.results['errors'])}):")
            for i, e in enumerate(self.results["errors"], 1):
                if isinstance(e, dict):
                    print(f"  {i}. {e.get('phase')}: {e.get('error')}")
                else:
                    print(f"  {i}. {e}")
        else:
            print(f"\n✅ No errors!")
        
        # Metadata
        if self.results["metadata"]:
            print(f"\nℹ️  Metadata ({len(self.results['metadata'])} items):")
            for m in self.results["metadata"]:
                print(f"  {m}")
        
        print("\n" + "="*60)


async def main():
    """Main entry point"""
    import sys
    
    # Get WebSocket URL from command line or use default
    if len(sys.argv) > 1:
        ws_url = sys.argv[1]
    else:
        ws_url = "ws://localhost:8000/v1/stream/ws/call/example-123"
    
    # Get optional audio file path
    audio_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("🎙️  Ghost Voice OS - Streaming API Example")
    print("="*60)
    print(f"WebSocket URL: {ws_url}")
    if audio_file:
        print(f"Audio file: {audio_file}")
    print("="*60 + "\n")
    
    # Create and run client
    client = StreamingVoiceExample(ws_url, audio_file)
    await client.connect_and_stream()
    
    # Print summary
    client.print_summary()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
