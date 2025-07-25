# Add to your .env file for advanced voice customization

# Voice Engine Preferences (choose primary and fallback)
DEFAULT_VOICE_ENGINE=elevenlabs  # Options: openai, elevenlabs, browser
VOICE_FALLBACK_ENGINE=openai

# OpenAI Voice Selection
OPENAI_VOICE_PROFESSIONAL=nova     # Warm, professional female
OPENAI_VOICE_EMPATHETIC=shimmer    # Gentle, caring female  
OPENAI_VOICE_EXCITED=shimmer       # Energetic female
OPENAI_VOICE_CALM=alloy           # Steady, gender-neutral

# ElevenLabs Voice Selection (get these from your ElevenLabs account)
ELEVENLABS_VOICE_PROFESSIONAL=EXAVITQu4vr4xnSDxMaL  # Bella - professional
ELEVENLABS_VOICE_EMPATHETIC=21m00Tcm4TlvDq8ikWAM    # Rachel - caring
ELEVENLABS_VOICE_EXCITED=pNInz6obpgDQGcFmaJgB       # Adam - confident male
ELEVENLABS_VOICE_CALM=EXAVITQu4vr4xnSDxMaL          # Bella - calm

# Audio Quality Settings  
AUDIO_QUALITY=high                 # Options: high, medium, low
AUDIO_BITRATE=128                  # kbps - higher = better quality
MAX_AUDIO_DURATION=30              # seconds - prevents overly long responses
AUDIO_TIMEOUT=15                   # seconds - API timeout

# Speech Optimization
ENABLE_CONTRACTIONS=true           # Enable natural contractions (can't, won't, etc.)
ENABLE_CONTEXT_DETECTION=true     # Detect emotional context from user input
ENABLE_SPEECH_PAUSES=true         # Add natural pauses for longer responses
MAX_RESPONSE_WORDS=70             # Maximum words per response for phone calls

# A/B Testing (Optional)
ENABLE_VOICE_AB_TEST=false        # Test different voice configurations
VOICE_AB_TEST_PERCENTAGE=50       # Percentage of users who get new voice
AB_TEST_VOICE_ENGINE=elevenlabs   # Engine to test against default

# Debugging and Monitoring
LOG_TTS_PERFORMANCE=true          # Log audio generation times
LOG_USER_INTERACTIONS=true        # Log user conversations (be mindful of privacy)
ENABLE_AUDIO_CACHING=false        # Cache frequently used responses (future feature)