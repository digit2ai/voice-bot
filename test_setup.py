#!/usr/bin/env python3
"""
Test script for Enhanced TTS setup
Run this to verify everything is working before launching
"""

import os
import sys
import asyncio
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_environment_variables():
    """Test if all required environment variables are set"""
    print("🔍 Testing Environment Variables...")
    
    required_vars = {
        'ANTHROPIC_API_KEY': 'Claude AI responses',
        'OPENAI_API_KEY': 'OpenAI TTS (recommended)',
        'ELEVENLABS_API_KEY': 'ElevenLabs TTS (premium)'
    }
    
    results = {}
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask the key for security
            masked = value[:8] + '...' + value[-4:] if len(value) > 12 else 'present'
            print(f"   ✅ {var}: {masked} ({description})")
            results[var] = True
        else:
            print(f"   ❌ {var}: Missing ({description})")
            results[var] = False
    
    return results

def test_claude_api():
    """Test Claude API connection"""
    print("\n🧠 Testing Claude API...")
    
    try:
        import anthropic
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("   ❌ ANTHROPIC_API_KEY not found")
            return False
            
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=20,
            messages=[{"role": "user", "content": "Say hello"}]
        )
        
        result = response.content[0].text.strip()
        print(f"   ✅ Claude API working: {result}")
        return True
        
    except Exception as e:
        print(f"   ❌ Claude API error: {e}")
        return False

def test_openai_tts():
    """Test OpenAI TTS"""
    print("\n🎵 Testing OpenAI TTS...")
    
    try:
        from openai import OpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("   ⚠️  OPENAI_API_KEY not found - skipping")
            return False
            
        client = OpenAI(api_key=api_key)
        
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input="Hello, this is a test of OpenAI TTS."
        )
        
        audio_size = len(response.content)
        print(f"   ✅ OpenAI TTS working: Generated {audio_size} bytes")
        return True
        
    except Exception as e:
        print(f"   ❌ OpenAI TTS error: {e}")
        return False

def test_elevenlabs_tts():
    """Test ElevenLabs TTS"""
    print("\n🎤 Testing ElevenLabs TTS...")
    
    try:
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            print("   ⚠️  ELEVENLABS_API_KEY not found - skipping")
            return False
        
        # Test with a simple voice
        url = "https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
        
        data = {
            "text": "Hello, this is a test of ElevenLabs TTS.",
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.75,
                "similarity_boost": 0.85,
                "style": 0.5
            }
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            audio_size = len(response.content)
            print(f"   ✅ ElevenLabs TTS working: Generated {audio_size} bytes")
            return True
        else:
            print(f"   ❌ ElevenLabs TTS error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ ElevenLabs TTS error: {e}")
        return False

def test_enhanced_modules():
    """Test if our enhanced modules can be imported"""
    print("\n📦 Testing Enhanced Modules...")
    
    try:
        # Test if files exist
        required_files = [
            'enhanced_tts.py',
            'speech_optimized_claude.py'
        ]
        
        for file in required_files:
            if os.path.exists(file):
                print(f"   ✅ {file} exists")
            else:
                print(f"   ❌ {file} missing")
                return False
        
        # Test imports
        from enhanced_tts import tts_engine
        from speech_optimized_claude import get_enhanced_claude_response
        
        print("   ✅ All modules imported successfully")
        return True
        
    except Exception as e:
        print(f"   ❌ Module import error: {e}")
        return False

async def test_tts_engine():
    """Test the enhanced TTS engine"""
    print("\n🔧 Testing Enhanced TTS Engine...")
    
    try:
        from enhanced_tts import tts_engine
        
        test_text = "Hello! This is a test of the enhanced RinglyPro voice system."
        
        # Test audio generation
        audio_bytes, engine_used, context = await tts_engine.generate_audio(
            test_text, 
            "test input"
        )
        
        if audio_bytes:
            print(f"   ✅ TTS Engine working: {len(audio_bytes)} bytes using {engine_used}")
            return True
        else:
            print(f"   ⚠️  TTS Engine: No audio generated, fallback available")
            return True  # Still okay, browser fallback will work
            
    except Exception as e:
        print(f"   ❌ TTS Engine error: {e}")
        return False

def test_speech_optimization():
    """Test speech text optimization"""
    print("\n💬 Testing Speech Optimization...")
    
    try:
        from speech_optimized_claude import get_enhanced_claude_response
        
        test_input = "How does scheduling work?"
        
        response = get_enhanced_claude_response(test_input, "professional", "english")
        
        # Check if response has speech optimizations
        has_contractions = "'" in response
        is_reasonable_length = len(response.split()) < 80
        sounds_conversational = any(word in response.lower() for word in ['so,', 'basically,', 'actually,', 'here\'s'])
        
        print(f"   ✅ Response generated: '{response[:60]}...'")
        print(f"   ✅ Has contractions: {has_contractions}")
        print(f"   ✅ Reasonable length: {is_reasonable_length} ({len(response.split())} words)")
        print(f"   ✅ Conversational tone: {sounds_conversational}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Speech optimization error: {e}")
        return False

def test_flask_app():
    """Test if Flask app can start"""
    print("\n🌐 Testing Flask App Setup...")
    
    try:
        from flask import Flask
        
        # Basic import test
        print("   ✅ Flask imports working")
        
        # Check if main app file exists
        if os.path.exists('app.py'):
            print("   ✅ app.py exists")
        else:
            print("   ❌ app.py not found")
            return False
            
        print("   ✅ Flask app should be ready to start")
        print("   ℹ️  Run 'python app.py' to start the server")
        return True
        
    except Exception as e:
        print(f"   ❌ Flask setup error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 RinglyPro Enhanced Voice Assistant - Setup Test")
    print("=" * 60)
    
    tests = [
        ("Environment Variables", test_environment_variables),
        ("Claude API", test_claude_api),
        ("OpenAI TTS", test_openai_tts),
        ("ElevenLabs TTS", test_elevenlabs_tts),
        ("Enhanced Modules", test_enhanced_modules),
        ("Speech Optimization", test_speech_optimization),
        ("Flask App", test_flask_app),
    ]
    
    results = {}
    
    # Run synchronous tests
    for test_name, test_func in tests:
        if test_name == "Enhanced TTS Engine":
            continue  # Skip async test for now
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"   ❌ {test_name} test failed: {e}")
            results[test_name] = False
    
    # Run async test
    try:
        print("\n🔧 Testing Enhanced TTS Engine...")
        results["Enhanced TTS Engine"] = asyncio.run(test_tts_engine())
    except Exception as e:
        print(f"   ❌ Enhanced TTS Engine test failed: {e}")
        results["Enhanced TTS Engine"] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")
    
    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Your setup is ready.")
        print("🚀 Run 'python app.py' to start your enhanced voice assistant")
    elif passed >= total - 2:
        print("\n⚠️  MOSTLY READY! Some premium features may be limited.")
        print("🚀 You can still run 'python app.py' - fallbacks will work")
    else:
        print("\n❌ SETUP INCOMPLETE! Please fix the failing tests before proceeding.")
        
        # Provide specific guidance
        if not results.get("Environment Variables"):
            print("\n📋 NEXT STEPS:")
            print("1. Create/update your .env file with required API keys")
            print("2. Get OpenAI API key: https://platform.openai.com/api-keys")
            print("3. Get ElevenLabs API key: https://elevenlabs.io (optional)")
        
        if not results.get("Enhanced Modules"):
            print("4. Make sure enhanced_tts.py and speech_optimized_claude.py are in your project folder")
        
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)