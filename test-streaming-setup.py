#!/usr/bin/env python3
"""
Quick test to validate streaming pipeline setup
Run this to ensure all dependencies and configurations are correct
"""

import sys
import os

def check_python_version():
    """Check Python version"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    print(f"✅ Python {sys.version.split()[0]}")
    return True

def check_imports():
    """Check if required packages can be imported"""
    packages = {
        'fastapi': 'FastAPI (web framework)',
        'websockets': 'WebSockets (bidirectional)',
        'pydantic': 'Pydantic (validation)',
        'asyncio': 'AsyncIO (async support)',
    }
    
    all_good = True
    for package, description in packages.items():
        try:
            __import__(package)
            print(f"✅ {description}")
        except ImportError:
            print(f"❌ {description} - Install with: pip install -r requirements.txt")
            all_good = False
    
    return all_good

def check_streaming_files():
    """Check if streaming implementation files exist"""
    files = {
        'services/voice-api/providers/streaming/stt_base.py': 'STT base interface',
        'services/voice-api/providers/streaming/tts_base.py': 'TTS base interface',
        'services/voice-api/providers/streaming/llm_base.py': 'LLM base interface',
        'services/voice-api/providers/streaming/deepgram_streaming.py': 'Deepgram STT',
        'services/voice-api/providers/streaming/openai_streaming.py': 'OpenAI LLM',
        'services/voice-api/providers/streaming/elevenlabs_streaming.py': 'ElevenLabs TTS',
        'services/voice-api/core/streaming_engine.py': 'Streaming engine',
        'services/voice-api/routes/streaming.py': 'WebSocket routes',
    }
    
    all_good = True
    for filepath, description in files.items():
        if os.path.exists(filepath):
            print(f"✅ {description}")
        else:
            print(f"❌ {description} - Missing: {filepath}")
            all_good = False
    
    return all_good

def check_environment_variables():
    """Check for required API keys"""
    keys = {
        'DEEPGRAM_API_KEY': 'Deepgram (STT)',
        'OPENAI_API_KEY': 'OpenAI (LLM)',
        'ELEVENLABS_API_KEY': 'ElevenLabs (TTS)',
    }
    
    print("\nEnvironment Variables (optional for testing):")
    for key, description in keys.items():
        if os.getenv(key):
            print(f"✅ {key} set ({description})")
        else:
            print(f"⚠️  {key} not set ({description})")
    
    return True

def main():
    """Run all checks"""
    print("=" * 60)
    print("🎙️  Streaming Pipeline - Setup Verification")
    print("=" * 60)
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("Required Packages", check_imports),
        ("Streaming Files", check_streaming_files),
        ("Environment Setup", check_environment_variables),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n📋 {name}:")
        print("-" * 40)
        result = check_func()
        results.append((name, result))
    
    print()
    print("=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✅ All checks passed! You're ready to use streaming.")
        print("\nQuick Start:")
        print("  1. cd services/voice-api")
        print("  2. python main.py")
        print("  3. Connect with: ws://localhost:8000/v1/stream/ws/call/test-123")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please resolve the issues above.")
        print("\nFor help:")
        print("  • Installation: STREAMING_SETUP.md")
        print("  • Architecture: STREAMING_IMPLEMENTATION.md")
        print("  • Troubleshooting: See STREAMING_IMPLEMENTATION.md#troubleshooting")
        return 1

if __name__ == "__main__":
    sys.exit(main())
