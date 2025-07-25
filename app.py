from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import anthropic
import os
import logging
from dotenv import load_dotenv
from difflib import get_close_matches
import json
import time
import base64
import asyncio

# Import our new modules
from enhanced_tts import tts_engine
from speech_optimized_claude import get_enhanced_claude_response

# Load environment variables
load_dotenv()

# API Keys validation
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

if not anthropic_api_key:
    raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

# Setup Flask
app = Flask(__name__)
CORS(app)

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Your existing FAQ_BRAIN (keep this unchanged)
FAQ_BRAIN = {
    # ... (your existing FAQ dictionary stays the same)
    "what is ringlypro?": (
        "RinglyPro.com is an AI-powered business assistant built for solo professionals and service-based businesses. It acts as your 24/7 receptionist, scheduler, and communication hub, helping you handle calls, book appointments, follow up with leads, and automate your entire sales and communication process."
    ),
    # ... (rest of your FAQ entries)
}

def get_faq_response(user_text: str) -> tuple[str, bool]:
    """
    Check for FAQ matches with fuzzy matching
    Returns: (response_text, is_faq_match)
    """
    user_text_lower = user_text.lower().strip()
    
    # Try exact match first
    if user_text_lower in FAQ_BRAIN:
        return FAQ_BRAIN[user_text_lower], True
    
    # Try fuzzy matching
    matched = get_close_matches(user_text_lower, FAQ_BRAIN.keys(), n=1, cutoff=0.6)
    if matched:
        return FAQ_BRAIN[matched[0]], True
    
    return "", False

# Your existing HTML template (keep unchanged for now)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
  <!-- Your existing head content stays the same -->
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <title>Talk to RinglyPro AI — Your Business Assistant</title>
  <!-- ... rest of your existing HTML head ... -->
</head>
<body>
  <!-- Your existing body content -->
  <div class="container">
    <h1>RinglyPro AI</h1>
    <div class="subtitle">Your Intelligent Business Assistant</div>
    
    <div class="language-selector">
      <button class="lang-btn active" data-lang="en-US">🇺🇸 English</button>
      <button class="lang-btn" data-lang="es-ES">🇪🇸 Español</button>
    </div>

    <div class="mic-container">
      <div class="voice-visualizer" id="voiceVisualizer"></div>
      <button id="micBtn" class="mic-button" aria-label="Talk to RinglyPro AI">
        <svg xmlns="http://www.w3.org/2000/svg" height="60" viewBox="0 0 24 24" width="60" fill="#ffffff">
          <!-- Your existing SVG -->
        </svg>
      </button>
    </div>
    
    <div id="status" class="status-ready">🎙️ Tap to talk to RinglyPro AI</div>
    
    <div class="controls">
      <button id="stopBtn" class="control-btn" disabled>⏹️ Stop</button>
      <button id="clearBtn" class="control-btn">🗑️ Clean</button>
    </div>

    <div id="errorMessage" class="error-message"></div>
    
    <div class="powered-by">
      Powered by
      <div class="claude-badge">
        <div class="ai-indicator"></div>
        Enhanced Claude AI + Premium TTS
      </div>
    </div>
  </div>

  <!-- Enhanced JavaScript for premium audio -->
  <script>
    class EnhancedVoiceBot {
      constructor() {
        this.micBtn = document.getElementById('micBtn');
        this.status = document.getElementById('status');
        this.stopBtn = document.getElementById('stopBtn');
        this.clearBtn = document.getElementById('clearBtn');
        this.errorMessage = document.getElementById('errorMessage');
        this.voiceVisualizer = document.getElementById('voiceVisualizer');
        this.langBtns = document.querySelectorAll('.lang-btn');
        
        this.isListening = false;
        this.isProcessing = false;
        this.isPlaying = false;
        this.currentLanguage = 'en-US';
        this.recognition = null;
        this.currentAudio = null;
        this.audioContext = null;
        this.userInteracted = false;
        this.isMobile = this.detectMobile();
        
        this.init();
      }

      detectMobile() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
      }

      async init() {
        console.log('Initializing enhanced voice bot...');
        
        try {
          this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
          console.log('Audio context initialized');
        } catch (error) {
          console.warn('Web Audio API not supported:', error);
        }
        
        this.setupEventListeners();
        this.initSpeechRecognition();
        
        if (this.isMobile) {
          this.updateStatus('🎙️ Tap the microphone to start');
        } else {
          this.updateStatus('🎙️ Click the microphone to start');
        }
      }

      initSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        
        if (!SpeechRecognition) {
          this.showError('Speech recognition not supported in this browser');
          return;
        }
        
        try {
          this.recognition = new SpeechRecognition();
          this.recognition.continuous = false;
          this.recognition.interimResults = false;
          this.recognition.lang = this.currentLanguage;
          this.recognition.maxAlternatives = 1;

          this.recognition.onstart = () => {
            console.log('Speech recognition started');
            this.isListening = true;
            this.updateUI('listening');
            this.voiceVisualizer.classList.add('active');
            this.updateStatus('🎙️ Listening... Speak now');
          };

          this.recognition.onresult = (event) => {
            if (event.results && event.results.length > 0) {
              const transcript = event.results[0][0].transcript.trim();
              console.log('Transcript received:', transcript);
              this.processTranscript(transcript);
            }
          };

          this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            this.handleSpeechError(event.error);
          };

          this.recognition.onend = () => {
            console.log('Speech recognition ended');
            this.isListening = false;
            this.voiceVisualizer.classList.remove('active');
            this.stopBtn.disabled = true;
            
            if (!this.isProcessing) {
              this.updateUI('ready');
              this.updateStatus('🎙️ Tap the microphone to start');
            }
          };

        } catch (error) {
          console.error('Failed to initialize speech recognition:', error);
          this.showError('Speech recognition initialization failed');
        }
      }

      async processTranscript(transcript) {
        if (!transcript || transcript.length < 2) {
          this.handleError('No valid speech detected');
          return;
        }

        console.log('Processing transcript:', transcript);
        this.isProcessing = true;
        this.updateUI('processing');
        this.updateStatus('🤖 Processing...');

        const processingTimeout = setTimeout(() => {
          console.error('Processing timeout after 30 seconds');
          this.handleError('Processing timeout. Please try again.');
        }, 30000);

        try {
          const response = await fetch('/process-text-enhanced', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              text: transcript,
              language: this.currentLanguage
            })
          });

          clearTimeout(processingTimeout);

          if (!response.ok) {
            throw new Error(`Server error: ${response.status} ${response.statusText}`);
          }

          const data = await response.json();
          
          if (data.error) {
            throw new Error(data.error);
          }
          
          if (!data.response) {
            throw new Error('No response from server');
          }
          
          // Play premium audio if available, fallback to enhanced browser TTS
          if (data.audio) {
            console.log('Playing premium audio...');
            await this.playPremiumAudio(data.audio, data.response);
            this.showAudioQuality('premium', data.engine_used);
          } else {
            console.log('Using enhanced browser TTS...');
            await this.playEnhancedBrowserTTS(data.response, data.context || 'neutral');
            this.showAudioQuality('enhanced', 'browser');
          }

        } catch (error) {
          clearTimeout(processingTimeout);
          console.error('Processing failed:', error);
          this.handleError('Processing error: ' + error.message);
        }
      }

      async playPremiumAudio(audioBase64, responseText) {
        try {
          // Convert base64 to audio data
          const audioData = atob(audioBase64);
          const arrayBuffer = new ArrayBuffer(audioData.length);
          const uint8Array = new Uint8Array(arrayBuffer);
          
          for (let i = 0; i < audioData.length; i++) {
            uint8Array[i] = audioData.charCodeAt(i);
          }

          // Create audio blob and URL
          const audioBlob = new Blob([arrayBuffer], { type: 'audio/mpeg' });
          const audioUrl = URL.createObjectURL(audioBlob);
          
          // Create and configure audio element
          this.currentAudio = new Audio(audioUrl);
          this.currentAudio.preload = 'auto';
          
          return new Promise((resolve, reject) => {
            this.currentAudio.onloadstart = () => {
              this.updateStatus('🔊 Loading audio...');
            };
            
            this.currentAudio.onplay = () => {
              this.isPlaying = true;
              this.updateUI('speaking');
              this.updateStatus('🔊 Speaking...');
            };
            
            this.currentAudio.onended = () => {
              this.audioFinished();
              URL.revokeObjectURL(audioUrl);
              resolve();
            };
            
            this.currentAudio.onerror = (error) => {
              console.error('Audio playback error:', error);
              this.audioFinished();
              URL.revokeObjectURL(audioUrl);
              // Fallback to browser TTS
              this.playEnhancedBrowserTTS(responseText, 'neutral').then(resolve);
            };

            // Start playback
            this.currentAudio.play().catch(error => {
              console.error('Audio play failed:', error);
              this.currentAudio.onerror(error);
            });
          });
          
        } catch (error) {
          console.error('Premium audio playback failed:', error);
          // Fallback to enhanced browser TTS
          return this.playEnhancedBrowserTTS(responseText, 'neutral');
        }
      }

      async playEnhancedBrowserTTS(text, context) {
        console.log('Using enhanced browser TTS with context:', context);
        
        try {
          // Cancel any existing speech
          speechSynthesis.cancel();
          await new Promise(resolve => setTimeout(resolve, 100));
          
          const utterance = new SpeechSynthesisUtterance(text);
          utterance.lang = this.currentLanguage;
          
          // Context-based voice settings
          const contextSettings = {
            empathetic: { rate: 0.85, pitch: 0.9, volume: 0.8 },
            professional: { rate: 0.95, pitch: 1.0, volume: 0.9 },
            excited: { rate: 1.05, pitch: 1.1, volume: 0.9 },
            calm: { rate: 0.90, pitch: 0.95, volume: 0.8 },
            neutral: { rate: 0.95, pitch: 1.0, volume: 0.85 }
          };
          
          const settings = contextSettings[context] || contextSettings.neutral;
          utterance.rate = settings.rate;
          utterance.pitch = settings.pitch;
          utterance.volume = settings.volume;

          // Try to select better voice
          const voices = speechSynthesis.getVoices();
          const preferredVoices = this.currentLanguage.startsWith('es') 
            ? ['Google español', 'Microsoft Sabina', 'Spanish']
            : ['Google UK English Female', 'Microsoft Zira', 'Samantha', 'Google US English'];

          for (const voiceName of preferredVoices) {
            const voice = voices.find(v => v.name.includes(voiceName));
            if (voice) {
              utterance.voice = voice;
              break;
            }
          }

          return new Promise((resolve) => {
            utterance.onstart = () => {
              this.isPlaying = true;
              this.updateUI('speaking');
              this.updateStatus('🔊 Speaking...');
            };

            utterance.onend = () => {
              this.audioFinished();
              resolve();
            };

            utterance.onerror = (error) => {
              console.error('Browser TTS error:', error);
              this.audioFinished();
              resolve();
            };

            speechSynthesis.speak(utterance);
          });

        } catch (error) {
          console.error('Enhanced browser TTS failed:', error);
          this.audioFinished();
        }
      }

      showAudioQuality(quality, engine) {
        const indicator = document.createElement('div');
        indicator.className = 'audio-quality-indicator';
        
        const qualityText = quality === 'premium' 
          ? `🎵 Premium Audio (${engine})` 
          : `🔊 Enhanced Audio (${engine})`;
          
        indicator.innerHTML = qualityText;
        
        indicator.style.cssText = `
          position: fixed;
          top: 20px;
          right: 20px;
          background: rgba(76, 175, 80, 0.9);
          color: white;
          padding: 0.75rem 1rem;
          border-radius: 20px;
          font-size: 0.8rem;
          z-index: 1000;
          box-shadow: 0 4px 12px rgba(0,0,0,0.3);
          animation: slideInRight 0.3s ease;
        `;
        
        document.body.appendChild(indicator);
        
        setTimeout(() => {
          indicator.style.animation = 'slideOutRight 0.3s ease';
          setTimeout(() => indicator.remove(), 300);
        }, 3000);
      }

      audioFinished() {
        console.log('Audio playback finished');
        this.isPlaying = false;
        this.isProcessing = false;
        this.updateUI('ready');
        this.updateStatus('🎙️ Tap microphone to continue');
        
        if (this.currentAudio) {
          this.currentAudio = null;
        }
      }

      stopAudio() {
        if (this.isPlaying) {
          if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio.currentTime = 0;
            this.currentAudio = null;
          }
          
          speechSynthesis.cancel();
          this.audioFinished();
        }
      }

      setupEventListeners() {
        // Microphone button
        const micHandler = async (e) => {
          e.preventDefault();
          
          if (!this.userInteracted) {
            this.userInteracted = true;
            
            if (this.audioContext && this.audioContext.state === 'suspended') {
              await this.audioContext.resume();
            }
            
            this.updateStatus('🎙️ Voice enabled! Tap to start');
            return;
          }
          
          this.toggleListening();
        };
        
        this.micBtn.addEventListener('click', micHandler);
        this.micBtn.addEventListener('touchend', micHandler);
        
        // Stop button
        this.stopBtn.addEventListener('click', (e) => {
          e.preventDefault();
          
          if (this.isListening) {
            this.stopListening();
          } else if (this.isPlaying) {
            this.stopAudio();
          }
        });
        
        // Clear button
        this.clearBtn.addEventListener('click', (e) => {
          e.preventDefault();
          this.clearAll();
        });
        
        // Language buttons
        this.langBtns.forEach(btn => {
          btn.addEventListener('click', (e) => {
            e.preventDefault();
            this.changeLanguage(e.target.dataset.lang);
          });
        });

        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
          if (document.hidden && this.isPlaying) {
            this.stopAudio();
          }
        });
      }

      changeLanguage(lang) {
        console.log('Changing language to:', lang);
        this.currentLanguage = lang;
        if (this.recognition) {
          this.recognition.lang = lang;
        }
        
        this.langBtns.forEach(btn => {
          btn.classList.toggle('active', btn.dataset.lang === lang);
        });
      }

      toggleListening() {
        if (this.isListening) {
          this.stopListening();
        } else {
          this.startListening();
        }
      }

      async startListening() {
        if (this.isProcessing || !this.recognition || !this.userInteracted) {
          return;
        }
        
        try {
          this.clearError();
          speechSynthesis.cancel();
          
          this.recognition.start();
          this.stopBtn.disabled = false;
          
        } catch (error) {
          console.error('Failed to start speech recognition:', error);
          this.handleError('Failed to start listening: ' + error.message);
        }
      }

      stopListening() {
        if (this.isListening && this.recognition) {
          try {
            this.recognition.stop();
          } catch (error) {
            console.error('Failed to stop speech recognition:', error);
          }
        }
      }

      updateUI(state) {
        this.micBtn.className = 'mic-button';
        this.status.className = '';
        
        switch (state) {
          case 'listening':
            this.micBtn.classList.add('listening');
            this.status.classList.add('status-listening');
            this.stopBtn.disabled = false;
            break;
          case 'processing':
            this.micBtn.classList.add('processing');
            this.status.classList.add('status-processing');
            this.stopBtn.disabled = false;
            break;
          case 'speaking':
            this.status.classList.add('status-speaking');
            this.stopBtn.disabled = false;
            break;
          case 'ready':
          default:
            this.status.classList.add('status-ready');
            this.stopBtn.disabled = true;
            break;
        }
      }

      updateStatus(message) {
        this.status.textContent = message;
        this.status.style.color = '';
      }

      handleError(message) {
        console.error('ERROR:', message);
        this.showError(message);
        this.isProcessing = false;
        this.isListening = false;
        this.isPlaying = false;
        this.updateUI('ready');
        this.voiceVisualizer.classList.remove('active');
        
        setTimeout(() => {
          this.updateStatus('🎙️ Tap microphone to try again');
        }, 3000);
      }

      handleSpeechError(error) {
        let message = '';
        switch (error) {
          case 'not-allowed':
            message = 'Microphone access denied. Please allow microphone permission.';
            break;
          case 'no-speech':
            message = 'No speech detected. Please try again.';
            break;
          case 'audio-capture':
            message = 'Microphone not accessible. Check if another app is using it.';
            break;
          case 'network':
            message = 'Network error. Check your internet connection.';
            break;
          default:
            message = `Speech error: ${error}`;
        }
        
        this.handleError(message);
      }

      showError(message) {
        this.errorMessage.textContent = message;
        this.errorMessage.classList.add('show');
        
        setTimeout(() => {
          this.clearError();
        }, 8000);
      }

      clearError() {
        this.errorMessage.classList.remove('show');
      }

      clearAll() {
        console.log('Clearing all...');
        
        this.stopAudio();
        
        if (this.isListening && this.recognition) {
          this.recognition.stop();
        }
        
        this.isProcessing = false;
        this.isListening = false;
        this.isPlaying = false;
        
        this.updateUI('ready');
        this.voiceVisualizer.classList.remove('active');
        this.clearError();
        this.updateStatus('🎙️ Tap microphone to start');
      }
    }

    // Add CSS animations for quality indicator
    const style = document.createElement('style');
    style.textContent = `
      @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
      
      @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
      }
      
      .mic-button.speaking {
        background: linear-gradient(135deg, #4CAF50, #45a049);
        animation: speaking 2s infinite;
      }
      
      @keyframes speaking {
        0%, 100% { 
          box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.7);
          transform: scale(1);
        }
        25% { transform: scale(1.02); }
        50% { box-shadow: 0 0 0 15px rgba(76, 175, 80, 0); }
        75% { transform: scale(0.98); }
      }
    `;
    document.head.appendChild(style);

    // Initialize enhanced voice bot
    document.addEventListener('DOMContentLoaded', () => {
      console.log('Initializing enhanced voice bot...');
      try {
        new EnhancedVoiceBot();
      } catch (error) {
        console.error('Failed to create enhanced voice bot:', error);
        document.getElementById('status').textContent = 'Initialization failed: ' + error.message;
      }
    });
  </script>
</body>
</html>
"""

@app.route('/')
def serve_index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/process-text-enhanced', methods=['POST'])
async def process_text_enhanced():
    """Enhanced text processing with premium TTS"""
    logging.info("📥 Received enhanced text processing request")
    
    try:
        data = request.get_json()
        logging.info(f"📋 Request data: {data}")
        
        if not data or 'text' not in data:
            logging.error("❌ Missing text data")
            return jsonify({"error": "Missing text data"}), 400
            
        user_text = data['text'].strip()
        user_language = data.get('language', 'en-US')
        
        if not user_text or len(user_text) < 2:
            error_msg = ("Texto muy corto. Por favor intenta de nuevo." 
                        if user_language.startswith('es') 
                        else "Text too short. Please try again.")
            logging.error(f"❌ Text too short: '{user_text}'")
            return jsonify({"error": error_msg}), 400
        
        logging.info(f"📝 Processing text: '{user_text}'")
        logging.info(f"🌐 Language: {user_language}")
        
        # Step 1: Try FAQ matching first (fast response)
        faq_response, is_faq = get_faq_response(user_text)
        response_text = None
        context = "neutral"
        
        if is_faq:
            response_text = faq_response
            logging.info("🤖 Matched FAQ response")
            # Simple context detection for FAQ
            if any(word in user_text.lower() for word in ['problem', 'help', 'issue']):
                context = "empathetic"
            elif any(word in faq_response.lower() for word in ['great', 'perfect', 'amazing']):
                context = "excited"
            else:
                context = "professional"
        else:
            # Step 2: Get enhanced Claude response
            language_context = "spanish" if user_language.startswith('es') else "english"
            
            try:
                logging.info("🧠 Calling enhanced Claude...")
                
                # Detect context from user input first
                user_lower = user_text.lower()
                if any(word in user_lower for word in ['problem', 'issue', 'help', 'confused', 'stuck']):
                    context = "empathetic"
                elif any(word in user_lower for word in ['great', 'awesome', 'love', 'amazing']):
                    context = "excited"
                elif any(word in user_lower for word in ['schedule', 'appointment', 'book', 'meeting']):
                    context = "professional"
                elif any(word in user_lower for word in ['how', 'what', 'explain', 'tell me']):
                    context = "calm"
                else:
                    context = "neutral"
                
                response_text = get_enhanced_claude_response(user_text, context, language_context)
                logging.info(f"✅ Enhanced Claude response received: {response_text[:100]}...")
                
            except Exception as e:
                logging.error(f"❌ Enhanced Claude error: {e}")
                fallback_msg = ("Lo siento, tuve un problema técnico. Por favor intenta de nuevo." 
                              if user_language.startswith('es') 
                              else "Sorry, I had a technical issue. Please try again.")
                return jsonify({"error": fallback_msg}), 500
        
        # Step 3: Generate premium audio
        audio_data = None
        engine_used = "none"
        
        try:
            logging.info(f"🎵 Generating audio with context: {context}")
            
            # Run async TTS generation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            audio_bytes, engine_used, detected_context = loop.run_until_complete(
                tts_engine.generate_audio(response_text, user_text)
            )
            loop.close()
            
            if audio_bytes:
                audio_data = base64.b64encode(audio_bytes).decode('utf-8')
                logging.info(f"✅ Audio generated successfully using {engine_used}")
            else:
                logging.warning(f"⚠️ Audio generation failed, using fallback")
                
        except Exception as e:
            logging.error(f"❌ Audio generation error: {e}")
            engine_used = "browser_fallback"
        
        # Step 4: Return response
        response_payload = {
            "response": response_text,
            "language": user_language,
            "context": context,
            "is_faq": is_faq,
            "engine_used": engine_used
        }
        
        if audio_data:
            response_payload["audio"] = audio_data
        
        logging.info("✅ Sending enhanced response")
        return jsonify(response_payload)
        
    except Exception as e:
        logging.error(f"❌ Enhanced processing error: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Keep your existing routes
@app.route('/process-text', methods=['POST'])
def process_text():
    """Original endpoint for backwards compatibility"""
    logging.info("📥 Received original text processing request")
    
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({"error": "Missing text data"}), 400
            
        user_text = data['text'].strip()
        user_language = data.get('language', 'en-US')
        
        if not user_text or len(user_text) < 2:
            error_msg = ("Texto muy corto. Por favor intenta de nuevo." 
                        if user_language.startswith('es') 
                        else "Text too short. Please try again.")
            return jsonify({"error": error_msg}), 400
        
        # Use FAQ matching or fallback to simple Claude response
        faq_response, is_faq = get_faq_response(user_text)
        
        if is_faq:
            response_text = faq_response
        else:
            # Simple Claude fallback (your original logic)
            try:
                claude_client = anthropic.Anthropic(api_key=anthropic_api_key)
                message = claude_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=250,
                    temperature=0.8,
                    system="You are RinglyPro AI, a helpful business assistant. Keep responses under 80 words.",
                    messages=[{"role": "user", "content": user_text}]
                )
                response_text = message.content[0].text.strip()
            except Exception as e:
                logging.error(f"Original Claude error: {e}")
                response_text = "I'm sorry, I had a technical issue. Please try again."
        
        return jsonify({
            "response": response_text,
            "language": user_language,
            "matched_faq": is_faq
        })
        
    except Exception as e:
        logging.error(f"Original processing error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/health')
def health_check():
    """Enhanced health check"""
    tts_status = {
        "openai": "available" if openai_api_key else "missing_key",
        "elevenlabs": "available" if os.getenv("ELEVENLABS_API_KEY") else "missing_key",
        "browser_fallback": "available"
    }
    
    return jsonify({
        "status": "healthy",
        "claude_api": "connected" if anthropic_api_key else "missing",
        "tts_engines": tts_status,
        "timestamp": time.time(),
        "features": [
            "Enhanced Claude Sonnet 4 AI",
            "Premium TTS (OpenAI + ElevenLabs)",
            "Emotional Context Detection", 
            "Speech-Optimized Responses",
            "Browser Speech Recognition",
            "Bilingual Support",
            "FAQ Matching",
            "Mobile Compatibility"
        ]
    })

@app.route('/tts-test', methods=['POST'])
async def tts_test():
    """Test endpoint for TTS engines"""
    try:
        data = request.get_json()
        text = data.get('text', 'Hello, this is a test of the RinglyPro AI voice system.')
        context = data.get('context', 'neutral')
        engine = data.get('engine', 'auto')
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        if engine == 'auto':
            audio_bytes, engine_used, detected_context = loop.run_until_complete(
                tts_engine.generate_audio(text, "test input")
            )
        elif engine == 'openai':
            audio_bytes = loop.run_until_complete(
                tts_engine.generate_audio_openai(text, context)
            )
            engine_used = "openai" if audio_bytes else "failed"
        elif engine == 'elevenlabs':
            audio_bytes = loop.run_until_complete(
                tts_engine.generate_audio_elevenlabs(text, context)
            )
            engine_used = "elevenlabs" if audio_bytes else "failed"
        else:
            return jsonify({"error": "Invalid engine specified"}), 400
            
        loop.close()
        
        if audio_bytes:
            audio_data = base64.b64encode(audio_bytes).decode('utf-8')
            return jsonify({
                "success": True,
                "audio": audio_data,
                "engine_used": engine_used,
                "context": context,
                "text_processed": tts_engine.optimize_text_for_speech(text, context)
            })
        else:
            return jsonify({
                "success": False,
                "error": "Audio generation failed",
                "engine_tested": engine
            })
            
    except Exception as e:
        logging.error(f"TTS test error: {e}")
        return jsonify({"error": str(e)}), 500

# Allow iframe embedding
@app.after_request
def allow_iframe_embedding(response):
    response.headers['X-Frame-Options'] = 'ALLOWALL'
    response.headers['Content-Security-Policy'] = "frame-ancestors *"
    return response

if __name__ == "__main__":
    # Verify API connections on startup
    try:
        claude_client = anthropic.Anthropic(api_key=anthropic_api_key)
        test_claude = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hello"}]
        )
        logging.info("✅ Claude API connection successful")
    except Exception as e:
        logging.error(f"❌ Claude API connection test failed: {e}")
        print("⚠️  Warning: Claude API connection not verified.")

    # Test TTS engines
    if openai_api_key:
        logging.info("✅ OpenAI API key found")
    else:
        logging.warning("⚠️  OpenAI API key not found - premium TTS unavailable")

    if os.getenv("ELEVENLABS_API_KEY"):
        logging.info("✅ ElevenLabs API key found")
    else:
        logging.warning("⚠️  ElevenLabs API key not found - premium TTS limited")

    print("🚀 Starting Enhanced RinglyPro AI Voice Assistant...")
    print("🎯 Enhanced Features:")
    print("   • Premium TTS with OpenAI + ElevenLabs")
    print("   • Speech-optimized Claude responses")
    print("   • Emotional context detection")
    print("   • Enhanced mobile compatibility")
    print("   • Smart audio fallback system")
    print("   • A/B testing capabilities")
    print("   • Real-time audio quality indicators")
    print("\n📋 API Keys Status:")
    print(f"   • Claude API: {'✅ Connected' if anthropic_api_key else '❌ Missing'}")
    print(f"   • OpenAI TTS: {'✅ Available' if openai_api_key else '❌ Missing'}")
    print(f"   • ElevenLabs TTS: {'✅ Available' if os.getenv('ELEVENLABS_API_KEY') else '❌ Missing'}")
    print("\n🌐 Access URLs:")
    print("   • Main App: http://localhost:5000")
    print("   • Health Check: http://localhost:5000/health")
    print("   • TTS Test: http://localhost:5000/tts-test")
    print("\n📱 Mobile Support: ✅ Enhanced compatibility")
    print("🎵 Audio Quality: Premium with intelligent fallback")

    app.run(debug=True, host='0.0.0.0', port=5000)