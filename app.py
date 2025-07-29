from flask import Flask, request, jsonify, render_template_string, session
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import phonenumbers
from phonenumbers import NumberParseException
from twilio.rest import Client
import anthropic
import os
import logging
from dotenv import load_dotenv
from difflib import get_close_matches
import json
import time
import base64
import asyncio
from datetime import datetime

# Import our new modules
from enhanced_tts import tts_engine
from speech_optimized_claude import get_enhanced_claude_response

# Load environment variables
load_dotenv()

# SMS/Phone Helper Functions
def validate_phone_number(phone_str):
    """Validate and format phone number"""
    try:
        # Parse the number (assuming US if no country code)
        number = phonenumbers.parse(phone_str, "US")
        
        # Check if valid
        if phonenumbers.is_valid_number(number):
            # Return formatted number
            return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
        else:
            return None
    except NumberParseException:
        return None

def send_sms_notification(customer_phone, customer_question):
    """Send SMS notification to customer service"""
    try:
        client = Client(
            os.getenv('TWILIO_ACCOUNT_SID'),
            os.getenv('TWILIO_AUTH_TOKEN')
        )
        
        message_body = f"""
New customer inquiry:
Phone: {customer_phone}
Question: {customer_question}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()
        
        message = client.messages.create(
            body=message_body,
            from_=os.getenv('TWILIO_PHONE_NUMBER'),
            to='+16566001400'
        )
        
        return True, message.sid
    except Exception as e:
        return False, str(e)

def is_no_answer_response(response):
    """Check if the FAQ response indicates no answer was found"""
    no_answer_indicators = [
        "I don't have information",
        "couldn't find a direct answer",
        "please contact our customer service",
        "I don't have a specific answer",
        "contact our support team"
    ]
    return any(indicator in response.lower() for indicator in no_answer_indicators)

# API Keys validation
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

if not anthropic_api_key:
    raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

# Setup Flask
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-default-secret-key-change-this')
CORS(app)

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Your existing FAQ_BRAIN (keep this unchanged)
FAQ_BRAIN = {
    # Basic Platform Information
    "what is ringlypro?": "RinglyPro.com is a 24/7 AI-powered call answering and client booking service designed for small businesses and professionals. It ensures you never miss a call by providing automated phone answering, appointment scheduling, and customer communication through AI technology.",

    "what does ringlypro do?": "RinglyPro provides 24/7 answering service, bilingual virtual receptionists (English/Spanish), AI-powered chat and text messaging, missed-call text-back, appointment scheduling, and integrations with existing business apps like CRMs and calendars.",

    "who owns ringlypro?": "RinglyPro.com is owned and operated by DIGIT2AI LLC, a company focused on building technology solutions that create better business opportunities.",

    # Core Features
    "what are ringlypro main features?": "Key features include: 24/7 AI call answering, bilingual virtual receptionists, AI-powered chat & text, missed-call text-back, appointment scheduling, CRM integrations, call recording, automated booking tools, and mobile app access.",

    "does ringlypro support multiple languages?": "Yes, RinglyPro offers bilingual virtual receptionists that provide professional support in both English and Spanish to help businesses serve a wider audience.",

    "can ringlypro integrate with my existing tools?": "Yes, RinglyPro integrates seamlessly with existing CRMs, schedulers, calendars, and other business apps. Integration is available through online links or using Zapier for broader connectivity.",

    "does ringlypro offer appointment scheduling?": "Yes, clients can schedule appointments through phone, text, or online booking. All appointments sync with your existing calendar system for easy management.",

    # Pricing & Plans
    "how much does ringlypro cost?": "RinglyPro offers three pricing tiers: scheduling assistant ($97 permonth), Office Manager ($297 permonth), and marketing director ($497per month). Each plan includes different amounts of minutes, text messages, and online replies.",

    "what is included in the starter plan?": "The scheduling assistant plan ($49 per month) includes 1,000 minutes, 1,000 text messages, 1,000 online replies, self-guided setup, email support, premium voice options, call forwarding/porting, toll-free numbers, call recording, and automated booking tools.",

    "what is included in the office manager plan?": "The Office Manager plan ($297 per month) includes 3,000 minutes, 3,000 texts, 3,000 online replies, all Starter features plus assisted onboarding, phone/email/text support, custom voice choices, live call queuing, Zapier integrations, CRM setup, invoice automation, payment gateway setup, and mobile app.",

    "what is included in the business growth plan?": "The Marketing Director plan ($497 per month) includes 7,500 minutes, 7,500 texts, 7,500 online replies, everything in Office Manager plus professional onboarding, dedicated account manager, custom integrations, landing page design, lead capture automation, Google Ads campaign, email marketing, reputation management, conversion reporting, and monthly analytics.",

    "are there setup fees?": "Setup fees are not explicitly mentioned in the pricing. The Starter plan includes self-guided setup, while higher tiers include assisted onboarding and professional setup services.",

    "can i choose annual vs monthly billing?": "Yes, RinglyPro allows you to decide on billing frequency, offering both annual and monthly billing options.",

    # Technical Capabilities
    "what is missed-call text-back?": "Missed-call text-back is a feature that instantly re-engages callers you couldn't answer by automatically sending them a text message, keeping conversations and opportunities alive.",

    "does ringlypro record calls?": "Yes, call recording is available as a feature across all plans, allowing you to review conversations and maintain records of customer interactions.",

    "can i get a toll-free number?": "Yes, RinglyPro offers toll-free numbers and vanity numbers as part of their service options.",

    "does ringlypro have a mobile app?": "Yes, a mobile app is included with the Office Manager and Business Growth plans, allowing you to manage your service on the go.",

    # Setup & Onboarding
    "how do i get started with ringlypro?": "Getting started involves 4 steps: 1) Choose your plan based on call/text volume and support needs, 2) Decide on billing frequency, 3) Set up your account and choose your number through onboarding, 4) Launch your service with automated calls, texts, and appointment tools.",

    "what kind of support does ringlypro offer?": "Support varies by plan: Starter includes email support, Office Manager includes phone/email/text support, and Business Growth includes a dedicated account manager plus professional onboarding services.",

    "how long does setup take?": "The timeline isn't specified, but setup options range from self-guided (Starter) to assisted onboarding (Office Manager) to professional onboarding services (Business Growth).",

    # Business Benefits
    "how does ringlypro help my business?": "RinglyPro helps by ensuring you never miss calls, providing 24/7 availability, automating appointment scheduling, offering bilingual support to reach more customers, integrating with existing tools, and providing analytics to track performance.",

    "what types of businesses use ringlypro?": "RinglyPro is designed for small businesses, solo professionals, service-based businesses, and any business that needs reliable call answering and appointment scheduling services.",

    "can ringlypro help with lead generation?": "Yes, especially with higher-tier plans that include lead capture automation, Google Ads campaigns, email marketing, and lead conversion reporting.",

    # Customer Service & Contact
    "how can i contact ringlypro support?": "You can contact RinglyPro customer service at (656) 213-3300 or via email. The level of support (email, phone, text) depends on your plan level.",

    "what are ringlypro business hours?": "RinglyPro provides 24/7 service availability. Their experts are available around the clock to support and grow your business.",

    "where can i find ringlypro terms of service?": "Terms of service and privacy policy information can be found on their website. The service is provided by DIGIT2AI LLC.",

    # Competitive Advantages
    "what makes ringlypro different?": "RinglyPro stands out with its combination of AI-powered automation, bilingual support, comprehensive integrations, multiple communication channels (phone, text, chat), and scalable plans with dedicated support options.",

    "does ringlypro offer custom solutions?": "Yes, the Business Growth plan includes custom integrations for advanced workflows, and they offer custom solutions tailored to specific business needs.",

    # Technical Support
    "what happens if i exceed my plan limits?": "The plans include specific amounts of minutes, text messages, and online replies. Contact their support team to discuss options if you regularly exceed your plan limits.",

    "can i upgrade or downgrade my plan?": "While not explicitly stated, most subscription services allow plan changes. Contact RinglyPro support to discuss plan modifications based on your changing needs.",

    "does ringlypro offer analytics?": "Yes, monthly analytics reporting is included with the Business Growth plan, and conversion reporting helps track lead performance.",

    # Integration & Compatibility
    "what crms does ringlypro work with?": "RinglyPro mentions working with CRMs and offers CRM setup for small businesses. They integrate through online links and Zapier, which supports hundreds of popular CRM systems.",

    "can ringlypro integrate with zapier?": "Yes, Zapier integration is available with the Office Manager and Business Growth plans, allowing connection to thousands of business applications.",

    "does ringlypro work with stripe?": "Yes, Stripe/Payment Gateway Setup is included in the Office Manager and Business Growth plans.",

    # AI Capabilities
    "how smart is ringlypro ai?": "RinglyPro uses AI-powered chat and text to streamline and tailor customer conversations with intelligent automation. The AI handles call answering, appointment scheduling, and customer communications.",

    "can the ai handle complex questions?": "While specific AI capabilities aren't detailed, the service includes escalation to human support and various plan tiers offer different levels of human assistance for complex situations.",

    "does ringlypro ai learn from interactions?": "The system uses AI-powered automation, though specific machine learning capabilities aren't detailed in available information. Contact their support for technical details about AI improvement over time."
}

# Original voice FAQ function (unchanged)
def get_faq_response(user_text: str) -> tuple[str, bool]:
    """
    Check for FAQ matches with fuzzy matching and web scraping
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
    
    # Try web scraping RinglyPro.com
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; FAQ-Bot)'}
        response = requests.get("https://RinglyPro.com", headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text()
            if len(text) > 100:
                return "Based on information from our website: I found some relevant content that might help. For more specific assistance, please contact our support team.", True
    except:
        pass
    
    # Fallback to customer service
    return "I don't have a specific answer to that question. Please contact our Customer Service team for specialized assistance.", True

# NEW: SMS-enabled FAQ function for text chat
def get_faq_response_with_sms(user_text: str) -> tuple[str, bool, bool]:
    """
    Check for FAQ matches with SMS phone collection capability
    Returns: (response_text, is_faq_match, needs_phone_collection)
    """
    user_text_lower = user_text.lower().strip()
    
    # Try exact match first
    if user_text_lower in FAQ_BRAIN:
        return FAQ_BRAIN[user_text_lower], True, False
    
    # Try fuzzy matching
    matched = get_close_matches(user_text_lower, FAQ_BRAIN.keys(), n=1, cutoff=0.6)
    if matched:
        return FAQ_BRAIN[matched[0]], True, False
    
    # Try web scraping RinglyPro.com
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; FAQ-Bot)'}
        response = requests.get("https://RinglyPro.com", headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text()
            if len(text) > 100:
                # Return with phone collection since this is a generic response
                return "I found some information on our website that might be related, but I'd like to connect you with our customer service team for personalized assistance with your specific question. Could you please provide your phone number so they can reach out to help you?", False, True
    except:
        pass
    
    # Fallback to customer service with phone collection
    return "I don't have a specific answer to that question. I'd like to connect you with our customer service team. Could you please provide your phone number so they can reach out to help you?", False, True

# ORIGINAL VOICE INTERFACE HTML (unchanged)
VOICE_HTML_TEMPLATE = '''
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

    .interface-switcher {
      position: absolute;
      top: 20px;
      right: 20px;
      background: rgba(255, 255, 255, 0.2);
      border: none;
      border-radius: 15px;
      color: white;
      padding: 0.5rem 1rem;
      cursor: pointer;
      font-size: 0.8rem;
      transition: all 0.3s ease;
    }

    .interface-switcher:hover {
      background: rgba(255, 255, 255, 0.3);
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
      left: 20px;
      background: rgba(76, 175, 80, 0.9);
      color: white;
      padding: 0.75rem 1rem;
      border-radius: 20px;
      font-size: 0.8rem;
      z-index: 1000;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      animation: slideInLeft 0.3s ease;
    }

    @keyframes slideInLeft {
      from { transform: translateX(-100%); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
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

      .interface-switcher {
        top: 10px;
        right: 10px;
        font-size: 0.7rem;
        padding: 0.4rem 0.8rem;
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
    <button class="interface-switcher" onclick="window.location.href='/chat'">💬 Try Text Chat</button>
    
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
            this.audioURLs = new Set();
            
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

            try {
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
                debugLog('Audio context initialized:', this.audioContext.state);
                
                if (this.isMobile) {
                    debugLog('📱 Setting up mobile audio environment...');
                    
                    const unlockAudio = async () => {
                        try {
                            if (this.audioContext.state === 'suspended') {
                                await this.audioContext.resume();
                                debugLog('📱 Audio context resumed');
                            }
                            
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
                this.setupMobileAudioOptimizations();
            } else {
                this.initSpeechRecognition();
                this.userInteracted = true;
                this.updateStatus('🎙️ Click the microphone to start');
            }
        }

        setupMobileAudioOptimizations() {
            debugLog('📱 Setting up mobile audio optimizations...');
            
            let lastTouchEnd = 0;
            document.addEventListener('touchend', (event) => {
                const now = Date.now();
                if (now - lastTouchEnd <= 300) {
                    event.preventDefault();
                }
                lastTouchEnd = now;
            }, false);
            
            const viewport = document.querySelector('meta[name=viewport]');
            if (viewport) {
                viewport.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover');
            }
            
            this.showMobileAudioStatus();
        }

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

        resetMobileAudioState() {
            if (this.isMobile) {
                debugLog('📱 Resetting mobile audio state...');
                
                speechSynthesis.cancel();
                
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
                
                this.audioURLs.forEach(url => {
                    try {
                        URL.revokeObjectURL(url);
                    } catch (error) {
                        debugLog('📱 URL cleanup error (non-critical):', error);
                    }
                });
                this.audioURLs.clear();
                
                if (this.audioContext && this.audioContext.state === 'suspended') {
                    this.audioContext.resume().catch(error => {
                        debugLog('📱 Audio context resume error:', error);
                    });
                }
                
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

        async playPremiumAudio(audioBase64, responseText) {
            try {
                if (this.recognition && this.isListening) {
                    this.recognition.stop();
                    debugLog('🔇 Stopped speech recognition during audio');
                }
                
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
                
                this.audioURLs.add(audioUrl);
                
                this.currentAudio = new Audio();
                
                if (this.isMobile) {
                    debugLog('📱 Configuring for mobile device...');
                    this.currentAudio.crossOrigin = 'anonymous';
                    this.currentAudio.preload = 'metadata';
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
                    let hasResolved = false;
                    
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
                        }, 8000);
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
                        
                        speechSynthesis.cancel();
                        debugLog('🔇 CANCELLED speech synthesis - premium audio is playing');
                    };
                    
                    this.currentAudio.onended = () => {
                        debugLog('📱 Mobile premium audio ended');
                        this.audioFinished();
                        
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
                        
                        debugLog('📱 Premium audio failed, using TTS fallback');
                        
                        if (!hasResolved) {
                            this.playEnhancedBrowserTTS(responseText, 'neutral').then(resolveOnce);
                        }
                    };
                    
                    const playAudio = async () => {
                        try {
                            debugLog('📱 Attempting to play mobile audio...');
                            
                            if (this.audioContext && this.audioContext.state === 'suspended') {
                                await this.audioContext.resume();
                                debugLog('📱 Audio context resumed for mobile');
                            }
                            
                            if (this.isMobile && this.currentAudio.readyState < 2) {
                                debugLog('📱 Waiting for mobile audio to be ready...');
                                await new Promise(resolve => {
                                    const checkReady = () => {
                                        if (this.currentAudio && this.currentAudio.readyState >= 2) {
                                            resolve();
                                        } else if (this.currentAudio) {
                                            setTimeout(checkReady, 100);
                                        } else {
                                            resolve();
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
                    
                    if (this.isMobile) {
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
                return this.playEnhancedBrowserTTS(responseText, 'neutral');
            }
        }

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

        audioFinished() {
            debugLog('📱 Audio playback finished - cleaning up mobile resources');
            this.isPlaying = false;
            this.isProcessing = false;
            this.updateUI('ready');
            
            this.cleanupCurrentAudio();
            
            this.audioURLs.forEach(url => {
                try {
                    URL.revokeObjectURL(url);
                } catch (error) {
                    debugLog('📱 URL cleanup error (non-critical):', error);
                }
            });
            this.audioURLs.clear();
            
            if (this.isMobile) {
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
                
                if (this.isMobile && this.userInteracted) {
                    debugLog('📱 Performing complete mobile reset before new interaction');
                    this.resetMobileAudioState();
                    
                    await new Promise(resolve => setTimeout(resolve, 800));
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
                
                if (this.isMobile && (this.isProcessing || this.isPlaying || this.isListening)) {
                    debugLog('📱 Mobile: Blocking interaction - another process is active');
                    this.updateStatus('📱 Please wait, processing...');
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
            
            if (this.isMobile && this.isListening) {
                debugLog('📱 Mobile: Recognition already active, stopping first...');
                try {
                    this.recognition.stop();
                    await new Promise(resolve => setTimeout(resolve, 300));
                    this.isListening = false;
                } catch (error) {
                    debugLog('📱 Mobile: Error stopping recognition:', error);
                    this.isListening = false;
                }
            }
            
            if (this.isListening) {
                debugLog('📱 Mobile: Still listening, aborting start attempt');
                return;
            }
            
            try {
                this.clearError();
                speechSynthesis.cancel();
                
                debugLog('📱 Mobile: Starting speech recognition...');
                this.recognition.start();
                this.stopBtn.disabled = false;
                
            } catch (error) {
                debugLog('📱 Mobile: Start listening error:', error);
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
            
            this.isProcessing = false;
            this.isListening = false;
            this.isPlaying = false;
            this.updateUI('ready');
            this.voiceVisualizer.classList.remove('active');
            this.clearError();
            this.updateStatus('🎙️ Tap microphone to start');
            
            if (this.isMobile) {
                speechSynthesis.cancel();
                
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

# NEW: Text chat interface with SMS phone collection
CHAT_HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RinglyPro FAQ Assistant</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .chat-container {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            position: relative;
        }
        .interface-switcher {
            position: absolute;
            top: 20px;
            right: 20px;
            background: #2196F3;
            color: white;
            border: none;
            border-radius: 15px;
            padding: 0.5rem 1rem;
            cursor: pointer;
            font-size: 0.8rem;
            transition: all 0.3s ease;
        }
        .interface-switcher:hover {
            background: #1976D2;
        }
        .message {
            margin: 10px 0;
            padding: 10px;
            border-radius: 5px;
        }
        .user-message {
            background-color: #e3f2fd;
            text-align: right;
        }
        .bot-message {
            background-color: #f1f8e9;
        }
        .input-container {
            display: flex;
            margin-top: 20px;
        }
        .input-container input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin-right: 10px;
        }
        .input-container button {
            padding: 10px 20px;
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        .phone-form {
            background-color: #fff3e0;
            border: 2px solid #ff9800;
            border-radius: 5px;
            padding: 15px;
            margin: 10px 0;
        }
        .success-message {
            background-color: #e8f5e8;
            border: 2px solid #4caf50;
            color: #2e7d32;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .error-message {
            background-color: #ffebee;
            border: 2px solid #f44336;
            color: #c62828;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <button class="interface-switcher" onclick="window.location.href='/'">🎤 Try Voice Chat</button>
        
        <h1>RinglyPro FAQ Assistant</h1>
        <div id="chatMessages">
            <div class="message bot-message">
                Hello! I'm your RinglyPro assistant. Ask me anything about our services, pricing, features, or how to get started! If I can't answer your question, I'll connect you with our customer service team.
            </div>
        </div>
        
        <div class="input-container">
            <input type="text" id="userInput" placeholder="Ask a question about RinglyPro..." onkeypress="handleKeyPress(event)">
            <button onclick="sendMessage()">Send</button>
        </div>
    </div>

    <script>
        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }

        function sendMessage() {
            const input = document.getElementById('userInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            // Add user message to chat
            addMessage(message, 'user');
            input.value = '';
            
            // Send to server
            fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            })
            .then(response => response.json())
            .then(data => {
                addMessage(data.response, 'bot');
                
                // Check if phone collection is needed
                if (data.needs_phone_collection) {
                    showPhoneForm();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                addMessage('Sorry, there was an error processing your request.', 'bot');
            });
        }

        function addMessage(message, sender) {
            const chatMessages = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}-message`;
            messageDiv.textContent = message;
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function showPhoneForm() {
            const chatMessages = document.getElementById('chatMessages');
            const phoneFormDiv = document.createElement('div');
            phoneFormDiv.className = 'phone-form';
            phoneFormDiv.innerHTML = `
                <p><strong>📞 Let's get you connected!</strong></p>
                <p>Please enter your phone number so our customer service team can help you:</p>
                <div style="display: flex; gap: 10px; margin-top: 10px;">
                    <input type="tel" id="phoneInput" placeholder="(555) 123-4567" style="flex: 1; padding: 8px;">
                    <button onclick="submitPhone()" style="padding: 8px 15px; background-color: #4caf50; color: white; border: none; border-radius: 3px;">Submit</button>
                </div>
            `;
            chatMessages.appendChild(phoneFormDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            // Focus on phone input
            setTimeout(() => {
                document.getElementById('phoneInput').focus();
            }, 100);
        }

        function submitPhone() {
            const phoneInput = document.getElementById('phoneInput');
            const phoneNumber = phoneInput.value.trim();
            
            if (!phoneNumber) {
                alert('Please enter a phone number.');
                return;
            }
            
            // Send phone number to server
            fetch('/submit_phone', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    phone: phoneNumber,
                    last_question: sessionStorage.getItem('lastQuestion') || 'General inquiry'
                })
            })
            .then(response => response.json())
            .then(data => {
                const chatMessages = document.getElementById('chatMessages');
                
                if (data.success) {
                    const successDiv = document.createElement('div');
                    successDiv.className = 'success-message';
                    successDiv.innerHTML = `
                        <strong>✅ Thank you!</strong><br>
                        ${data.message}
                    `;
                    chatMessages.appendChild(successDiv);
                } else {
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'error-message';
                    errorDiv.innerHTML = `
                        <strong>❌ Error:</strong><br>
                        ${data.message}
                    `;
                    chatMessages.appendChild(errorDiv);
                }
                
                chatMessages.scrollTop = chatMessages.scrollHeight;
            })
            .catch(error => {
                console.error('Error:', error);
                alert('There was an error submitting your phone number. Please try again.');
            });
        }

        // Store last question for context
        document.getElementById('userInput').addEventListener('input', function() {
            sessionStorage.setItem('lastQuestion', this.value);
        });
    </script>
</body>
</html>
'''

# ROUTES

# Original voice interface (unchanged)
@app.route('/')
def serve_index():
    return render_template_string(VOICE_HTML_TEMPLATE)

# NEW: Text chat interface route
@app.route('/chat')
def serve_chat():
    return render_template_string(CHAT_HTML_TEMPLATE)

# NEW: Chat message handling with SMS integration
@app.route('/chat', methods=['POST'])
def handle_chat():
    """Handle chat messages with SMS phone collection"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'response': 'Please enter a question.', 'needs_phone_collection': False})
        
        # Store the question in session for potential phone collection
        session['last_question'] = user_message
        
        # Get FAQ response with SMS capability
        response, is_faq_match, needs_phone_collection = get_faq_response_with_sms(user_message)
        
        return jsonify({
            'response': response,
            'needs_phone_collection': needs_phone_collection,
            'is_faq_match': is_faq_match
        })
        
    except Exception as e:
        logging.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            'response': 'Sorry, there was an error processing your request. Please try again.',
            'needs_phone_collection': False
        }), 500

# NEW: Phone submission endpoint
@app.route('/submit_phone', methods=['POST'])
def submit_phone():
    """Handle phone number submission and send SMS notification"""
    try:
        data = request.get_json()
        phone_number = data.get('phone', '').strip()
        last_question = data.get('last_question', session.get('last_question', 'General inquiry'))
        
        if not phone_number:
            return jsonify({
                'success': False,
                'message': 'Please provide a phone number.'
            })
        
        # Validate phone number
        validated_phone = validate_phone_number(phone_number)
        if not validated_phone:
            return jsonify({
                'success': False,
                'message': 'Please enter a valid phone number (e.g., (555) 123-4567).'
            })
        
        # Send SMS notification
        sms_success, sms_result = send_sms_notification(validated_phone, last_question)
        
        if sms_success:
            logging.info(f"SMS sent successfully to customer service. Customer: {validated_phone}, Question: {last_question}")
            return jsonify({
                'success': True,
                'message': f'Perfect! We\'ve received your phone number ({validated_phone}) and notified our customer service team about your question: "{last_question}". They\'ll reach out to you shortly to provide personalized assistance.'
            })
        else:
            logging.error(f"Failed to send SMS: {sms_result}")
            return jsonify({
                'success': True,  # Still success for user experience
                'message': f'Thank you for providing your phone number ({validated_phone}). We\'ve recorded your inquiry about "{last_question}" and our customer service team will contact you soon.'
            })
            
    except Exception as e:
        logging.error(f"Error in submit_phone endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'There was an error processing your request. Please try again or contact us directly at (656) 213-3300.'
        })

# Original voice processing routes (unchanged)
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
        
        # Backend echo detection
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
        
        # Generate response using original voice FAQ function
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
        
        # MOBILE-OPTIMIZED ELEVENLABS AUDIO
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
                
                mobile_text = response_text.replace("RinglyPro", "Ringly Pro")
                mobile_text = mobile_text.replace("AI", "A.I.")
                mobile_text = mobile_text.replace("$", " dollars")
                mobile_text = mobile_text.replace("&", "and")
                
                logging.info(f"📱 Audio text length: {len(mobile_text)} characters")
                
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
                
                timeout = 8 if is_mobile else 10
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
                    logging.warning(f"📱 ElevenLabs failed: {tts_response.status_code} - {tts_response.text}")
                    
            except requests.exceptions.Timeout:
                logging.warning("📱 ElevenLabs timeout - network issue")
            except Exception as tts_error:
                logging.error(f"📱 ElevenLabs error: {tts_error}")
        else:
            logging.info("📱 No ElevenLabs API key found, using browser TTS")
        
        # Return mobile-optimized response
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
    
    sms_status = {
        "twilio": "available" if os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN") else "missing_keys",
        "phone_validation": "available"
    }
    
    return jsonify({
        "status": "healthy",
        "claude_api": "connected" if anthropic_api_key else "missing",
        "tts_engines": tts_status,
        "sms_integration": sms_status,
        "timestamp": time.time(),
        "features": [
            "🎤 Enhanced Voice Interface with Premium TTS",
            "💬 Text Chat with SMS Integration", 
            "📱 Mobile Premium Audio Support",
            "📞 Phone Number Collection & Validation",
            "📲 SMS Notifications to Customer Service",
            "🔄 Echo Prevention System",
            "🤖 Enhanced Claude Sonnet 4 AI",
            "🌐 Bilingual Support (EN/ES)",
            "🔍 FAQ Matching with Web Scraping",
            "📱 iOS Audio Compatibility",
            "🧹 Mobile State Reset System",
            "💾 Audio Memory Management"
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

    print("🚀 Starting Enhanced RinglyPro AI Assistant with Dual Interface...")
    print("🎯 Enhanced Features:")
    print("   🎤 Premium Voice Interface with ElevenLabs Rachel voice")
    print("   💬 Text Chat Interface with SMS integration")
    print("   📱 Mobile Premium Audio Support (iOS Compatible)")
    print("   📞 Phone number collection & validation")
    print("   📲 SMS notifications to customer service")
    print("   🔇 Echo prevention system (frontend + backend)")
    print("   🎵 Speech-optimized responses")
    print("   📱 Enhanced mobile compatibility")
    print("   🧹 Smart audio fallback & memory management")
    print("\n📋 API Keys Status:")
    print(f"   • Claude API: {'✅ Connected' if anthropic_api_key else '❌ Missing'}")
    print(f"   • OpenAI TTS: {'✅ Available' if openai_api_key else '❌ Missing'}")
    print(f"   • ElevenLabs TTS: {'✅ Available' if os.getenv('ELEVENLABS_API_KEY') else '❌ Missing'}")
    print(f"   • Twilio SMS: {'✅ Available' if os.getenv('TWILIO_ACCOUNT_SID') else '❌ Missing'}")
    print("\n🌐 Access URLs:")
    print("   🎤 Voice Interface: http://localhost:5000")
    print("   💬 Text Chat Interface: http://localhost:5000/chat")
    print("   📊 Health Check: http://localhost:5000/health")
    print("\n✨ Dual Interface Features:")
    print("   🎤 Voice: Premium Rachel TTS + Speech Recognition")
    print("   💬 Text: FAQ + SMS phone collection for complex questions")
    print("   📱 Mobile: Premium audio compatibility + state management")
    print("   📞 SMS: Customer service notifications with phone collection")

    app.run(debug=True, host='0.0.0.0', port=5000)
