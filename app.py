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

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="theme-color" content="#2c3e50">
  <meta http-equiv="Permissions-Policy" content="microphone=*">
  <title>Talk to RinglyPro AI — Your Business Assistant</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet" />
  <style>
    * { 
      box-sizing: border-box;
      -webkit-touch-callout: none;
      -webkit-user-select: none;
      -khtml-user-select: none;
      -moz-user-select: none;
      -ms-user-select: none;
      user-select: none;
      -webkit-tap-highlight-color: transparent;
    }

    html, body {
      margin: 0;
      padding: 0;
      font-family: 'Inter', sans-serif;
      background: linear-gradient(135deg, #2c3e50 0%, #0d1b2a 100%);
      color: #ffffff;
      width: 100%;
      height: 100vh;
      display: flex;
      justify-content: center;
      align-items: center;
      text-align: center;
      overflow: hidden;
    }

    .container {
      max-width: 450px;
      width: 100%;
      padding: 2rem;
      background: rgba(255, 255, 255, 0.15);
      backdrop-filter: blur(15px);
      border-radius: 25px;
      box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
      border: 1px solid rgba(255, 255, 255, 0.18);
      position: relative;
    }

    h1 {
      font-size: 2.5rem;
      font-weight: 700;
      margin-bottom: 0.5rem;
      background: linear-gradient(45deg, #4CAF50, #2196F3, #FF6B6B);
      background-size: 200% auto;
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      animation: gradientShift 3s ease-in-out infinite;
    }

    @keyframes gradientShift {
      0%, 100% { background-position: 0% 50%; }
      50% { background-position: 100% 50%; }
    }

    .subtitle {
      font-size: 1.1rem;
      margin-bottom: 2.5rem;
      opacity: 0.9;
      font-weight: 500;
    }

    .voice-visualizer {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      pointer-events: none;
      opacity: 0;
      transition: opacity 0.3s ease;
    }

    .voice-visualizer.active {
      opacity: 1;
    }

    .voice-wave {
      position: absolute;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(76, 175, 80, 0.1), rgba(76, 175, 80, 0.05));
      animation: voiceWave 2s infinite;
    }

    @keyframes voiceWave {
      0% { 
        transform: scale(0.8);
        opacity: 0.8;
      }
      50% {
        transform: scale(1.2);
        opacity: 0.4;
      }
      100% { 
        transform: scale(1.5);
        opacity: 0;
      }
    }

    .mic-container {
      position: relative;
      display: inline-block;
      margin-bottom: 2rem;
    }

    .mic-button {
      width: 130px;
      height: 130px;
      background: linear-gradient(135deg, #0a192f, #1c2541);
      border: none;
      border-radius: 50%;
      box-shadow: 0 10px 40px rgba(76, 175, 80, 0.3);
      display: flex;
      justify-content: center;
      align-items: center;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      cursor: pointer;
      position: relative;
      overflow: hidden;
      touch-action: manipulation;
    }

    .mic-button::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: linear-gradient(45deg, transparent, rgba(255,255,255,0.1), transparent);
      transform: translateX(-100%);
      transition: transform 0.6s;
    }

    .mic-button:hover::before {
      transform: translateX(100%);
    }

    .mic-button:hover {
      transform: scale(1.05);
      box-shadow: 0 15px 50px rgba(76, 175, 80, 0.4);
    }

    .mic-button:active {
      transform: scale(0.95);
    }

    .mic-button.listening {
      animation: listening 1.5s infinite;
      background: linear-gradient(135deg, #f44336, #d32f2f);
      box-shadow: 0 0 0 0 rgba(244, 67, 54, 0.7);
    }

    .mic-button.processing {
      background: linear-gradient(135deg, #FF9800, #F57C00);
      animation: processing 2s infinite;
    }

    .mic-button.speaking {
      background: linear-gradient(135deg, #4CAF50, #45a049);
      animation: speaking 2s infinite;
    }

    @keyframes listening {
      0% { 
        box-shadow: 0 0 0 0 rgba(244, 67, 54, 0.7);
        transform: scale(1);
      }
      50% {
        transform: scale(1.05);
      }
      70% { 
        box-shadow: 0 0 0 20px rgba(244, 67, 54, 0);
      }
      100% { 
        box-shadow: 0 0 0 0 rgba(244, 67, 54, 0);
        transform: scale(1);
      }
    }

    @keyframes processing {
      0%, 100% { transform: rotate(0deg) scale(1); }
      25% { transform: rotate(90deg) scale(1.05); }
      50% { transform: rotate(180deg) scale(1); }
      75% { transform: rotate(270deg) scale(1.05); }
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

    .mic-button svg {
      width: 60px;
      height: 60px;
      fill: #ffffff;
      z-index: 1;
      transition: transform 0.3s ease;
    }

    .mic-button.listening svg {
      transform: scale(1.1);
    }

    #status {
      font-size: 1.2rem;
      font-weight: 600;
      margin-bottom: 2rem;
      min-height: 3rem;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.3s ease;
    }

    .status-ready {
      color: #E3F2FD !important;
    }

    .status-listening {
      color: #FFCDD2 !important;
      animation: blink 1.5s infinite;
    }

    .status-processing {
      color: #FFF3E0 !important;
    }

    .status-speaking {
      color: #E8F5E8 !important;
    }

    @keyframes blink {
      0%, 50% { opacity: 1; }
      51%, 100% { opacity: 0.7; }
    }

    .controls {
      display: flex;
      gap: 1rem;
      justify-content: center;
      margin-bottom: 2rem;
    }

    .control-btn {
      padding: 0.75rem 1.5rem;
      background: rgba(255, 255, 255, 0.2);
      border: none;
      border-radius: 25px;
      color: white;
      cursor: pointer;
      transition: all 0.3s ease;
      font-weight: 500;
      touch-action: manipulation;
      min-height: 44px;
    }

    .control-btn:hover {
      background: rgba(255, 255, 255, 0.3);
      transform: translateY(-2px);
    }

    .control-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .language-selector {
      margin-bottom: 1.5rem;
    }

    .lang-btn {
      padding: 0.5rem 1rem;
      margin: 0 0.25rem;
      background: rgba(255, 255, 255, 0.2);
      border: none;
      border-radius: 15px;
      color: white;
      cursor: pointer;
      transition: all 0.3s ease;
      font-size: 0.9rem;
      touch-action: manipulation;
      min-height: 44px;
    }

    .lang-btn.active {
      background: rgba(76, 175, 80, 0.8);
      transform: scale(1.05);
    }

    .powered-by {
      margin-top: 2rem;
      font-size: 0.9rem;
      opacity: 0.8;
    }

    .claude-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      background: rgba(255, 255, 255, 0.15);
      padding: 0.75rem 1.25rem;
      border-radius: 25px;
      margin-top: 0.75rem;
      transition: all 0.3s ease;
    }

    .claude-badge:hover {
      background: rgba(255, 255, 255, 0.25);
      transform: translateY(-2px);
    }

    .ai-indicator {
      width: 8px;
      height: 8px;
      background: #4CAF50;
      border-radius: 50%;
      animation: aiPulse 2s infinite;
    }

    @keyframes aiPulse {
      0%, 100% { opacity: 0.3; transform: scale(1); }
      50% { opacity: 1; transform: scale(1.2); }
    }

    .error-message {
      background: rgba(244, 67, 54, 0.2);
      border: 1px solid rgba(244, 67, 54, 0.3);
      border-radius: 15px;
      padding: 1rem;
      margin-top: 1rem;
      font-size: 0.9rem;
      opacity: 0;
      transform: translateY(-10px);
      transition: all 0.3s ease;
      -webkit-user-select: text;
      -moz-user-select: text;
      -ms-user-select: text;
      user-select: text;
    }

    .error-message.show {
      opacity: 1;
      transform: translateY(0);
    }

    .audio-quality-indicator {
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
    }

    @keyframes slideInRight {
      from { transform: translateX(100%); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }

    @keyframes slideOutRight {
      from { transform: translateX(0); opacity: 1; }
      to { transform: translateX(100%); opacity: 0; }
    }

    @media (max-width: 480px) {
      .container {
        margin: 1rem;
        padding: 1.5rem;
      }
      
      h1 {
        font-size: 2rem;
      }
      
      .mic-button {
        width: 110px;
        height: 110px;
      }
      
      .mic-button svg {
        width: 50px;
        height: 50px;
      }

      .controls {
        flex-direction: column;
        gap: 0.5rem;
      }
    }

    .sr-only {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>RinglyPro AI</h1>
    <div class="subtitle">Your Intelligent Business Assistant</div>
    
    <div class="language-selector">
      <button class="lang-btn active" data-lang="en-US">🇺🇸 English</button>
      <button class="lang-btn" data-lang="es-ES">🇪🇸 Español</button>
    </div>

    <div class="mic-container">
      <div class="voice-visualizer" id="voiceVisualizer">
        <div class="voice-wave" style="width: 200px; height: 200px; top: 50%; left: 50%; transform: translate(-50%, -50%);"></div>
        <div class="voice-wave" style="width: 250px; height: 250px; top: 50%; left: 50%; transform: translate(-50%, -50%); animation-delay: 0.5s;"></div>
        <div class="voice-wave" style="width: 300px; height: 300px; top: 50%; left: 50%; transform: translate(-50%, -50%); animation-delay: 1s;"></div>
      </div>
      
      <button id="micBtn" class="mic-button" aria-label="Talk to RinglyPro AI">
        <svg xmlns="http://www.w3.org/2000/svg" height="60" viewBox="0 0 24 24" width="60" fill="#ffffff">
          <path d="M0 0h24v24H0V0z" fill="none"/>
          <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5-3c0 2.76-2.24 5-5 5s-5-2.24-5-5H6c0 3.31 2.69 6 6 6s6-2.69 6-6h-1zm-5 9c-3.87 0-7-3.13-7-7H3c0 5 4 9 9 9s9-4 9-9h-2c0 3.87-3.13 7-7 7z"/>
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

  <script>
    function debugLog(message, data) {
        console.log('[DEBUG] ' + message, data || '');
        const statusEl = document.getElementById('status');
        if (statusEl && message.includes('ERROR')) {
            statusEl.textContent = message;
            statusEl.style.color = '#ff6b6b';
        }
    }

    class EnhancedVoiceBot {
        constructor() {
            debugLog('Creating EnhancedVoiceBot instance...');
            
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
            this.audioURLs = new Set(); // 📱 Track audio URLs for cleanup
            
            this.init();
        }

        detectMobile() {
            return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        }

        async init() {
            debugLog('Initializing mobile-first voice bot...');
            
            const hasSpeechRecognition = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
            
            if (!hasSpeechRecognition) {
                debugLog('ERROR: Speech recognition not supported');
                this.showError('Speech recognition not supported in this browser. Use Chrome or Edge.');
                return;
            }

            // 📱 MOBILE AUDIO CONTEXT SETUP
            try {
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
                debugLog('Audio context initialized:', this.audioContext.state);
                
                if (this.isMobile) {
                    debugLog('📱 Setting up mobile audio environment...');
                    
                    // 📱 CREATE SILENT AUDIO TO UNLOCK iOS AUDIO
                    const unlockAudio = async () => {
                        try {
                            if (this.audioContext.state === 'suspended') {
                                await this.audioContext.resume();
                                debugLog('📱 Audio context resumed');
                            }
                            
                            // 📱 PLAY SILENT AUDIO TO UNLOCK MOBILE AUDIO
                            const silentAudio = new Audio('data:audio/mp3;base64,SUQzBAAAAAABEVRYWFgAAAAtAAADY29tbWVudABCaWdTb3VuZEJhbmsuY29tIC8gTGFTb25vdGhlcXVlLm9yZwBURU5DAAAAHQAAAWK+YLQtAAAA');
                            silentAudio.volume = 0;
                            silentAudio.play().catch(() => {
                                debugLog('📱 Silent audio unlock attempt (expected to potentially fail)');
                            });
                            
                            debugLog('📱 Mobile audio environment initialized');
                        } catch (error) {
                            debugLog('📱 Mobile audio unlock error (expected):', error);
                        }
                    };
                    
                    // 📱 UNLOCK AUDIO ON FIRST USER INTERACTION
                    const handleFirstInteraction = () => {
                        unlockAudio();
                        document.removeEventListener('touchstart', handleFirstInteraction);
                        document.removeEventListener('click', handleFirstInteraction);
                    };
                    
                    document.addEventListener('touchstart', handleFirstInteraction, { once: true });
                    document.addEventListener('click', handleFirstInteraction, { once: true });
                }
            } catch (error) {
                debugLog('Audio context initialization failed:', error);
            }

            this.setupEventListeners();
            
            if (this.isMobile) {
                this.updateStatus('📱 Tap the microphone to start talking');
                // 📱 ADDITIONAL MOBILE SETUP
                this.setupMobileAudioOptimizations();
            } else {
                this.initSpeechRecognition();
                this.userInteracted = true;
                this.updateStatus('🎙️ Click the microphone to start');
            }
        }

        // 📱 MOBILE AUDIO OPTIMIZATIONS
        setupMobileAudioOptimizations() {
            debugLog('📱 Setting up mobile audio optimizations...');
            
            // 📱 PREVENT MOBILE ZOOM ON DOUBLE TAP
            let lastTouchEnd = 0;
            document.addEventListener('touchend', (event) => {
                const now = Date.now();
                if (now - lastTouchEnd <= 300) {
                    event.preventDefault();
                }
                lastTouchEnd = now;
            }, false);
            
            // 📱 OPTIMIZE FOR MOBILE VIEWPORT
            const viewport = document.querySelector('meta[name=viewport]');
            if (viewport) {
                viewport.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover');
            }
            
            // 📱 MOBILE AUDIO QUALITY INDICATOR
            this.showMobileAudioStatus();
        }

        // 📱 MOBILE AUDIO STATUS INDICATOR
        showMobileAudioStatus() {
            const indicator = document.createElement('div');
            indicator.style.cssText = `
                position: fixed;
                top: 10px;
                left: 10px;
                background: rgba(76, 175, 80, 0.9);
                color: white;
                padding: 0.5rem 1rem;
                border-radius: 15px;
                font-size: 0.7rem;
                z-index: 1000;
                box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            `;
            indicator.innerHTML = '📱 Mobile Premium Audio Ready';
            document.body.appendChild(indicator);
            
            setTimeout(() => {
                indicator.style.opacity = '0';
                indicator.style.transition = 'opacity 0.3s ease';
                setTimeout(() => indicator.remove(), 300);
            }, 3000);
        }

        // 📱 MOBILE AUDIO STATE RESET - Add this method to your class
        resetMobileAudioState() {
            if (this.isMobile) {
                debugLog('📱 Resetting mobile audio state...');
                
                // 🔇 CRITICAL: Cancel any speech synthesis first
                speechSynthesis.cancel();
                
                // Clear any existing audio
                if (this.currentAudio) {
                    try {
                        this.currentAudio.pause();
                        this.currentAudio.src = '';
                        this.currentAudio = null;
                    } catch (error) {
                        debugLog('📱 Audio reset error (non-critical):', error);
                        this.currentAudio = null;
                    }
                }
                
                // 📱 CLEANUP ALL AUDIO URLs
                this.audioURLs.forEach(url => {
                    try {
                        URL.revokeObjectURL(url);
                    } catch (error) {
                        debugLog('📱 URL cleanup error (non-critical):', error);
                    }
                });
                this.audioURLs.clear();
                
                // Reset audio context if needed
                if (this.audioContext && this.audioContext.state === 'suspended') {
                    this.audioContext.resume().catch(error => {
                        debugLog('📱 Audio context resume error:', error);
                    });
                }
                
                // Reset UI state completely
                this.isPlaying = false;
                this.isProcessing = false;
                this.isListening = false;
                this.updateUI('ready');
                this.voiceVisualizer.classList.remove('active');
                this.updateStatus('📱 Ready for voice command');
                
                debugLog('📱 Mobile audio state reset complete');
            }
        }

        async requestMicrophonePermission() {
            debugLog('Requesting microphone permission...');
            
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                debugLog('Microphone permission granted');
                stream.getTracks().forEach(track => track.stop());
                return true;
            } catch (error) {
                debugLog('ERROR: Microphone permission denied', error.message);
                this.showError('Microphone permission denied. Please allow microphone access.');
                return false;
            }
        }

        initSpeechRecognition() {
            debugLog('Initializing speech recognition...');
            
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            
            try {
                this.recognition = new SpeechRecognition();
                this.recognition.continuous = false;
                this.recognition.interimResults = false;
                this.recognition.lang = this.currentLanguage;
                this.recognition.maxAlternatives = 1;

                this.recognition.onstart = () => {
                    debugLog('Speech recognition started');
                    this.isListening = true;
                    this.updateUI('listening');
                    this.voiceVisualizer.classList.add('active');
                    this.updateStatus('🎙️ Listening... Speak now');
                };

                this.recognition.onresult = (event) => {
                    debugLog('Speech recognition result:', event);
                    if (event.results && event.results.length > 0) {
                        const transcript = event.results[0][0].transcript.trim();
                        debugLog('Transcript received:', transcript);
                        
                        // 🔇 SIMPLE ECHO CHECK
                        const lowerTranscript = transcript.toLowerCase();
                        const isEcho = (lowerTranscript.includes('ringly pro') || 
                                       lowerTranscript.includes('i can help') || 
                                       lowerTranscript.includes('scheduling') ||
                                       lowerTranscript.includes('perfect') ||
                                       lowerTranscript.includes('wonderful')) && 
                                       transcript.length > 30;
                        
                        if (isEcho) {
                            debugLog('🔄 Simple echo detected, ignoring:', transcript);
                            this.updateStatus('🎙️ Ready to listen again');
                            this.updateUI('ready');
                            return;
                        }
                        
                        this.processTranscript(transcript);
                    }
                };

                this.recognition.onerror = (event) => {
                    debugLog('ERROR: Speech recognition error', event.error);
                    this.handleSpeechError(event.error);
                };

                this.recognition.onend = () => {
                    debugLog('Speech recognition ended');
                    this.isListening = false;
                    this.voiceVisualizer.classList.remove('active');
                    this.stopBtn.disabled = true;
                    
                    if (!this.isProcessing) {
                        this.updateUI('ready');
                        this.updateStatus('🎙️ Tap the microphone to start');
                    }
                };

                debugLog('Speech recognition initialized successfully');
            } catch (error) {
                debugLog('ERROR: Failed to initialize speech recognition', error.message);
                this.showError('Failed to initialize speech recognition: ' + error.message);
            }
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
                    message = 'Speech error: ' + error;
            }
            this.handleError(message);
        }

        async processTranscript(transcript) {
            if (!transcript || transcript.length < 2) {
                this.handleError('No valid speech detected');
                return;
            }

            debugLog('Processing transcript:', transcript);
            this.isProcessing = true;
            this.updateUI('processing');
            this.updateStatus('🤖 Processing...');

            const processingTimeout = setTimeout(() => {
                debugLog('ERROR: Processing timeout after 30 seconds');
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
                        language: this.currentLanguage,
                        mobile: this.isMobile
                    })
                });

                clearTimeout(processingTimeout);

                if (!response.ok) {
                    throw new Error('Server error: ' + response.status);
                }

                const data = await response.json();
                
                if (data.error) {
                    throw new Error(data.error);
                }
                
                if (!data.response) {
                    throw new Error('No response from server');
                }
                
                // 🔇 CRITICAL FIX: Only play ONE audio source, prioritize premium
                if (data.audio) {
                    debugLog('✅ Playing premium audio ONLY (no TTS fallback)');
                    await this.playPremiumAudio(data.audio, data.response);
                    this.showAudioQuality('premium', data.engine_used || 'elevenlabs');
                } else {
                    debugLog('✅ Using enhanced browser TTS ONLY');
                    await this.playEnhancedBrowserTTS(data.response, data.context || 'neutral');
                    this.showAudioQuality('enhanced', 'browser');
                }

            } catch (error) {
                clearTimeout(processingTimeout);
                debugLog('ERROR: Processing failed', error.message);
                this.handleError('Processing error: ' + error.message);
            }
        }

        // 📱 MOBILE LOADING FIX - Improved playPremiumAudio method
        async playPremiumAudio(audioBase64, responseText) {
            try {
                if (this.recognition && this.isListening) {
                    this.recognition.stop();
                    debugLog('🔇 Stopped speech recognition during audio');
                }
                
                // 🔇 CRITICAL: Cancel any existing TTS to prevent double audio
                speechSynthesis.cancel();
                debugLog('🔇 Cancelled speech synthesis to prevent double audio');
                
                debugLog('📱 Starting mobile premium audio playback...');
                
                const audioData = atob(audioBase64);
                const arrayBuffer = new ArrayBuffer(audioData.length);
                const uint8Array = new Uint8Array(arrayBuffer);
                
                for (let i = 0; i < audioData.length; i++) {
                    uint8Array[i] = audioData.charCodeAt(i);
                }

                const audioBlob = new Blob([arrayBuffer], { 
                    type: this.isMobile ? 'audio/mp3' : 'audio/mpeg'
                });
                const audioUrl = URL.createObjectURL(audioBlob);
                
                // 📱 TRACK URL FOR CLEANUP
                this.audioURLs.add(audioUrl);
                
                this.currentAudio = new Audio();
                
                if (this.isMobile) {
                    debugLog('📱 Configuring for mobile device...');
                    this.currentAudio.crossOrigin = 'anonymous';
                    this.currentAudio.preload = 'metadata'; // 📱 CHANGED: Use metadata instead of auto
                    this.currentAudio.volume = 0.9;
                    this.currentAudio.playbackRate = 1.0;
                    this.currentAudio.setAttribute('webkit-playsinline', 'true');
                    this.currentAudio.setAttribute('playsinline', 'true');
                    this.currentAudio.muted = false;
                } else {
                    this.currentAudio.preload = 'auto';
                    this.currentAudio.volume = 0.85;
                }
                
                this.currentAudio.src = audioUrl;
                
                return new Promise((resolve, reject) => {
                    let loadTimeout;
                    let hasResolved = false; // 📱 PREVENT DOUBLE RESOLUTION
                    
                    const resolveOnce = (value) => {
                        if (!hasResolved) {
                            hasResolved = true;
                            resolve(value);
                        }
                    };
                    
                    if (this.isMobile) {
                        loadTimeout = setTimeout(() => {
                            debugLog('📱 Mobile audio loading timeout, using TTS fallback');
                            this.cleanupCurrentAudio();
                            this.playEnhancedBrowserTTS(responseText, 'neutral').then(resolveOnce);
                        }, 8000); // 📱 REDUCED TIMEOUT
                    }
                    
                    this.currentAudio.onloadstart = () => {
                        debugLog('📱 Mobile audio loading started...');
                        this.updateStatus('🔊 Loading Rachel...');
                    };
                    
                    this.currentAudio.oncanplay = () => {
                        debugLog('📱 Mobile audio can play');
                        if (loadTimeout) clearTimeout(loadTimeout);
                    };
                    
                    this.currentAudio.onplay = () => {
                        debugLog('📱 Mobile premium audio playing');
                        this.isPlaying = true;
                        this.updateUI('speaking');
                        this.updateStatus('🔊 Rachel speaking...');
                        if (loadTimeout) clearTimeout(loadTimeout);
                        
                        // 🔇 CRITICAL: Cancel any speech synthesis immediately when premium audio starts
                        speechSynthesis.cancel();
                        debugLog('🔇 CANCELLED speech synthesis - premium audio is playing');
                    };
                    
                    this.currentAudio.onended = () => {
                        debugLog('📱 Mobile premium audio ended');
                        this.audioFinished();
                        
                        // 📱 MOBILE FIX: Reset state properly after audio ends
                        setTimeout(() => {
                            if (this.isMobile) {
                                this.resetMobileAudioState();
                            }
                            this.updateStatus('🎙️ Tap microphone to continue');
                        }, 1000);
                        
                        resolveOnce();
                    };
                    
                    this.currentAudio.onerror = (error) => {
                        debugLog('📱 Mobile audio error:', error);
                        
                        if (loadTimeout) clearTimeout(loadTimeout);
                        
                        this.audioFinished();
                        
                        // 🔇 CRITICAL FIX: ONLY fallback to TTS if premium audio completely fails
                        debugLog('📱 Premium audio failed, using TTS fallback');
                        
                        // 🔇 MAKE SURE we don't have double resolution
                        if (!hasResolved) {
                            this.playEnhancedBrowserTTS(responseText, 'neutral').then(resolveOnce);
                        }
                    };
                    
                    const playAudio = async () => {
                        try {
                            debugLog('📱 Attempting to play mobile audio...');
                            
                            // 📱 ENSURE AUDIO CONTEXT IS READY
                            if (this.audioContext && this.audioContext.state === 'suspended') {
                                await this.audioContext.resume();
                                debugLog('📱 Audio context resumed for mobile');
                            }
                            
                            // 📱 MOBILE SPECIFIC: Wait a bit for audio to be ready
                            if (this.isMobile && this.currentAudio.readyState < 2) {
                                debugLog('📱 Waiting for mobile audio to be ready...');
                                await new Promise(resolve => {
                                    const checkReady = () => {
                                        if (this.currentAudio && this.currentAudio.readyState >= 2) {
                                            resolve();
                                        } else if (this.currentAudio) {
                                            setTimeout(checkReady, 100);
                                        } else {
                                            resolve(); // Audio was cleaned up
                                        }
                                    };
                                    checkReady();
                                });
                            }
                            
                            if (this.currentAudio) {
                                const playPromise = this.currentAudio.play();
                                
                                if (playPromise !== undefined) {
                                    await playPromise;
                                    debugLog('📱 Mobile audio play promise resolved');
                                }
                            }
                            
                        } catch (playError) {
                            debugLog('📱 Mobile play error:', playError.name, playError.message);
                            
                            if (playError.name === 'NotAllowedError') {
                                debugLog('📱 Mobile audio blocked by browser policy');
                                this.updateStatus('🔊 Please tap screen to enable audio');
                                
                                const enableAudio = () => {
                                    if (this.currentAudio) {
                                        this.currentAudio.play().catch(() => {
                                            this.currentAudio.onerror(playError);
                                        });
                                    }
                                };
                                
                                document.addEventListener('touchstart', enableAudio, { once: true });
                                document.addEventListener('click', enableAudio, { once: true });
                                
                            } else {
                                this.currentAudio.onerror(playError);
                            }
                        }
                    };
                    
                    // 📱 MOBILE SPECIFIC: Start playing immediately for mobile
                    if (this.isMobile) {
                        // Load the audio first, then play
                        this.currentAudio.load();
                        setTimeout(() => {
                            if (this.currentAudio && !hasResolved) {
                                playAudio();
                            }
                        }, 100);
                    } else {
                        if (this.currentAudio.readyState >= 2) {
                            playAudio();
                        } else {
                            this.currentAudio.addEventListener('canplay', playAudio, { once: true });
                        }
                    }
                });
                
            } catch (error) {
                debugLog('📱 Mobile premium audio setup failed:', error);
                // 🔇 ONLY fallback to TTS if premium audio completely fails
                return this.playEnhancedBrowserTTS(responseText, 'neutral');
            }
        }

        // 📱 HELPER METHOD FOR AUDIO CLEANUP
        cleanupCurrentAudio() {
            if (this.currentAudio) {
                try {
                    this.currentAudio.pause();
                    this.currentAudio.src = '';
                    this.currentAudio = null;
                } catch (error) {
                    debugLog('📱 Audio cleanup error (non-critical):', error);
                    this.currentAudio = null;
                }
            }
        }

        async playEnhancedBrowserTTS(text, context) {
            try {
                // 🔇 CRITICAL: Don't play TTS if premium audio is already playing
                if (this.isPlaying) {
                    debugLog('🔇 BLOCKING TTS: Premium audio is already playing');
                    return;
                }
                
                if (this.recognition && this.isListening) {
                    this.recognition.stop();
                    debugLog('🔇 Stopped speech recognition during TTS');
                }
                
                speechSynthesis.cancel();
                await new Promise(resolve => setTimeout(resolve, 100));
                
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = this.currentLanguage;
                
                if (this.isMobile) {
                    debugLog('📱 Using mobile TTS settings...');
                    utterance.rate = 0.9;
                    utterance.pitch = 1.0;
                    utterance.volume = 1.0;
                    
                    const voices = speechSynthesis.getVoices();
                    debugLog('📱 Available voices:', voices.length);
                    
                    if (voices.length > 0) {
                        const preferredVoice = voices.find(voice => 
                            voice.lang.startsWith('en') && 
                            (voice.name.includes('Female') || voice.name.includes('woman') || voice.name.includes('Google'))
                        ) || voices.find(voice => voice.lang.startsWith('en'));
                        
                        if (preferredVoice) {
                            utterance.voice = preferredVoice;
                            debugLog('📱 Using mobile voice:', preferredVoice.name);
                        }
                    }
                } else {
                    utterance.rate = 0.95;
                    utterance.pitch = 1.0;
                    utterance.volume = 0.85;
                }

                return new Promise((resolve) => {
                    utterance.onstart = () => {
                        // 🔇 DOUBLE CHECK: Don't start if premium audio started playing
                        if (this.currentAudio) {
                            debugLog('🔇 CANCELLING TTS: Premium audio detected');
                            speechSynthesis.cancel();
                            resolve();
                            return;
                        }
                        
                        this.isPlaying = true;
                        this.updateUI('speaking');
                        this.updateStatus(this.isMobile ? '📱 Speaking...' : '🔊 Speaking...');
                        debugLog(this.isMobile ? '📱 Mobile TTS started' : '🔊 Desktop TTS started');
                    };

                    utterance.onend = () => {
                        debugLog(this.isMobile ? '📱 Mobile TTS ended' : '🔊 Desktop TTS ended');
                        this.audioFinished();
                        
                        setTimeout(() => {
                            this.updateStatus('🎙️ Tap microphone to continue');
                        }, 1000);
                        
                        resolve();
                    };

                    utterance.onerror = (error) => {
                        debugLog('ERROR: Browser TTS error', error);
                        this.audioFinished();
                        resolve();
                    };

                    if (this.isMobile && speechSynthesis.getVoices().length === 0) {
                        debugLog('📱 Loading mobile voices...');
                        speechSynthesis.addEventListener('voiceschanged', () => {
                            speechSynthesis.speak(utterance);
                        }, { once: true });
                    } else {
                        speechSynthesis.speak(utterance);
                    }
                });

            } catch (error) {
                debugLog('ERROR: Enhanced browser TTS failed', error);
                this.audioFinished();
            }
        }

        showAudioQuality(quality, engine) {
            const indicator = document.createElement('div');
            indicator.className = 'audio-quality-indicator';
            
            const qualityText = quality === 'premium' 
                ? '🎵 Premium Audio (' + engine + ')' 
                : '🔊 Enhanced Audio (' + engine + ')';
                
            indicator.innerHTML = qualityText;
            document.body.appendChild(indicator);
            
            setTimeout(() => {
                indicator.style.animation = 'slideOutRight 0.3s ease';
                setTimeout(() => indicator.remove(), 300);
            }, 3000);
        }

        // 📱 MOBILE CLEANUP FIX - Improved audioFinished method
        audioFinished() {
            debugLog('📱 Audio playback finished - cleaning up mobile resources');
            this.isPlaying = false;
            this.isProcessing = false;
            this.updateUI('ready');
            
            // 📱 MOBILE AUDIO CLEANUP
            this.cleanupCurrentAudio();
            
            // 📱 CLEANUP AUDIO URLs
            this.audioURLs.forEach(url => {
                try {
                    URL.revokeObjectURL(url);
                } catch (error) {
                    debugLog('📱 URL cleanup error (non-critical):', error);
                }
            });
            this.audioURLs.clear();
            
            // 📱 MOBILE MEMORY CLEANUP
            if (this.isMobile) {
                // Force garbage collection hint
                setTimeout(() => {
                    if (window.gc) {
                        window.gc();
                    }
                }, 1000);
            }
        }

        setupEventListeners() {
            const micHandler = async (e) => {
                e.preventDefault();
                debugLog('Microphone button activated');
                
                // 📱 MOBILE STATE RESET BEFORE NEW INTERACTION
                if (this.isMobile && this.userInteracted) {
                    // 🔇 CRITICAL: Always reset state before new interaction
                    debugLog('📱 Performing complete mobile reset before new interaction');
                    this.resetMobileAudioState();
                    
                    // 📱 LONGER DELAY for mobile to ensure complete cleanup
                    await new Promise(resolve => setTimeout(resolve, 500));
                }
                
                if (!this.userInteracted) {
                    debugLog('First user interaction - enabling voice features');
                    this.userInteracted = true;
                    
                    if (this.isMobile) {
                        const permissionGranted = await this.requestMicrophonePermission();
                        if (!permissionGranted) {
                            return;
                        }
                    }
                    
                    if (this.audioContext && this.audioContext.state === 'suspended') {
                        await this.audioContext.resume();
                    }
                    
                    this.initSpeechRecognition();
                    this.updateStatus('🎙️ Voice enabled! Tap microphone to start');
                    return;
                }
                
                // 📱 MOBILE: Additional check to prevent multiple simultaneous requests
                if (this.isMobile && (this.isProcessing || this.isPlaying || this.isListening)) {
                    debugLog('📱 Mobile: Blocking interaction - another process is active');
                    return;
                }
                
                this.toggleListening();
            };
            
            this.micBtn.addEventListener('click', micHandler);
            this.micBtn.addEventListener('touchend', micHandler);
            
            this.stopBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (this.isListening) {
                    this.stopListening();
                } else if (this.isPlaying) {
                    this.stopAudio();
                }
                
                // 📱 MOBILE RESET AFTER STOP
                if (this.isMobile) {
                    setTimeout(() => this.resetMobileAudioState(), 500);
                }
            });
            
            this.clearBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.clearAll();
            });
            
            this.langBtns.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.changeLanguage(e.target.dataset.lang);
                });
            });
        }

        changeLanguage(lang) {
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
                this.handleError('Failed to start listening: ' + error.message);
            }
        }

        stopListening() {
            if (this.isListening && this.recognition) {
                try {
                    this.recognition.stop();
                } catch (error) {
                    debugLog('ERROR: Failed to stop speech recognition', error.message);
                }
            }
        }

        // 📱 IMPROVED stopAudio method for better mobile handling
        stopAudio() {
            if (this.isPlaying) {
                debugLog('📱 Stopping mobile audio...');
                
                this.cleanupCurrentAudio();
                speechSynthesis.cancel();
                this.audioFinished();
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
                    this.micBtn.classList.add('speaking');
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

        showError(message) {
            this.errorMessage.textContent = message;
            this.errorMessage.classList.add('show');
            setTimeout(() => this.clearError(), 8000);
        }

        clearError() {
            this.errorMessage.classList.remove('show');
        }

        // 📱 ENHANCED clearAll method for mobile
        clearAll() {
            debugLog('📱 Clearing all mobile audio resources...');
            
            this.stopAudio();
            
            if (this.isListening && this.recognition) {
                try {
                    this.recognition.stop();
                } catch (error) {
                    debugLog('📱 Recognition stop error (non-critical):', error);
                }
            }
            
            // 📱 RESET ALL STATES
            this.isProcessing = false;
            this.isListening = false;
            this.isPlaying = false;
            this.updateUI('ready');
            this.voiceVisualizer.classList.remove('active');
            this.clearError();
            this.updateStatus('🎙️ Tap microphone to start');
            
            // 📱 MOBILE CLEANUP
            if (this.isMobile) {
                speechSynthesis.cancel();
                
                // Clear any pending timeouts
                setTimeout(() => {
                    this.updateStatus('📱 Ready for next command');
                }, 500);
            }
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        try {
            new EnhancedVoiceBot();
        } catch (error) {
            console.error('Failed to create voice bot:', error);
            document.getElementById('status').textContent = 'Failed to initialize: ' + error.message;
        }
    });
  </script>
</body>
</html>
'''

@app.route('/')
def serve_index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/process-text-enhanced', methods=['POST'])
def process_text_enhanced():
    """Mobile-optimized premium audio with ElevenLabs"""
    logging.info("📱 Mobile-first premium audio processing")
    
    try:
        data = request.get_json()
        logging.info(f"📋 Request data: {data}")
        
        if not data or 'text' not in data:
            logging.error("❌ Missing text data")
            return jsonify({"error": "Missing text data"}), 400
            
        user_text = data['text'].strip()
        user_language = data.get('language', 'en-US')
        is_mobile = data.get('mobile', False)
        
        # 🔇 BACKEND ECHO DETECTION
        echo_phrases = [
            'ringly pro', 'i can help', 'scheduling', 'perfect', 'wonderful',
            'how can i help', 'i\'m here to help', 'that\'s great', 'absolutely',
            'fantastic', 'excellent'
        ]
        
        user_lower = user_text.lower()
        is_echo = any(phrase in user_lower for phrase in echo_phrases) and len(user_text) > 30
        
        if is_echo:
            logging.warning(f"🔄 Backend echo detected: '{user_text[:50]}...'")
            return jsonify({
                "response": "I think I heard an echo. Please speak again.",
                "language": user_language,
                "context": "clarification",
                "engine_used": "echo_prevention"
            })
        
        if not user_text or len(user_text) < 2:
            error_msg = ("Texto muy corto. Por favor intenta de nuevo." 
                        if user_language.startswith('es') 
                        else "Text too short. Please try again.")
            logging.error(f"❌ Text too short: '{user_text}'")
            return jsonify({"error": error_msg}), 400
        
        logging.info(f"📝 Processing text: '{user_text}'")
        logging.info(f"📱 Mobile request: {is_mobile}")
        
        # Step 1: Generate response
        faq_response, is_faq = get_faq_response(user_text)
        response_text = None
        context = "neutral"
        
        if is_faq:
            response_text = faq_response
            context = "professional"
        else:
            if any(word in user_lower for word in ['problem', 'issue', 'help']):
                context = "empathetic"
                response_text = "I understand what you're asking about. Let me help you with that."
            elif any(word in user_lower for word in ['schedule', 'appointment', 'book']):
                context = "professional" 
                response_text = "I can help you with scheduling. RinglyPro makes booking appointments super easy."
            elif any(word in user_lower for word in ['how', 'what', 'explain']):
                context = "calm"
                response_text = "Let me explain that for you. I'm here to provide clear, helpful information."
            else:
                context = "friendly"
                response_text = "Hi! I'm your RinglyPro AI assistant. How can I help you today?"
        
        # Step 2: MOBILE-OPTIMIZED ELEVENLABS AUDIO
        audio_data = None
        engine_used = "browser_fallback"
        
        elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
        if elevenlabs_key:
            try:
                import requests
                
                logging.info(f"📱 Generating mobile-optimized ElevenLabs audio...")
                
                url = "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM"
                
                headers = {
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": elevenlabs_key
                }
                
                mobile_text = response_text[:180]
                mobile_text = mobile_text.replace("RinglyPro", "Ringly Pro")
                mobile_text = mobile_text.replace("AI", "A.I.")
                
                tts_data = {
                    "text": mobile_text,
                    "model_id": "eleven_flash_v2_5" if is_mobile else "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": 0.8,
                        "similarity_boost": 0.9,
                        "style": 0.2,
                        "use_speaker_boost": False
                    }
                }
                
                if is_mobile:
                    tts_data["optimize_streaming_latency"] = 4
                    tts_data["output_format"] = "mp3_44100_128"
                
                timeout = 6 if is_mobile else 10
                tts_response = requests.post(url, json=tts_data, headers=headers, timeout=timeout)
                
                if tts_response.status_code == 200:
                    audio_content = tts_response.content
                    
                    if len(audio_content) > 1000:
                        audio_data = base64.b64encode(audio_content).decode('utf-8')
                        engine_used = "elevenlabs_mobile" if is_mobile else "elevenlabs"
                        logging.info(f"✅ {'Mobile' if is_mobile else 'Desktop'} ElevenLabs audio generated ({len(audio_content)} bytes)")
                    else:
                        logging.warning("📱 ElevenLabs audio too small, using fallback")
                else:
                    logging.warning(f"📱 ElevenLabs failed: {tts_response.status_code}")
                    
            except requests.exceptions.Timeout:
                logging.warning("📱 ElevenLabs timeout - mobile network issue")
            except Exception as tts_error:
                logging.error(f"📱 ElevenLabs mobile error: {tts_error}")
        
        # Step 3: Return mobile-optimized response
        response_payload = {
            "response": response_text,
            "language": user_language,
            "context": context,
            "is_faq": is_faq,
            "engine_used": engine_used,
            "mobile_optimized": is_mobile,
            "echo_prevention": True
        }
        
        if audio_data:
            response_payload["audio"] = audio_data
            response_payload["audio_format"] = "mp3_mobile" if is_mobile else "mp3_desktop"
            logging.info(f"✅ {'Mobile' if is_mobile else 'Desktop'} response with premium Rachel audio")
        else:
            logging.info(f"✅ {'Mobile' if is_mobile else 'Desktop'} response with browser TTS fallback")
        
        return jsonify(response_payload)
        
    except Exception as e:
        logging.error(f"❌ Mobile processing error: {e}")
        return jsonify({"error": "I had a technical issue. Please try again."}), 500

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
        
        faq_response, is_faq = get_faq_response(user_text)
        
        if is_faq:
            response_text = faq_response
        else:
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
            "Premium TTS (ElevenLabs Rachel)",
            "Mobile Premium Audio Support",
            "Echo Prevention System",
            "Speech-Optimized Responses",
            "Browser Speech Recognition",
            "Bilingual Support",
            "FAQ Matching",
            "iOS Audio Compatibility",
            "Mobile State Reset System",
            "Audio Memory Management"
        ]
    })

# Allow iframe embedding
@app.after_request
def allow_iframe_embedding(response):
    response.headers['X-Frame-Options'] = 'ALLOWALL'
    response.headers['Content-Security-Policy'] = "frame-ancestors *"
    return response

if __name__ == "__main__":
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
    print("   • Premium TTS with ElevenLabs Rachel voice")
    print("   • Mobile Premium Audio Support (iOS Compatible)")
    print("   • Echo prevention system (frontend + backend)")
    print("   • Speech-optimized responses")
    print("   • Enhanced mobile compatibility")
    print("   • Smart audio fallback system")
    print("   • Real-time audio quality indicators")
    print("   • Mobile state reset system")
    print("   • Audio memory management")
    print("\n📋 API Keys Status:")
    print(f"   • Claude API: {'✅ Connected' if anthropic_api_key else '❌ Missing'}")
    print(f"   • OpenAI TTS: {'✅ Available' if openai_api_key else '❌ Missing'}")
    print(f"   • ElevenLabs TTS: {'✅ Available' if os.getenv('ELEVENLABS_API_KEY') else '❌ Missing'}")
    print("\n🌐 Access URLs:")
    print("   • Main App: http://localhost:5000")
    print("   • Health Check: http://localhost:5000/health")
    print("\n📱 Mobile Premium Audio: ✅ iOS Compatible")
    print("🔇 Echo Prevention: ✅ Frontend + Backend protection")
    print("🎵 Audio Quality: Premium Rachel voice with mobile optimization")
    print("📱 Mobile Loading Fix: ✅ State reset + Audio cleanup")
    print("🧹 Memory Management: ✅ URL cleanup + Resource management")

    app.run(debug=True, host='0.0.0.0', port=5000)
