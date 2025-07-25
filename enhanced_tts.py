"""
Enhanced TTS Engine for RinglyPro Voice Assistant
Supports OpenAI TTS, ElevenLabs, and fallback to browser TTS
"""

import os
import requests
import logging
import asyncio
import base64
from openai import OpenAI
from typing import Optional, Dict, Any, Tuple
import json
import time

class EnhancedTTSEngine:
    def __init__(self):
        # API clients
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        
        # Configuration
        self.default_engine = os.getenv("DEFAULT_VOICE_ENGINE", "openai")
        self.audio_quality = os.getenv("AUDIO_QUALITY", "high")
        self.max_duration = int(os.getenv("MAX_AUDIO_DURATION", "30"))
        self.timeout = int(os.getenv("AUDIO_TIMEOUT", "15"))
        
        # Voice configurations
        self.voice_configs = {
            "openai": {
                "model": "tts-1-hd" if self.audio_quality == "high" else "tts-1",
                "voices": {
                    "professional_female": "nova",
                    "friendly_female": "shimmer", 
                    "professional_male": "onyx",
                    "warm_female": "alloy"
                }
            },
            "elevenlabs": {
                "model": "eleven_multilingual_v2",
                "voices": {
                    "professional_female": "EXAVITQu4vr4xnSDxMaL",  # Bella
                    "empathetic_female": "21m00Tcm4TlvDq8ikWAM",   # Rachel
                    "confident_male": "pNInz6obpgDQGcFmaJgB",      # Adam
                    "custom_brand": os.getenv("RINGLYPRO_VOICE_ID")
                },
                "settings": {
                    "stability": 0.75,
                    "similarity_boost": 0.85,
                    "style": 0.5,
                    "use_speaker_boost": True
                }
            }
        }

    def optimize_text_for_speech(self, text: str, context: str = "neutral") -> str:
        """Transform written text into speech-optimized format"""
        
        # Step 1: Basic contractions for natural speech
        contractions = {
            "cannot": "can't", "will not": "won't", "do not": "don't",
            "does not": "doesn't", "did not": "didn't", "have not": "haven't", 
            "has not": "hasn't", "had not": "hadn't", "would not": "wouldn't",
            "could not": "couldn't", "should not": "shouldn't", "must not": "mustn't",
            "I am": "I'm", "you are": "you're", "we are": "we're", "they are": "they're",
            "it is": "it's", "that is": "that's", "there is": "there's", "here is": "here's",
            "I will": "I'll", "you will": "you'll", "we will": "we'll", "they will": "they'll",
            "I have": "I've", "you have": "you've", "we have": "we've", "they have": "they've",
            "I would": "I'd", "you would": "you'd", "we would": "we'd", "they would": "they'd"
        }
        
        for full, contraction in contractions.items():
            text = text.replace(full, contraction)
        
        # Step 2: Replace formal language with conversational
        conversational_replacements = {
            "However,": "But here's the thing,",
            "Additionally,": "Plus,", 
            "Furthermore,": "And what's even better,",
            "Nevertheless,": "Still though,",
            "Therefore,": "So,",
            "Consequently,": "Which means,",
            "In conclusion,": "So basically,",
            "For example,": "Like,",
            "Specifically,": "I mean,",
            "In particular,": "Especially,",
            "As a result,": "So what happens is,",
        }
        
        for formal, casual in conversational_replacements.items():
            text = text.replace(formal, casual)
        
        # Step 3: Business-specific optimizations
        business_optimizations = {
            "RinglyPro.com": "Ringly Pro",
            "24/7": "twenty-four seven", 
            "AI": "A-I",
            "FAQ": "frequently asked questions",
            "CRM": "customer management system",
            "SMS": "text messages",
            "API": "A-P-I"
        }
        
        for technical, spoken in business_optimizations.items():
            text = text.replace(technical, spoken)
        
        # Step 4: Context-specific adjustments
        if context == "empathetic":
            text = text.replace(". ", "... ")
            text = text.replace("I understand", "I totally understand")
            text = text.replace("That's correct", "You're absolutely right")
            
        elif context == "excited":
            text = text.replace("Good", "Fantastic")
            text = text.replace("Yes", "Absolutely")
            text = text.replace("That works", "That's perfect")
            
        elif context == "professional":
            text = text.replace("I think", "What I can tell you is")
            text = text.replace("Maybe", "What typically works best is")
            
        # Step 5: Add natural pauses for longer responses
        if len(text) > 120:
            sentences = text.split('. ')
            if len(sentences) > 2:
                formatted_sentences = []
                for i, sentence in enumerate(sentences):
                    formatted_sentences.append(sentence)
                    # Add natural breathing pause every 2 sentences
                    if (i + 1) % 2 == 0 and i < len(sentences) - 1:
                        formatted_sentences.append("... ")
                text = '. '.join(formatted_sentences)
        
        return text.strip()

    def detect_emotional_context(self, user_input: str, assistant_response: str) -> str:
        """Analyze conversation to determine appropriate emotional tone"""
        
        user_lower = user_input.lower()
        response_lower = assistant_response.lower()
        
        # Check for frustrated/confused users
        frustrated_indicators = ['problem', 'issue', 'not working', 'confused', 'help me', 'stuck', 'error']
        if any(indicator in user_lower for indicator in frustrated_indicators):
            return "empathetic"
        
        # Check for excited/positive interactions
        excited_indicators = ['great', 'awesome', 'perfect', 'amazing', 'love', 'fantastic']
        if any(indicator in response_lower for indicator in excited_indicators):
            return "excited"
            
        # Check for professional/business contexts
        professional_indicators = ['schedule', 'appointment', 'meeting', 'business', 'service', 'pricing']
        if any(indicator in response_lower for indicator in professional_indicators):
            return "professional"
            
        # Check for informational/calm contexts
        calm_indicators = ['how', 'what', 'explain', 'tell me', 'information', 'details']
        if any(indicator in user_lower for indicator in calm_indicators):
            return "calm"
            
        return "neutral"

    async def generate_audio_openai(self, text: str, context: str = "neutral") -> Optional[bytes]:
        """Generate audio using OpenAI TTS"""
        
        try:
            # Optimize text for speech
            optimized_text = self.optimize_text_for_speech(text, context)
            
            # Select appropriate voice based on context
            voice_mapping = {
                "empathetic": "nova",      # Warm, caring
                "professional": "alloy",   # Professional, clear
                "excited": "shimmer",      # Energetic, friendly
                "calm": "nova",            # Steady, reassuring
                "neutral": "nova"          # Default professional
            }
            
            selected_voice = voice_mapping.get(context, "nova")
            
            # Adjust speaking rate based on context
            speed_mapping = {
                "empathetic": 0.85,  # Slower for caring tone
                "professional": 0.95, # Standard professional pace
                "excited": 1.05,     # Faster for enthusiasm
                "calm": 0.90,        # Steady pace
                "neutral": 0.95      # Default
            }
            
            speaking_speed = speed_mapping.get(context, 0.95)
            
            # Generate audio
            response = self.openai_client.audio.speech.create(
                model=self.voice_configs["openai"]["model"],
                voice=selected_voice,
                input=optimized_text,
                speed=speaking_speed
            )
            
            audio_content = response.content
            
            # Log successful generation
            logging.info(f"OpenAI TTS generated {len(audio_content)} bytes for context: {context}")
            
            return audio_content
            
        except Exception as e:
            logging.error(f"OpenAI TTS generation failed: {e}")
            return None

    async def generate_audio_elevenlabs(self, text: str, context: str = "neutral", voice_type: str = "professional_female") -> Optional[bytes]:
        """Generate audio using ElevenLabs"""
        
        if not self.elevenlabs_api_key:
            logging.warning("ElevenLabs API key not found, skipping")
            return None
            
        try:
            # Optimize text for speech
            optimized_text = self.optimize_text_for_speech(text, context)
            
            # Select voice ID
            voice_id = self.voice_configs["elevenlabs"]["voices"].get(voice_type)
            if not voice_id:
                voice_id = self.voice_configs["elevenlabs"]["voices"]["professional_female"]
            
            # Adjust voice settings based on context
            base_settings = self.voice_configs["elevenlabs"]["settings"].copy()
            
            context_adjustments = {
                "empathetic": {"stability": 0.70, "style": 0.65},
                "professional": {"stability": 0.85, "style": 0.35},
                "excited": {"stability": 0.65, "style": 0.75},
                "calm": {"stability": 0.80, "style": 0.25}
            }
            
            if context in context_adjustments:
                base_settings.update(context_adjustments[context])
            
            # API request
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json", 
                "xi-api-key": self.elevenlabs_api_key
            }
            
            data = {
                "text": optimized_text,
                "model_id": self.voice_configs["elevenlabs"]["model"],
                "voice_settings": base_settings
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
            
            if response.status_code == 200:
                logging.info(f"ElevenLabs TTS generated {len(response.content)} bytes for context: {context}")
                return response.content
            else:
                logging.error(f"ElevenLabs API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"ElevenLabs TTS generation failed: {e}")
            return None

    async def generate_audio(self, text: str, user_input: str = "", preferred_engine: str = None) -> Tuple[Optional[bytes], str, str]:
        """
        Main audio generation method with automatic fallback
        Returns: (audio_bytes, engine_used, context_detected)
        """
        
        # Detect emotional context
        context = self.detect_emotional_context(user_input, text)
        
        # Determine which engine to use
        engine = preferred_engine or self.default_engine
        
        # Try primary engine
        audio_data = None
        engine_used = "none"
        
        if engine == "elevenlabs":
            audio_data = await self.generate_audio_elevenlabs(text, context)
            if audio_data:
                engine_used = "elevenlabs"
            
        if not audio_data and engine != "openai":  # Try OpenAI as fallback
            audio_data = await self.generate_audio_openai(text, context)
            if audio_data:
                engine_used = "openai"
        
        if not audio_data and engine == "openai":  # OpenAI as primary
            audio_data = await self.generate_audio_openai(text, context)
            if audio_data:
                engine_used = "openai"
                
        # Final fallback - return optimized text for browser TTS
        if not audio_data:
            logging.warning("All TTS engines failed, falling back to browser TTS")
            engine_used = "browser_fallback"
        
        return audio_data, engine_used, context

# Global instance for use in Flask routes
tts_engine = EnhancedTTSEngine()