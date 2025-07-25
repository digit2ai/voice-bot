from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import anthropic
import os
import logging
from dotenv import load_dotenv
from difflib import get_close_matches
import json
import time

# Load environment variables
load_dotenv()

# API Keys
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

if not anthropic_api_key:
    raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

# Initialize Claude client
claude_client = anthropic.Anthropic(api_key=anthropic_api_key)

# Setup Flask
app = Flask(__name__)
CORS(app)

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Enhanced FAQ dictionary for RinglyPro.com
FAQ_BRAIN = {
    # What is RinglyPro?
    "what is ringlypro?": (
        "RinglyPro.com is an AI-powered business assistant built for solo professionals and service-based businesses. It acts as your 24/7 receptionist, scheduler, and communication hub, helping you handle calls, book appointments, follow up with leads, and automate your entire sales and communication process."
    ),
    "what is ringlypro.com?": (
        "RinglyPro.com is an AI-powered business assistant built for solo professionals and service-based businesses. It acts as your 24/7 receptionist, scheduler, and communication hub, helping you handle calls, book appointments, follow up with leads, and automate your entire sales and communication process."
    ),
    "tell me about ringlypro": (
        "RinglyPro.com is an AI-powered business assistant built for solo professionals and service-based businesses. It acts as your 24/7 receptionist, scheduler, and communication hub, helping you handle calls, book appointments, follow up with leads, and automate your entire sales and communication process."
    ),

    # AI Phone Assistant
    "what does the ai phone assistant do?": (
        "The AI assistant answers calls 24/7 with a friendly, professional voice. It can respond to FAQs, capture lead info, book appointments, and follow up via SMS or email when calls are missed. It speaks both English and Spanish."
    ),
    "how does the phone assistant work?": (
        "The AI assistant answers calls 24/7 with a friendly, professional voice. It can respond to FAQs, capture lead info, book appointments, and follow up via SMS or email when calls are missed. It speaks both English and Spanish."
    ),
    "ai phone features": (
        "The AI assistant answers calls 24/7 with a friendly, professional voice. It can respond to FAQs, capture lead info, book appointments, and follow up via SMS or email when calls are missed. It speaks both English and Spanish."
    ),

    # Scheduling
    "how does appointment scheduling work?": (
        "RinglyPro syncs with your Google or Outlook calendar. Clients can book through phone, text, or your website. It automatically sends confirmations and reminders to reduce no-shows and booking conflicts."
    ),
    "how do i schedule appointments?": (
        "RinglyPro syncs with your Google or Outlook calendar. Clients can book through phone, text, or your website. It automatically sends confirmations and reminders to reduce no-shows and booking conflicts."
    ),
    "appointment booking": (
        "RinglyPro syncs with your Google or Outlook calendar. Clients can book through phone, text, or your website. It automatically sends confirmations and reminders to reduce no-shows and booking conflicts."
    ),

    # Follow-ups
    "can ringlypro send follow-ups?": (
        "Yes. It can send SMS and email follow-ups with quotes, pricing, directions, and more. It also answers common questions using AI and allows you to jump into any conversation at any time."
    ),
    "how do follow-ups work?": (
        "Yes. It can send SMS and email follow-ups with quotes, pricing, directions, and more. It also answers common questions using AI and allows you to jump into any conversation at any time."
    ),
    "automatic follow-ups": (
        "Yes. It can send SMS and email follow-ups with quotes, pricing, directions, and more. It also answers common questions using AI and allows you to jump into any conversation at any time."
    ),

    # Smart AI Agent
    "what is the smart ai agent feature?": (
        "The Smart AI Agent can understand natural language voice commands like: 'Send a text to Lisa, email the quote to Joe, and remind me at 3PM.' It can execute multiple tasks from one sentence. Emotion detection and predictive follow-up are also in development."
    ),
    "smart ai agent": (
        "The Smart AI Agent can understand natural language voice commands like: 'Send a text to Lisa, email the quote to Joe, and remind me at 3PM.' It can execute multiple tasks from one sentence. Emotion detection and predictive follow-up are also in development."
    ),
    "voice commands": (
        "The Smart AI Agent can understand natural language voice commands like: 'Send a text to Lisa, email the quote to Joe, and remind me at 3PM.' It can execute multiple tasks from one sentence. Emotion detection and predictive follow-up are also in development."
    ),

    # CRM
    "does it include crm capabilities?": (
        "Yes. You can track leads and clients in a visual pipeline, automate follow-ups, onboarding, and nurture campaigns, and trigger actions based on calls, form submissions, or new leads."
    ),
    "crm features": (
        "Yes. You can track leads and clients in a visual pipeline, automate follow-ups, onboarding, and nurture campaigns, and trigger actions based on calls, form submissions, or new leads."
    ),
    "lead management": (
        "Yes. You can track leads and clients in a visual pipeline, automate follow-ups, onboarding, and nurture campaigns, and trigger actions based on calls, form submissions, or new leads."
    ),

    # Website Builder
    "can i build landing pages and forms with ringlypro?": (
        "Yes. RinglyPro includes a website and funnel builder to help you create landing pages, lead capture forms, and automate responses and bookings based on form submissions."
    ),
    "website builder": (
        "Yes. RinglyPro includes a website and funnel builder to help you create landing pages, lead capture forms, and automate responses and bookings based on form submissions."
    ),
    "landing pages": (
        "Yes. RinglyPro includes a website and funnel builder to help you create landing pages, lead capture forms, and automate responses and bookings based on form submissions."
    ),

    # Reporting
    "what kind of reporting does ringlypro offer?": (
        "You can view call history, SMS conversations, bookings, and campaign results. Analytics help you understand what's working and where to focus."
    ),
    "analytics and reporting": (
        "You can view call history, SMS conversations, bookings, and campaign results. Analytics help you understand what's working and where to focus."
    ),
    "call history": (
        "You can view call history, SMS conversations, bookings, and campaign results. Analytics help you understand what's working and where to focus."
    ),

    # Industries
    "what industries is ringlypro best for?": (
        "It's designed for solo professionals including contractors, realtors, wellness providers, legal professionals, and more."
    ),
    "who should use ringlypro?": (
        "It's designed for solo professionals including contractors, realtors, wellness providers, legal professionals, and more."
    ),
    "target audience": (
        "It's designed for solo professionals including contractors, realtors, wellness providers, legal professionals, and more."
    ),

    # Benefits
    "what are the main benefits of ringlypro?": (
        "24/7 coverage so you never miss a lead, all-in-one platform for calls, bookings, CRM, and automations, smarter communication where AI handles routine tasks while you focus on important conversations, more sales with less work through instant and consistent follow-ups, access anywhere from desktop or mobile, and custom AI experience tailored for professionals."
    ),
    "benefits of ringlypro": (
        "24/7 coverage so you never miss a lead, all-in-one platform for calls, bookings, CRM, and automations, smarter communication where AI handles routine tasks while you focus on important conversations, more sales with less work through instant and consistent follow-ups, access anywhere from desktop or mobile, and custom AI experience tailored for professionals."
    ),
    "why choose ringlypro?": (
        "24/7 coverage so you never miss a lead, all-in-one platform for calls, bookings, CRM, and automations, smarter communication where AI handles routine tasks while you focus on important conversations, more sales with less work through instant and consistent follow-ups, access anywhere from desktop or mobile, and custom AI experience tailored for professionals."
    ),

    # Getting Started
    "how do i get started with ringlypro?": (
        "Visit RinglyPro.com to sign up, schedule an onboarding call, or start a free trial."
    ),
    "how to get started": (
        "Visit RinglyPro.com to sign up, schedule an onboarding call, or start a free trial."
    ),
    "sign up process": (
        "Visit RinglyPro.com to sign up, schedule an onboarding call, or start a free trial."
    ),
    "how do i sign up?": (
        "Visit RinglyPro.com to sign up, schedule an onboarding call, or start a free trial."
    ),

    # Spanish versions for key questions
    "¿qué es ringlypro?": (
        "RinglyPro.com es un asistente empresarial impulsado por IA construido para profesionales independientes y empresas de servicios. Actúa como tu recepcionista 24/7, programador y centro de comunicación, ayudándote a manejar llamadas, reservar citas, hacer seguimiento a clientes potenciales y automatizar todo tu proceso de ventas y comunicación."
    ),
    "¿cómo empiezo?": (
        "Visita RinglyPro.com para registrarte, programar una llamada de incorporación o comenzar una prueba gratuita."
    ),
    "¿qué hace el asistente telefónico ai?": (
        "El asistente AI responde llamadas 24/7 con una voz amigable y profesional. Puede responder preguntas frecuentes, capturar información de clientes potenciales, reservar citas y hacer seguimiento vía SMS o email cuando se pierden llamadas. Habla tanto inglés como español."
    )
}

# HTML template with browser-based speech recognition and synthesis
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <title>Talk to RinglyPro AI — Your Business Assistant</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet" />
  <style>
    * { box-sizing: border-box; }

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
    }

    .error-message.show {
      opacity: 1;
      transform: translateY(0);
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

    /* Accessibility improvements */
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
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
    
    <div id="status" class="status-ready">🎙️ Tap to talk to Lina</div>
    
    <div class="controls">
      <button id="stopBtn" class="control-btn" disabled>⏹️ Stop</button>
      <button id="clearBtn" class="control-btn">🗑️ Clean</button>
    </div>

    <div id="errorMessage" class="error-message"></div>
    
    <div class="powered-by">
      Powered by
      <div class="claude-badge">
        <div class="ai-indicator"></div>
        Claude AI Sonnet 4
      </div>
    </div>
  </div>

  <script>
    class LinaVoiceBot {
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
        this.currentLanguage = 'en-US';
        this.recognition = null;
        this.synthesis = window.speechSynthesis;
        
        this.init();
      }

      init() {
        this.checkBrowserSupport();
        this.setupEventListeners();
        this.initSpeechRecognition();
      }

      checkBrowserSupport() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
          this.showError('Tu navegador no soporta reconocimiento de voz. Usa Chrome o Edge para mejor experiencia.');
          return false;
        }
        
        if (!('speechSynthesis' in window)) {
          this.showError('Tu navegador no soporta síntesis de voz.');
          return false;
        }
        
        return true;
      }

      initSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        this.recognition.continuous = false;
        this.recognition.interimResults = false;
        this.recognition.lang = this.currentLanguage;
        this.recognition.maxAlternatives = 1;

        this.recognition.onstart = () => {
          this.isListening = true;
          this.updateUI('listening');
          this.voiceVisualizer.classList.add('active');
        };

        this.recognition.onresult = (event) => {
          const transcript = event.results[0][0].transcript.trim();
          console.log('Transcript:', transcript);
          this.processTranscript(transcript);
        };

        this.recognition.onerror = (event) => {
          console.error('Speech recognition error:', event.error);
          this.handleError('Error en reconocimiento de voz: ' + event.error);
        };

        this.recognition.onend = () => {
          this.isListening = false;
          this.voiceVisualizer.classList.remove('active');
          this.stopBtn.disabled = true;
        };
      }

      setupEventListeners() {
        this.micBtn.addEventListener('click', () => this.toggleListening());
        this.stopBtn.addEventListener('click', () => this.stopListening());
        this.clearBtn.addEventListener('click', () => this.clearAll());
        
        this.langBtns.forEach(btn => {
          btn.addEventListener('click', (e) => this.changeLanguage(e.target.dataset.lang));
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
          if (e.code === 'Space' && !this.isListening && !this.isProcessing) {
            e.preventDefault();
            this.startListening();
          }
        });

        document.addEventListener('keyup', (e) => {
          if (e.code === 'Space' && this.isListening) {
            e.preventDefault();
            this.stopListening();
          }
        });
      }

      changeLanguage(lang) {
        this.currentLanguage = lang;
        this.recognition.lang = lang;
        
        this.langBtns.forEach(btn => {
          btn.classList.toggle('active', btn.dataset.lang === lang);
        });

        const isSpanish = lang === 'es-ES';
        this.updateStatus(isSpanish ? '🎙️ Toca para hablar con RinglyPro AI' : '🎙️ Tap to speak with RinglyPro AI');
      }

      toggleListening() {
        if (this.isListening) {
          this.stopListening();
        } else {
          this.startListening();
        }
      }

      startListening() {
        if (this.isProcessing) return;
        
        try {
          this.clearError();
          this.recognition.start();
          this.stopBtn.disabled = false;
          
          const isSpanish = this.currentLanguage === 'es-ES';
          this.updateStatus(isSpanish ? '🎙️ Escuchando... Habla ahora' : '🎙️ Listening... Speak now');
        } catch (error) {
          this.handleError('Error al iniciar reconocimiento: ' + error.message);
        }
      }

      stopListening() {
        if (this.isListening) {
          this.recognition.stop();
        }
      }

      async processTranscript(transcript) {
        if (!transcript || transcript.length < 2) {
          const isSpanish = this.currentLanguage === 'es-ES';
          this.handleError(isSpanish ? 'No se detectó speech válido' : 'No valid speech detected');
          return;
        }

        this.isProcessing = true;
        this.updateUI('processing');
        
        const isSpanish = this.currentLanguage === 'es-ES';
        this.updateStatus(isSpanish ? '🤖 RinglyPro AI está pensando...' : '🤖 RinglyPro AI is thinking...');

        try {
          const response = await fetch('/process-text', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              text: transcript,
              language: this.currentLanguage
            })
          });

          if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
          }

          const data = await response.json();
          this.speakResponse(data.response);

        } catch (error) {
          console.error('Processing error:', error);
          const errorMsg = isSpanish ? 'Error procesando respuesta' : 'Error processing response';
          this.handleError(errorMsg + ': ' + error.message);
        }
      }

      speakResponse(text) {
        this.synthesis.cancel(); // Clear any pending speech
        
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = this.currentLanguage;
        utterance.rate = 0.9;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;

        // Choose appropriate voice
        const voices = this.synthesis.getVoices();
        const preferredVoice = voices.find(voice => 
          voice.lang.startsWith(this.currentLanguage.split('-')[0]) && 
          (voice.name.includes('Natural') || voice.name.includes('Neural') || voice.localService)
        );
        
        if (preferredVoice) {
          utterance.voice = preferredVoice;
        }

        utterance.onstart = () => {
          this.updateUI('speaking');
          const isSpanish = this.currentLanguage === 'es-ES';
          this.updateStatus(isSpanish ? '🔊 RinglyPro AI está hablando...' : '🔊 RinglyPro AI is speaking...');
        };

        utterance.onend = () => {
          this.isProcessing = false;
          this.updateUI('ready');
          const isSpanish = this.currentLanguage === 'es-ES';
          this.updateStatus(isSpanish ? '🎙️ Toca para hablar con RinglyPro AI' : '🎙️ Tap to speak with RinglyPro AI');
        };

        utterance.onerror = (error) => {
          console.error('Speech synthesis error:', error);
          this.handleError('Error en síntesis de voz');
          this.isProcessing = false;
          this.updateUI('ready');
        };

        this.synthesis.speak(utterance);
      }

      updateUI(state) {
        this.micBtn.className = 'mic-button';
        this.status.className = '';
        
        switch (state) {
          case 'listening':
            this.micBtn.classList.add('listening');
            this.status.classList.add('status-listening');
            break;
          case 'processing':
            this.micBtn.classList.add('processing');
            this.status.classList.add('status-processing');
            break;
          case 'speaking':
            this.status.classList.add('status-speaking');
            break;
          case 'ready':
          default:
            this.status.classList.add('status-ready');
            break;
        }
      }

      updateStatus(message) {
        this.status.textContent = message;
      }

      handleError(message) {
        this.showError(message);
        this.isProcessing = false;
        this.isListening = false;
        this.updateUI('ready');
        this.voiceVisualizer.classList.remove('active');
        
        const isSpanish = this.currentLanguage === 'es-ES';
        setTimeout(() => {
          this.updateStatus(isSpanish ? '🎙️ Toca para hablar con RinglyPro AI' : '🎙️ Tap to speak with RinglyPro AI');
        }, 3000);
      }

      showError(message) {
        this.errorMessage.textContent = message;
        this.errorMessage.classList.add('show');
        
        setTimeout(() => {
          this.clearError();
        }, 5000);
      }

      clearError() {
        this.errorMessage.classList.remove('show');
      }

      clearAll() {
        this.synthesis.cancel();
        if (this.isListening) {
          this.recognition.stop();
        }
        this.isProcessing = false;
        this.isListening = false;
        this.updateUI('ready');
        this.voiceVisualizer.classList.remove('active');
        this.clearError();
        
        const isSpanish = this.currentLanguage === 'es-ES';
        this.updateStatus(isSpanish ? '🎙️ Toca para hablar con RinglyPro AI' : '🎙️ Tap to speak with RinglyPro AI');
      }
    }

    // Initialize the voice bot when the page loads
    document.addEventListener('DOMContentLoaded', () => {
      // Wait for voices to load
      if (speechSynthesis.onvoiceschanged !== undefined) {
        speechSynthesis.onvoiceschanged = () => {
          new LinaVoiceBot();
        };
      } else {
        new LinaVoiceBot();
      }
    });
  </script>
</body>
</html>
"""

def get_claude_response(user_message, language_context=""):
    """
    Get response from Claude AI with emotional intelligence and context awareness
    """
    system_prompt =     """You are RinglyPro AI, a warm, empathetic, and highly knowledgeable AI assistant specializing in business automation and communication solutions for solo professionals and service-based businesses.

Your personality traits:
- Emotionally intelligent and empathetic
- Warm and friendly, like talking to a helpful business advisor
- Professional but approachable
- Knowledgeable about business automation, lead management, and communication systems
- Supportive and encouraging
- Culturally sensitive and bilingual (English/Spanish)

Key guidelines:
- Always respond in the same language the user spoke in
- Keep responses conversational and under 80 words for voice interaction
- Show emotional understanding and validation
- Provide specific, actionable information about RinglyPro services
- If you don't know something specific, be honest but offer to help connect them with more information
- Use encouraging and positive language
- Address solo professionals and service business owners appropriately
- Be natural and conversational, avoid robotic responses

About RinglyPro.com:
- AI-powered business assistant for solo professionals and service-based businesses
- 24/7 AI phone receptionist, scheduler, and communication hub
- Handles calls, books appointments, follows up with leads automatically
- Includes CRM, website builder, analytics, and automation tools
- Bilingual AI assistant (English/Spanish)
- Syncs with Google/Outlook calendars
- Smart AI agent with natural language voice commands
- Built for contractors, realtors, wellness providers, legal professionals, and more
- Automates entire sales and communication process

Remember to be emotionally supportive, understanding, and genuinely helpful in every interaction."""

    try:
        message = claude_client.messages.create(
            model="claude-sonnet-4-20250514",  # Latest Claude Sonnet 4
            max_tokens=250,
            temperature=0.8,  # More natural and conversational
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"{language_context}\n\nUser message: {user_message}"
                }
            ]
        )
        
        response_text = message.content[0].text.strip()
        
        # Ensure response is appropriate length for voice
        if len(response_text) > 400:
            response_text = response_text[:397] + "..."
            
        return response_text
        
    except Exception as e:
        logging.error(f"❌ Claude API error: {e}")
        # Fallback response based on language
        if "spanish" in user_message.lower() or any(word in user_message.lower() for word in ['qué', 'cómo', 'dónde', 'cuándo']):
            return "Lo siento, tuve un problema técnico. Por favor intenta de nuevo en un momento."
        else:
            return "I'm sorry, I had a technical issue. Please try again in a moment."

def detect_language(text):
    """Enhanced language detection"""
    spanish_indicators = [
        'qué', 'cómo', 'dónde', 'cuándo', 'por', 'para', 'con', 'sin', 'muy', 'más', 
        'es', 'la', 'el', 'de', 'en', 'y', 'a', 'que', 'se', 'no', 'un', 'una',
        'pero', 'como', 'su', 'me', 'le', 'te', 'nos', 'los', 'las', 'del', 'al'
    ]
    
    text_lower = text.lower()
    spanish_count = sum(1 for word in spanish_indicators if f' {word} ' in f' {text_lower} ')
    
    # Also check for Spanish characters
    spanish_chars = sum(1 for char in text if char in 'ñáéíóúü')
    
    return "spanish" if (spanish_count > 1 or spanish_chars > 0) else "english"

@app.route('/')
def serve_index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/process-text', methods=['POST'])
def process_text():
    logging.info("📥 Received text processing request")
    
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({"error": "Missing text data"}), 400
            
        user_text = data['text'].strip()
        user_language = data.get('language', 'es-ES')
        
        if not user_text or len(user_text) < 2:
            error_msg = ("Texto muy corto. Por favor intenta de nuevo." 
                        if user_language.startswith('es') 
                        else "Text too short. Please try again.")
            return jsonify({"error": error_msg}), 400
        
        logging.info(f"📝 Processing text: {user_text}")
        logging.info(f"🌐 Language: {user_language}")
        
        # Step 1: Enhanced FAQ matching
        user_text_lower = user_text.lower()
        response_text = None
        
        # Try exact and fuzzy matching
        matched = get_close_matches(user_text_lower, FAQ_BRAIN.keys(), n=1, cutoff=0.5)
        
        if matched:
            response_text = FAQ_BRAIN[matched[0]]
            logging.info(f"🤖 Matched FAQ: {matched[0]}")
        else:
            # Step 2: Fallback to Claude AI with emotional intelligence
            language_context = f"Please respond in {'Spanish' if user_language.startswith('es') else 'English'}."
            
            try:
                response_text = get_claude_response(user_text, language_context)
                logging.info(f"🧠 Claude Response: {response_text}")
            except Exception as e:
                logging.error(f"❌ Claude API error: {e}")
                fallback_msg = ("Lo siento, tuve un problema técnico. Por favor intenta de nuevo." 
                              if user_language.startswith('es') 
                              else "I'm sorry, I had a technical issue. Please try again.")
                return jsonify({"error": fallback_msg}), 500
        
        return jsonify({
            "response": response_text,
            "language": user_language,
            "matched_faq": bool(matched)
        })
        
    except Exception as e:
        logging.error(f"❌ Text processing error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "claude_api": "connected" if anthropic_api_key else "missing",
        "timestamp": time.time(),
        "features": [
            "Claude Sonnet 4 AI",
            "Browser Speech Recognition",
            "Browser Speech Synthesis",
            "Bilingual Support",
            "FAQ Matching",
            "Emotional Intelligence"
        ]
    })

@app.route('/voices')
def get_voices():
    """Endpoint to help debug voice availability"""
    return jsonify({
        "message": "Use browser console: speechSynthesis.getVoices()",
        "tip": "This endpoint helps developers check available voices in browser"
    })

if __name__ == "__main__":
    # Verify Claude API on startup
    try:
        # Test Claude API
        test_claude = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hello"}]
        )
        logging.info("✅ Claude API connection successful")
        
    except Exception as e:
        logging.error(f"❌ Claude API connection test failed: {e}")
        print("⚠️  Warning: Claude API connection not verified. Check your API key.")
    
    print("🚀 Starting RinglyPro AI Voice Assistant...")
    print("🎯 Features:")
    print("   • Claude Sonnet 4 for emotional intelligence")
    print("   • Browser Speech Recognition (fast & free)")
    print("   • Browser Speech Synthesis (natural voices)")
    print("   • Bilingual support (English/Spanish)")
    print("   • Embedded HTML interface")
    print("   • Enhanced FAQ matching for RinglyPro.com")
    print("   • Zero OpenAI dependency")
    print("\n📋 Required environment variables:")
    print("   • ANTHROPIC_API_KEY")
    print("\n🌐 Access the voice assistant at: http://localhost:5000")
    print("\n📱 Browser Support:")
    print("   • Chrome/Edge: Full support")
    print("   • Firefox: Limited voice options")
    print("   • Safari: Basic support")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
