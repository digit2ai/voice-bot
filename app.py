from twilio.twiml.voice_response import VoiceResponse, Gather, Say, Play, Record, Dial, Pause
from twilio.rest import Client
from functools import wraps
import re
from urllib.parse import urlencode
from flask import Flask, request, jsonify, render_template_string, session, make_response
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
from datetime import datetime, timedelta
import sqlite3
from typing import Optional, Tuple, Dict, Any, List
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
import uuid
import hashlib

# Load environment variables
load_dotenv()

# Setup Flask
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-default-secret-key-change-this')
CORS(app, origins="*", allow_headers="*", methods="*")

# Setup Enhanced Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("ringlypro.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# API Keys validation
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_phone = os.getenv("TWILIO_PHONE_NUMBER")
# Twilio Webhook Configuration
TWILIO_PHONE_NUMBER = "+18886103810"  # Your business number
TWILIO_WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "https://voice-bot-r91r.onrender.com")

# Email Configuration
smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
smtp_port = int(os.getenv("SMTP_PORT", "587"))
email_user = os.getenv("EMAIL_USER")
email_password = os.getenv("EMAIL_PASSWORD")
from_email = os.getenv("FROM_EMAIL", email_user)

# HubSpot Configuration
hubspot_api_token = os.getenv("HUBSPOT_ACCESS_TOKEN")
hubspot_portal_id = os.getenv("HUBSPOT_PORTAL_ID")
hubspot_owner_id = os.getenv("HUBSPOT_OWNER_ID")

# Zoom Configuration
zoom_meeting_url = "https://us06web.zoom.us/j/7269045564?pwd=MnR6TXVio652a69JpgaDtMcemiwT9X.1"
zoom_meeting_id = "726 904 5564"
zoom_password = "RinglyPro2024"

# Business Configuration
business_timezone = timezone(timedelta(hours=-5))  # Eastern Time (UTC-5)
business_hours = {
    'monday': {'start': '09:00', 'end': '17:00'},
    'tuesday': {'start': '09:00', 'end': '17:00'},
    'wednesday': {'start': '09:00', 'end': '17:00'},
    'thursday': {'start': '09:00', 'end': '17:00'},
    'friday': {'start': '09:00', 'end': '17:00'},
    'saturday': {'start': '10:00', 'end': '14:00'},
    'sunday': {'start': 'closed', 'end': 'closed'}
}

if not anthropic_api_key:
    logger.error("ANTHROPIC_API_KEY not found in environment variables")
    raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

# ==================== ENHANCED DATABASE SETUP ====================

def init_database():
    """Initialize SQLite database for customers and appointments"""
    try:
        conn = sqlite3.connect('ringlypro.db')
        cursor = conn.cursor()
        
        # Original customer inquiries table
        cursor.execute('''CREATE TABLE IF NOT EXISTS inquiries (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          phone TEXT NOT NULL,
                          question TEXT NOT NULL,
                          timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                          status TEXT DEFAULT 'new',
                          sms_sent BOOLEAN DEFAULT FALSE,
                          sms_sid TEXT,
                          source TEXT DEFAULT 'chat',
                          notes TEXT)''')
        
        # Enhanced appointments table
        cursor.execute('''CREATE TABLE IF NOT EXISTS appointments (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          customer_name TEXT NOT NULL,
                          customer_email TEXT NOT NULL,
                          customer_phone TEXT NOT NULL,
                          appointment_date DATE NOT NULL,
                          appointment_time TIME NOT NULL,
                          duration INTEGER DEFAULT 30,
                          purpose TEXT,
                          status TEXT DEFAULT 'scheduled',
                          zoom_meeting_url TEXT,
                          hubspot_contact_id TEXT,
                          hubspot_meeting_id TEXT,
                          confirmation_code TEXT UNIQUE,
                          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                          timezone TEXT DEFAULT 'Eastern',
                          notes TEXT)''')
        
        # Calendar availability table (for blocked times)
        cursor.execute('''CREATE TABLE IF NOT EXISTS availability_blocks (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          date DATE NOT NULL,
                          start_time TIME NOT NULL,
                          end_time TIME NOT NULL,
                          is_available BOOLEAN DEFAULT TRUE,
                          reason TEXT,
                          created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Enhanced database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")

# ==================== HUBSPOT SERVICE ====================

class HubSpotService:
    """Enhanced HubSpot CRM integration"""
    
    def __init__(self):
        self.api_token = hubspot_api_token
        self.portal_id = hubspot_portal_id
        self.owner_id = hubspot_owner_id
        self.base_url = "https://api.hubapi.com"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        if self.api_token:
            logger.info(f"✅ HubSpot service initialized - Token: {self.api_token[:12]}...")
        else:
            logger.warning("⚠️ HubSpot not configured - missing HUBSPOT_ACCESS_TOKEN")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test HubSpot API connection"""
        if not self.api_token:
            return {"success": False, "error": "HubSpot API token not configured"}
        
        try:
            response = requests.get(
                f"{self.base_url}/crm/v3/objects/contacts",
                headers=self.headers,
                params={"limit": 1},
                timeout=10
            )
            
            if response.status_code == 200:
                return {"success": True, "message": "HubSpot connection successful"}
            else:
                return {"success": False, "error": f"API returned status {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {"success": False, "error": f"Connection failed: {str(e)}"}
    
    def create_contact(self, name: str, email: str = "", phone: str = "", company: str = "") -> Dict[str, Any]:
        """Create or update contact in HubSpot"""
        try:
            # Search for existing contact by email first
            if email:
                existing = self.search_contact_by_email(email)
                if existing.get("success") and existing.get("contact"):
                    return self.update_contact(existing["contact"]["id"], {
                        "firstname": name.split()[0] if name.split() else "",
                        "lastname": " ".join(name.split()[1:]) if len(name.split()) > 1 else "",
                        "phone": phone,
                        "company": company
                    })
            
            # Create new contact
            name_parts = name.strip().split()
            properties = {
                "firstname": name_parts[0] if name_parts else "",
                "lastname": " ".join(name_parts[1:]) if len(name_parts) > 1 else "",
                "email": email,
                "phone": phone,
                "company": company,
                "lifecyclestage": "lead",
                "lead_source": "RinglyPro Voice Assistant"
            }
            
            # Remove empty values
            properties = {k: v for k, v in properties.items() if v}
            
            contact_data = {"properties": properties}
            
            response = requests.post(
                f"{self.base_url}/crm/v3/objects/contacts",
                headers=self.headers,
                json=contact_data,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                contact = response.json()
                return {
                    "success": True,
                    "message": f"Contact created: {name}",
                    "contact_id": contact.get("id"),
                    "contact": contact
                }
            else:
                return {"success": False, "error": f"Failed to create contact: {response.text}"}
                
        except Exception as e:
            return {"success": False, "error": f"Error creating contact: {str(e)}"}
    
    def search_contact_by_email(self, email: str) -> Dict[str, Any]:
        """Search for contact by email address"""
        try:
            search_data = {
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "email",
                        "operator": "EQ",
                        "value": email
                    }]
                }],
                "properties": ["email", "firstname", "lastname", "phone", "company"],
                "limit": 1
            }
            
            response = requests.post(
                f"{self.base_url}/crm/v3/objects/contacts/search",
                headers=self.headers,
                json=search_data,
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json()
                contacts = results.get("results", [])
                
                if contacts:
                    return {
                        "success": True,
                        "contact": contacts[0]
                    }
                else:
                    return {"success": False, "error": f"No contact found with email: {email}"}
            else:
                return {"success": False, "error": f"Search failed: {response.text}"}
                
        except Exception as e:
            return {"success": False, "error": f"Error searching contact: {str(e)}"}
    
    def update_contact(self, contact_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update contact information"""
        try:
            # Remove empty values
            updates = {k: v for k, v in updates.items() if v}
            update_data = {"properties": updates}
            
            response = requests.patch(
                f"{self.base_url}/crm/v3/objects/contacts/{contact_id}",
                headers=self.headers,
                json=update_data,
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Contact updated successfully",
                    "contact": response.json()
                }
            else:
                return {"success": False, "error": f"Failed to update contact: {response.text}"}
                
        except Exception as e:
            return {"success": False, "error": f"Error updating contact: {str(e)}"}
    
def create_meeting(self, title: str, contact_id: str, start_time: datetime, duration_minutes: int = 30) -> Dict[str, Any]:
    """Create meeting using Engagement API (WORKING VERSION)"""
    try:
        # Use the Engagement API that we just tested and works!
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        meeting_data = {
            "engagement": {
                "active": True,
                "type": "MEETING",
                "timestamp": int(start_time.timestamp() * 1000)
            },
            "associations": {
                "contactIds": [contact_id] if contact_id else [],
                "companyIds": [],
                "dealIds": []
            },
            "metadata": {
                "title": title,
                "body": f"Appointment scheduled via RinglyPro Voice Assistant\n\nZoom Details:\n{zoom_meeting_url}\nMeeting ID: {zoom_meeting_id}\nPassword: {zoom_password}",
                "startTime": int(start_time.timestamp() * 1000),
                "endTime": int(end_time.timestamp() * 1000),
                "location": zoom_meeting_url,
                "meetingOutcome": "SCHEDULED"
            }
        }
        
        response = requests.post(
            "https://api.hubapi.com/engagements/v1/engagements",
            headers=self.headers,
            json=meeting_data,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            engagement = response.json()
            # Get the engagement ID correctly from the response structure
            engagement_id = engagement.get("engagement", {}).get("id")
            
            logger.info(f"✅ Meeting created via Engagement API: {engagement_id}")
            
            return {
                "success": True,
                "message": f"Meeting created: {title}",
                "meeting_id": str(engagement_id),  # Convert to string for consistency
                "meeting": engagement
            }
        else:
            logger.error(f"Failed to create meeting: {response.status_code} - {response.text}")
            return {"success": False, "error": f"Failed to create meeting: {response.text}"}
            
    except Exception as e:
        logger.error(f"Error creating meeting: {str(e)}")
        return {"success": False, "error": f"Error creating meeting: {str(e)}"}
    
    def associate_meeting_with_contact(self, meeting_id: str, contact_id: str) -> Dict[str, Any]:
        """Associate meeting with contact"""
        try:
            association_data = {
                "inputs": [{
                    "from": {
                        "id": meeting_id
                    },
                    "to": {
                        "id": contact_id
                    },
                    "type": "meeting_to_contact"
                }]
            }
            
            response = requests.put(
                f"{self.base_url}/crm/v4/associations/meetings/contacts/batch/create",
                headers=self.headers,
                json=association_data,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                return {"success": True, "message": "Meeting associated with contact"}
            else:
                return {"success": False, "error": f"Failed to associate meeting: {response.text}"}
                
        except Exception as e:
            return {"success": False, "error": f"Error associating meeting: {str(e)}"}


# ==================== TELEPHONY CALL HANDLER ====================

def say_with_rachel(self, response: VoiceResponse, text: str) -> None:
    """Helper to use Rachel's voice or fallback to Polly"""
    audio_url = self.generate_rachel_audio(text)
    
    if audio_url:
        response.play(audio_url)
        logger.info("✅ Using Rachel's voice")
    else:
        response.say(text, voice='Polly.Joanna')
        logger.info("⚠️ Using Polly fallback")

class PhoneCallHandler:
    """Handle incoming phone calls with IVR and Rachel's voice"""
    
    def __init__(self):
        self.elevenlabs_api_key = elevenlabs_api_key
        self.rachel_voice_id = "21m00Tcm4TlvDq8ikWAM"
        self.webhook_base_url = os.getenv("WEBHOOK_BASE_URL", "https://voice-bot-r91r.onrender.com")
    
    def generate_rachel_audio(self, text: str) -> Optional[str]:
        """Generate audio URL using Rachel's voice via ElevenLabs"""
        if not self.elevenlabs_api_key:
            return None
            
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.rachel_voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_api_key
            }
            
            # Optimize text for speech
            speech_text = text.replace("RinglyPro", "Ringly Pro")
            speech_text = speech_text.replace("AI", "A.I.")
            speech_text = speech_text.replace("$", " dollars")
            
            tts_data = {
                "text": speech_text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }
            
            response = requests.post(url, json=tts_data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # Save audio temporarily
                audio_filename = f"rachel_{uuid.uuid4()}.mp3"
                audio_path = f"/tmp/{audio_filename}"
                
                with open(audio_path, 'wb') as f:
                    f.write(response.content)
                
                # Return URL that Twilio can access
                audio_url = f"{self.webhook_base_url}/audio/{audio_filename}"
                logger.info(f"✅ Rachel audio generated: {audio_url}")
                return audio_url
            else:
                logger.warning(f"ElevenLabs TTS failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating Rachel audio: {e}")
            return None
    
    def create_greeting_response(self) -> VoiceResponse:
        """Create the initial greeting when someone calls"""
        response = VoiceResponse()
        
        greeting_text = """
        Thank you for calling Ringly Pro, your A.I. powered business assistant. 
        I'm Rachel, your virtual receptionist. 
        To better serve you, please tell me what you'd like to do. 
        Say book a demo to schedule a consultation, 
        pricing to hear about our plans, 
        subscribe to get started with our service, 
        or support for customer service.
        """
        
        gather = Gather(
            input='speech',
            timeout=5,
            action='/phone/process-speech',
            method='POST',
            speechTimeout='auto',
            language='en-US'
        )
        
        # Try to use Rachel's voice first
        audio_url = self.generate_rachel_audio(greeting_text)
        
        if audio_url:
            # Use Rachel's premium voice
            gather.play(audio_url)
            logger.info("✅ Using Rachel's premium voice from ElevenLabs")
        else:
            # Fallback to Twilio's voice
            gather.say(greeting_text, voice='Polly.Joanna', language='en-US')
            logger.info("⚠️ Falling back to Twilio's Polly voice")
        
        response.append(gather)
        response.redirect('/phone/webhook')
        
        return response
    
    def process_speech_input(self, speech_result: str) -> VoiceResponse:
        """Process the caller's speech and route accordingly"""
        response = VoiceResponse()
        speech_lower = speech_result.lower().strip()
        
        logger.info(f"📞 Phone speech input: {speech_result}")
        
        # Detect intent from speech
        if any(word in speech_lower for word in ['demo', 'consultation', 'appointment', 'meeting', 'schedule']):
            return self.handle_demo_booking()
        elif any(word in speech_lower for word in ['price', 'pricing', 'cost', 'plan', 'package']):
            return self.handle_pricing_inquiry()
        elif any(word in speech_lower for word in ['subscribe', 'subscription', 'sign up', 'signup', 'get started', 'start service', 'want to subscribe', 'i want to subscribe']):
            return self.handle_subscription()
        elif any(word in speech_lower for word in ['support', 'help', 'customer service', 'agent', 'representative']):
            return self.handle_support_transfer()
        else:
            # Try FAQ system - FIXED: Use the global function, not self method
            faq_response, is_faq = get_faq_response(speech_result)
            
            if is_faq and not is_no_answer_response(faq_response):
                # Limit response length for phone
                if len(faq_response) > 300:
                    faq_response = faq_response[:297] + "..."
                
                # Use Rachel's voice for FAQ response
                audio_url = self.generate_rachel_audio(faq_response)
                
                if audio_url:
                    response.play(audio_url)
                else:
                    response.say(faq_response, voice='Polly.Joanna')
                
                response.pause(length=1)
                
                followup = Gather(
                    input='speech',
                    timeout=5,
                    action='/phone/process-speech',
                    method='POST',
                    speechTimeout='auto'
                )
                
                followup_text = "Is there anything else I can help you with today?"
                followup_audio = self.generate_rachel_audio(followup_text)
                
                if followup_audio:
                    followup.play(followup_audio)
                else:
                    followup.say(followup_text, voice='Polly.Joanna')
                
                response.append(followup)
            else:
                # Can't answer, offer to transfer
                transfer_text = "I'd be happy to help with that. Let me connect you with someone who can provide more specific information."
                
                audio_url = self.generate_rachel_audio(transfer_text)
                
                if audio_url:
                    response.play(audio_url)
                else:
                    response.say(transfer_text, voice='Polly.Joanna')
                
                dial = Dial(action='/phone/call-complete', timeout=30)
                dial.number('+16566001400')
                response.append(dial)
            
            return response
    
    def handle_demo_booking(self) -> VoiceResponse:
        """Handle demo booking request"""
        response = VoiceResponse()
        
        booking_text = """
        Excellent! I'd be happy to schedule a free consultation for you. 
        Our team will show you how Ringly Pro can transform your business communications. 
        I'll need to collect a few details. 
        First, please say your full name.
        """
        
        gather = Gather(
            input='speech',
            timeout=5,
            action='/phone/collect-name',
            method='POST',
            speechTimeout='auto'
        )
        
        # Try to use Rachel's voice first
        audio_url = self.generate_rachel_audio(booking_text)
        
        if audio_url:
            gather.play(audio_url)
            logger.info("✅ Using Rachel's voice for booking")
        else:
            gather.say(booking_text, voice='Polly.Joanna')
            logger.info("⚠️ Falling back to Polly voice")
        
        response.append(gather)
        
        return response
    
    def handle_pricing_inquiry(self) -> VoiceResponse:
        """Provide pricing information"""
        response = VoiceResponse()
        
        pricing_text = """
        I'd be happy to share our pricing plans with you. 
        
        We offer three tiers:
        
        The Starter Plan at 97 dollars per month includes 1000 minutes, 
        text messaging, and appointment scheduling.
        
        The Pro Plan at 297 dollars per month includes 3000 minutes, 
        C.R.M. integrations, and mobile app access.
        
        The Premium Plan at 497 dollars per month includes 7500 minutes, 
        dedicated account management, and marketing automation.
        
        Would you like to schedule a consultation to discuss which plan is right for you? 
        Say yes to book a demo, or repeat to hear the prices again.
        """
        
        gather = Gather(
            input='speech',
            timeout=5,
            action='/phone/pricing-followup',
            method='POST',
            speechTimeout='auto'
        )
        
        # Try to use Rachel's voice first
        audio_url = self.generate_rachel_audio(pricing_text)
        
        if audio_url:
            gather.play(audio_url)
            logger.info("✅ Using Rachel's voice for pricing")
        else:
            gather.say(pricing_text, voice='Polly.Joanna')
            logger.info("⚠️ Falling back to Polly voice")
        
        response.append(gather)
        
        return response
    
    def handle_subscription(self) -> VoiceResponse:
        """Handle subscription request with SMS and transfer"""
        response = VoiceResponse()
        
        try:
            # Get caller's phone number from the Twilio request
            caller_phone = request.form.get('From', '')
            logger.info(f"📱 Subscription request from: {caller_phone}")
            
            subscribe_text = """
            Wonderful! I'm excited to help you get started with Ringly Pro. 
            I'm sending you our subscription link via text message right now.
            I'll also connect you with our onboarding specialist 
            who will walk you through the setup process. 
            
            Please hold while I transfer you.
            """
            
            # Use Rachel's voice
            audio_url = self.generate_rachel_audio(subscribe_text)
            
            if audio_url:
                response.play(audio_url)
            else:
                response.say(subscribe_text, voice='Polly.Joanna')
            
            # Send SMS with subscription link
            if caller_phone:
                self.send_subscription_sms(caller_phone)
            
            response.pause(length=1)
            
            # Transfer to sales/onboarding number
            dial = Dial(
                action='/phone/call-complete',
                timeout=30,
                record='record-from-answer-dual'
            )
            dial.number('+16566001400')
            response.append(dial)
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error in handle_subscription: {e}")
            # Fallback response
            response.say("I'll connect you with our team to help with your subscription.", voice='Polly.Joanna')
            dial = Dial()
            dial.number('+16566001400')
            response.append(dial)
            return response
    
    def handle_support_transfer(self) -> VoiceResponse:
        """Transfer to customer support"""
        response = VoiceResponse()
        
        transfer_text = "I'll connect you with our customer support team right away. Please hold."
        
        # Use Rachel's voice
        audio_url = self.generate_rachel_audio(transfer_text)
        
        if audio_url:
            response.play(audio_url)
        else:
            response.say(transfer_text, voice='Polly.Joanna')
        
        dial = Dial(
            action='/phone/call-complete',
            timeout=30,
            record='record-from-answer-dual'
        )
        dial.number('+16566001400')
        response.append(dial)
        
        return response
    
    def handle_general_inquiry(self, question: str) -> VoiceResponse:
        """Handle general questions using FAQ system"""
        response = VoiceResponse()
        
        # Use existing FAQ system
        faq_response, is_faq = get_faq_response(question)
        
        if is_faq and not is_no_answer_response(faq_response):
            # Limit response length for phone
            if len(faq_response) > 300:
                faq_response = faq_response[:297] + "..."
            
            # Use Rachel's voice for FAQ response
            audio_url = self.generate_rachel_audio(faq_response)
            
            if audio_url:
                response.play(audio_url)
            else:
                response.say(faq_response, voice='Polly.Joanna')
            
            response.pause(length=1)
            
            followup = Gather(
                input='speech',
                timeout=5,
                action='/phone/process-speech',
                method='POST',
                speechTimeout='auto'
            )
            
            followup_text = "Is there anything else I can help you with today?"
            followup_audio = self.generate_rachel_audio(followup_text)
            
            if followup_audio:
                followup.play(followup_audio)
            else:
                followup.say(followup_text, voice='Polly.Joanna')
            
            response.append(followup)
        else:
            # Can't answer, offer to transfer
            transfer_text = "I'd be happy to help with that. Let me connect you with someone who can provide more specific information."
            
            audio_url = self.generate_rachel_audio(transfer_text)
            
            if audio_url:
                response.play(audio_url)
            else:
                response.say(transfer_text, voice='Polly.Joanna')
            
            dial = Dial(action='/phone/call-complete', timeout=30)
            dial.number('+16566001400')
            response.append(dial)
        
        return response
    
    def collect_booking_info(self, step: str, value: str = None) -> VoiceResponse:
        """Multi-step booking information collection"""
        response = VoiceResponse()
        
        if step == 'name':
            # Store name and ask for phone
            gather = Gather(
                input='speech dtmf',
                timeout=10,
                action='/phone/collect-phone',
                method='POST',
                speechTimeout='auto',
                numDigits=10,
                finishOnKey='#'
            )
            
            text = f"Thank you {value}. Now, please say or enter your phone number using the keypad."
            audio_url = self.generate_rachel_audio(text)
            
            if audio_url:
                gather.play(audio_url)
            else:
                gather.say(text, voice='Polly.Joanna')
            
            response.append(gather)
            
        elif step == 'phone':
            # Enhanced: Try to create appointment in database
            try:
                # Get call SID and customer name from session
                import flask
                call_sid = flask.request.form.get('CallSid', 'unknown')
                customer_name = flask.session.get(f'call_{call_sid}_name', 'Customer')
                
                # Try to create appointment
                success, confirmation_code = self.create_appointment_from_phone(
                    customer_name, 
                    value,  # phone number
                    call_sid
                )
                
                if success and confirmation_code:
                    # SUCCESS: Appointment created in database
                    text1 = f"Perfect! I've scheduled your consultation. Your confirmation code is {confirmation_code}. You'll receive text and email confirmations with all the details including your Zoom meeting link."
                else:
                    # FALLBACK: Use original behavior
                    text1 = f"Perfect! I have your phone number as {value}. I'll send you a text message with a link to schedule your consultation online at your convenience."
                    # Still send the SMS with booking link
                    self.send_booking_sms(value)
                    
            except Exception as e:
                logger.error(f"Appointment creation error: {e}")
                # FALLBACK: Use original behavior if anything fails
                text1 = f"Perfect! I have your phone number as {value}. I'll send you a text message with a link to schedule your consultation online at your convenience."
                self.send_booking_sms(value)
            
            audio_url = self.generate_rachel_audio(text1)
            
            if audio_url:
                response.play(audio_url)
            else:
                response.say(text1, voice='Polly.Joanna')
            
            response.pause(length=1)
            
            text2 = "Is there anything else I can help you with today?"
            
            audio_url2 = self.generate_rachel_audio(text2)
            
            if audio_url2:
                response.play(audio_url2)
            else:
                response.say(text2, voice='Polly.Joanna')
            
            gather = Gather(
                input='speech',
                timeout=5,
                action='/phone/process-speech',
                method='POST'
            )
            response.append(gather)
            
        return response
    
    def send_booking_sms(self, phone_number: str):
        """Send SMS with booking link"""
        try:
            if not all([twilio_account_sid, twilio_auth_token, twilio_phone]):
                logger.warning("Twilio not configured for SMS")
                return
            
            client = Client(twilio_account_sid, twilio_auth_token)
            
            message_body = f"""
Thank you for calling RinglyPro! 🎯

📅 Schedule your FREE consultation:
{self.webhook_base_url}/chat-enhanced

Or reply to this message with your preferred date/time.

Questions? Call us back at 888-610-3810

- The RinglyPro Team
            """.strip()
            
            message = client.messages.create(
                body=message_body,
                from_=twilio_phone,
                to=phone_number
            )
            
            logger.info(f"📱 Booking SMS sent to {phone_number}: {message.sid}")
            
        except Exception as e:
            logger.error(f"Failed to send booking SMS: {e}")
    
    def send_subscription_sms(self, phone_number: str):
        """Send SMS with subscription link"""
        try:
            if not all([twilio_account_sid, twilio_auth_token, twilio_phone]):
                logger.warning("Twilio not configured for subscription SMS")
                return
            
            client = Client(twilio_account_sid, twilio_auth_token)
            
            message_body = f"""
🎉 Thanks for wanting to subscribe to RinglyPro!

🔗 Complete your subscription here:
https://ringlypro.com/subscribe

You're also being connected to our specialist now.

Questions? Call us back at 888-610-3810

- The RinglyPro Team
            """.strip()
            
            message = client.messages.create(
                body=message_body,
                from_=twilio_phone,
                to=phone_number
            )
            
            logger.info(f"📱 Subscription SMS sent to {phone_number}: {message.sid}")
            
        except Exception as e:
            logger.error(f"Failed to send subscription SMS: {e}")
    
    def create_appointment_from_phone(self, name: str, phone: str, call_sid: str) -> Tuple[bool, Optional[str]]:
        """Create appointment after phone collection"""
        try:
            # Use a valid email format that HubSpot will accept
            phone_digits = re.sub(r'\D', '', phone)[-10:]  # Last 10 digits
            email = f"phone.{phone_digits}@booking.ringlypro.com"
            
            # Get tomorrow's date and default morning slot
            from datetime import datetime, timedelta
            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Log the attempt
            logger.info(f"📞 Creating phone appointment for {name} ({phone}) with email {email}")
            
            appointment_data = {
                'name': name,
                'email': email,
                'phone': phone,
                'date': tomorrow,
                'time': '10:00',  # Default morning slot
                'purpose': f'Phone booking - Call {call_sid[:8]} - NEEDS EMAIL VERIFICATION'
            }
            
            # Use existing AppointmentManager
            appointment_manager = AppointmentManager()
            success, message, appointment = appointment_manager.book_appointment(appointment_data)
            
            if success:
                logger.info(f"✅ Phone appointment created: {appointment.get('confirmation_code')}")
                logger.info(f"📊 HubSpot Contact ID: {appointment.get('hubspot_contact_id')}")
                logger.info(f"📊 HubSpot Meeting ID: {appointment.get('hubspot_meeting_id')}")
                
                # Create detailed HubSpot task for follow-up
                if appointment.get('hubspot_contact_id'):
                    self.create_detailed_hubspot_task(
                        name, 
                        phone, 
                        email,
                        appointment.get('confirmation_code'),
                        appointment.get('hubspot_contact_id')
                    )
                
                return True, appointment.get('confirmation_code', 'PENDING')
            else:
                logger.warning(f"Failed to create appointment: {message}")
                return False, None
                
        except Exception as e:
            logger.error(f"Failed to create phone appointment: {e}")
            return False, None

    def create_detailed_hubspot_task(self, name: str, phone: str, email: str, confirmation_code: str, contact_id: str):
        """Create detailed HubSpot task with contact association"""
        try:
            if not hubspot_api_token:
                logger.warning("HubSpot API token not configured")
                return
                
            headers = {
                "Authorization": f"Bearer {hubspot_api_token}",
                "Content-Type": "application/json"
            }
            
            # Create task with detailed information
            task_data = {
                "properties": {
                    "hs_task_subject": f"🔴 URGENT: Verify Phone Booking - {name}",
                    "hs_task_body": f"""
PHONE BOOKING FOLLOW-UP REQUIRED

Customer Information:
- Name: {name}
- Phone: {phone}
- Placeholder Email: {email}
- Confirmation Code: {confirmation_code}
- Booking Source: Phone Call (Rachel AI)

IMMEDIATE ACTIONS NEEDED:
1. ✉️ Get correct email address from customer
2. 📧 Update HubSpot contact with real email
3. 📅 Confirm appointment date/time works
4. 📑 Send pre-meeting materials
5. 💬 Add notes about customer's specific needs

APPOINTMENT DETAILS:
- Scheduled for: Tomorrow at 10:00 AM EST
- Meeting Type: RinglyPro Consultation (30 min)
- Zoom Link: Already sent via SMS

⚠️ NOTE: This was booked via phone, so email is a placeholder.
Customer expects confirmation - please verify ASAP!
                    """.strip(),
                    "hs_task_priority": "HIGH",
                    "hs_task_status": "NOT_STARTED",
                    "hs_task_type": "CALL"
                }
            }
            
            # Add owner if configured
            if hubspot_owner_id:
                task_data["properties"]["hubspot_owner_id"] = hubspot_owner_id
            
            # Set due date to 2 hours from now (urgent!)
            due_date = datetime.now() + timedelta(hours=2)
            task_data["properties"]["hs_timestamp"] = str(int(due_date.timestamp() * 1000))
            
            # Create the task
            response = requests.post(
                "https://api.hubapi.com/crm/v3/objects/tasks",
                headers=headers,
                json=task_data,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                task_id = response.json().get("id")
                logger.info(f"✅ HubSpot task created: {task_id}")
                
                # Associate task with contact
                if task_id and contact_id:
                    association_data = {
                        "inputs": [{
                            "from": {"id": task_id},
                            "to": {"id": contact_id},
                            "type": "task_to_contact"
                        }]
                    }
                    
                    assoc_response = requests.put(
                        "https://api.hubapi.com/crm/v4/associations/tasks/contacts/batch/create",
                        headers=headers,
                        json=association_data,
                        timeout=10
                    )
                    
                    if assoc_response.status_code in [200, 201, 204]:
                        logger.info(f"✅ Task associated with contact {contact_id}")
                    else:
                        logger.warning(f"Failed to associate task: {assoc_response.status_code}")
            else:
                logger.error(f"HubSpot task creation failed: {response.status_code} - {response.text}")
                    
        except Exception as e:
            logger.error(f"HubSpot task error: {e}")
    
    # ================ NEW METHODS ADDED BELOW ================
    
# ENHANCED create_appointment_from_phone method with better HubSpot integration
# Replace the existing method in PhoneCallHandler class

def create_appointment_from_phone(self, name: str, phone: str, call_sid: str) -> Tuple[bool, Optional[str]]:
    """Create appointment after phone collection - FIXED HUBSPOT VERSION"""
    try:
        # IMPORTANT: Use a valid email format that HubSpot will accept
        # Using the phone number as part of the email ensures uniqueness
        phone_digits = re.sub(r'\D', '', phone)[-10:]  # Last 10 digits
        email = f"phone.{phone_digits}@booking.ringlypro.com"  # More legitimate looking email
        
        # Get tomorrow's date and default morning slot
        from datetime import datetime, timedelta
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Log the attempt
        logger.info(f"📞 Creating phone appointment for {name} ({phone}) with email {email}")
        
        appointment_data = {
            'name': name,
            'email': email,
            'phone': phone,
            'date': tomorrow,
            'time': '10:00',  # Default morning slot
            'purpose': f'Phone booking - Call {call_sid[:8]} - NEEDS EMAIL VERIFICATION'
        }
        
        # Use existing AppointmentManager
        appointment_manager = AppointmentManager()
        success, message, appointment = appointment_manager.book_appointment(appointment_data)
        
        if success:
            logger.info(f"✅ Phone appointment created: {appointment.get('confirmation_code')}")
            logger.info(f"📊 HubSpot Contact ID: {appointment.get('hubspot_contact_id')}")
            logger.info(f"📊 HubSpot Meeting ID: {appointment.get('hubspot_meeting_id')}")
            
            # Create detailed HubSpot task for follow-up
            if appointment.get('hubspot_contact_id'):
                self.create_detailed_hubspot_task(
                    name, 
                    phone, 
                    email,
                    appointment.get('confirmation_code'),
                    appointment.get('hubspot_contact_id')
                )
            
            return True, appointment.get('confirmation_code', 'PENDING')
        else:
            logger.warning(f"Failed to create appointment: {message}")
            return False, None
            
    except Exception as e:
        logger.error(f"Failed to create phone appointment: {e}")
        return False, None

def create_detailed_hubspot_task(self, name: str, phone: str, email: str, confirmation_code: str, contact_id: str):
    """Create detailed HubSpot task with contact association - NEW METHOD"""
    try:
        if not hubspot_api_token:
            logger.warning("HubSpot API token not configured")
            return
            
        headers = {
            "Authorization": f"Bearer {hubspot_api_token}",
            "Content-Type": "application/json"
        }
        
        # Create task with detailed information
        task_data = {
            "properties": {
                "hs_task_subject": f"🔴 URGENT: Verify Phone Booking - {name}",
                "hs_task_body": f"""
PHONE BOOKING FOLLOW-UP REQUIRED

Customer Information:
- Name: {name}
- Phone: {phone}
- Placeholder Email: {email}
- Confirmation Code: {confirmation_code}
- Booking Source: Phone Call (Rachel AI)

IMMEDIATE ACTIONS NEEDED:
1. ✉️ Get correct email address from customer
2. 📧 Update HubSpot contact with real email
3. 📅 Confirm appointment date/time works
4. 📑 Send pre-meeting materials
5. 💬 Add notes about customer's specific needs

APPOINTMENT DETAILS:
- Scheduled for: Tomorrow at 10:00 AM EST
- Meeting Type: RinglyPro Consultation (30 min)
- Zoom Link: Already sent via SMS

⚠️ NOTE: This was booked via phone, so email is a placeholder.
Customer expects confirmation - please verify ASAP!
                """.strip(),
                "hs_task_priority": "HIGH",
                "hs_task_status": "NOT_STARTED",
                "hs_task_type": "CALL"
            }
        }
        
        # Add owner if configured
        if hubspot_owner_id:
            task_data["properties"]["hubspot_owner_id"] = hubspot_owner_id
        
        # Set due date to 2 hours from now (urgent!)
        due_date = datetime.now() + timedelta(hours=2)
        task_data["properties"]["hs_timestamp"] = str(int(due_date.timestamp() * 1000))
        
        # Create the task
        response = requests.post(
            "https://api.hubapi.com/crm/v3/objects/tasks",
            headers=headers,
            json=task_data,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            task_id = response.json().get("id")
            logger.info(f"✅ HubSpot task created: {task_id}")
            
            # Associate task with contact
            if task_id and contact_id:
                association_data = {
                    "inputs": [{
                        "from": {"id": task_id},
                        "to": {"id": contact_id},
                        "type": "task_to_contact"
                    }]
                }
                
                assoc_response = requests.put(
                    "https://api.hubapi.com/crm/v4/associations/tasks/contacts/batch/create",
                    headers=headers,
                    json=association_data,
                    timeout=10
                )
                
                if assoc_response.status_code in [200, 201, 204]:
                    logger.info(f"✅ Task associated with contact {contact_id}")
                else:
                    logger.warning(f"Failed to associate task: {assoc_response.status_code}")
        else:
            logger.error(f"HubSpot task creation failed: {response.status_code} - {response.text}")
                
    except Exception as e:
        logger.error(f"HubSpot task error: {e}")

def send_subscription_sms(self, phone_number: str):
    """Send SMS with subscription link"""
    try:
        if not all([twilio_account_sid, twilio_auth_token, twilio_phone]):
            logger.warning("Twilio not configured for subscription SMS")
            return
        
        client = Client(twilio_account_sid, twilio_auth_token)
        
        message_body = f"""
🎉 Thanks for wanting to subscribe to RinglyPro!

🔗 Complete your subscription here:
https://ringlypro.com/subscribe

You're also being connected to our specialist now.

Questions? Call us back at 888-610-3810

- The RinglyPro Team
        """.strip()
        
        message = client.messages.create(
            body=message_body,
            from_=twilio_phone,
            to=phone_number
        )
        
        logger.info(f"📱 Subscription SMS sent to {phone_number}: {message.sid}")
        
    except Exception as e:
        logger.error(f"Failed to send subscription SMS: {e}")

# ADD THIS DEBUG ENDPOINT to test HubSpot connection
@app.route('/test-meeting-only', methods=['GET'])
def test_meeting_only():
    """Test creating just a meeting"""
    try:
        headers = {
            "Authorization": f"Bearer {hubspot_api_token}",
            "Content-Type": "application/json"
        }
        
        # Create a meeting using the engagement API (older but more reliable)
        meeting_data = {
            "engagement": {
                "active": True,
                "type": "MEETING",
                "timestamp": int(time.time() * 1000)
            },
            "associations": {
                "contactIds": [],  # We'll leave empty for test
                "companyIds": [],
                "dealIds": []
            },
            "metadata": {
                "title": "Test RinglyPro Meeting",
                "body": "Test meeting from RinglyPro system",
                "startTime": int((datetime.now() + timedelta(days=1)).timestamp() * 1000),
                "endTime": int((datetime.now() + timedelta(days=1, minutes=30)).timestamp() * 1000),
                "location": "https://us06web.zoom.us/j/7269045564"
            }
        }
        
        # Try the older engagement API
        response = requests.post(
            "https://api.hubapi.com/engagements/v1/engagements",
            headers=headers,
            json=meeting_data,
            timeout=10
        )
        
        return jsonify({
            "status": response.status_code,
            "response": response.json() if response.status_code != 204 else "Success"
        })
        
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()})



@app.route('/test-hubspot', methods=['GET'])
def test_hubspot():
    """Test HubSpot integration and show recent contacts/meetings"""
    try:
        if not hubspot_api_token:
            return jsonify({"error": "HubSpot not configured"}), 500
        
        headers = {
            "Authorization": f"Bearer {hubspot_api_token}",
            "Content-Type": "application/json"
        }
        
        results = {
            "token_configured": bool(hubspot_api_token),
            "token_preview": hubspot_api_token[:20] + "..." if hubspot_api_token else None,
            "contacts": [],
            "meetings": [],
            "tasks": []
        }
        
        # Test 1: Get recent contacts
        contacts_response = requests.get(
            "https://api.hubapi.com/crm/v3/objects/contacts",
            headers=headers,
            params={"limit": 5, "sorts": "-createdAt"},
            timeout=10
        )
        
        if contacts_response.status_code == 200:
            contacts = contacts_response.json().get("results", [])
            for contact in contacts:
                props = contact.get("properties", {})
                results["contacts"].append({
                    "id": contact.get("id"),
                    "name": f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
                    "email": props.get("email"),
                    "phone": props.get("phone"),
                    "created": props.get("createdate")
                })
        else:
            results["contacts_error"] = f"Status {contacts_response.status_code}: {contacts_response.text[:200]}"
        
        # Test 2: Get recent meetings
        meetings_response = requests.get(
            "https://api.hubapi.com/crm/v3/objects/meetings",
            headers=headers,
            params={"limit": 5, "sorts": "-createdAt"},
            timeout=10
        )
        
        if meetings_response.status_code == 200:
            meetings = meetings_response.json().get("results", [])
            for meeting in meetings:
                props = meeting.get("properties", {})
                results["meetings"].append({
                    "id": meeting.get("id"),
                    "title": props.get("hs_meeting_title"),
                    "start_time": props.get("hs_meeting_start_time"),
                    "created": props.get("createdate")
                })
        else:
            results["meetings_error"] = f"Status {meetings_response.status_code}: {meetings_response.text[:200]}"
        
        # Test 3: Get recent tasks
        tasks_response = requests.get(
            "https://api.hubapi.com/crm/v3/objects/tasks",
            headers=headers,
            params={"limit": 5, "sorts": "-createdAt"},
            timeout=10
        )
        
        if tasks_response.status_code == 200:
            tasks = tasks_response.json().get("results", [])
            for task in tasks:
                props = task.get("properties", {})
                results["tasks"].append({
                    "id": task.get("id"),
                    "subject": props.get("hs_task_subject"),
                    "priority": props.get("hs_task_priority"),
                    "status": props.get("hs_task_status"),
                    "created": props.get("createdate")
                })
        else:
            results["tasks_error"] = f"Status {tasks_response.status_code}: {tasks_response.text[:200]}"
        
        # Test 4: Check our phone booking emails
        search_response = requests.post(
            "https://api.hubapi.com/crm/v3/objects/contacts/search",
            headers=headers,
            json={
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "email",
                        "operator": "CONTAINS_TOKEN",
                        "value": "booking.ringlypro"
                    }]
                }],
                "limit": 10
            },
            timeout=10
        )
        
        if search_response.status_code == 200:
            phone_bookings = search_response.json().get("results", [])
            results["phone_bookings"] = []
            for booking in phone_bookings:
                props = booking.get("properties", {})
                results["phone_bookings"].append({
                    "id": booking.get("id"),
                    "name": f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
                    "email": props.get("email"),
                    "phone": props.get("phone")
                })
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ALSO UPDATE the HubSpotService.create_contact method to handle phone bookings better
def create_contact(self, name: str, email: str = "", phone: str = "", company: str = "") -> Dict[str, Any]:
    """Create or update contact in HubSpot - ENHANCED FOR PHONE BOOKINGS"""
    try:
        # For phone bookings, search by phone first since email is placeholder
        if email and "booking.ringlypro" in email and phone:
            # Try to find existing contact by phone
            search_data = {
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "phone",
                        "operator": "EQ",
                        "value": phone
                    }]
                }],
                "properties": ["email", "firstname", "lastname", "phone", "company"],
                "limit": 1
            }
            
            search_response = requests.post(
                f"{self.base_url}/crm/v3/objects/contacts/search",
                headers=self.headers,
                json=search_data,
                timeout=10
            )
            
            if search_response.status_code == 200:
                results = search_response.json()
                if results.get("results"):
                    # Contact exists with this phone - update it
                    existing_contact = results["results"][0]
                    contact_id = existing_contact["id"]
                    
                    # Update with new information
                    update_data = {
                        "firstname": name.split()[0] if name.split() else "",
                        "lastname": " ".join(name.split()[1:]) if len(name.split()) > 1 else "",
                        "lifecyclestage": "lead",
                        "lead_source": "RinglyPro Voice Assistant - Phone Booking"
                    }
                    
                    # Only update email if the existing one is also a placeholder
                    existing_email = existing_contact.get("properties", {}).get("email", "")
                    if not existing_email or "booking.ringlypro" in existing_email:
                        update_data["email"] = email
                    
                    return self.update_contact(contact_id, update_data)
        
        # Standard contact creation for non-phone bookings or if no existing contact found
        name_parts = name.strip().split()
        properties = {
            "firstname": name_parts[0] if name_parts else "",
            "lastname": " ".join(name_parts[1:]) if len(name_parts) > 1 else "",
            "email": email,
            "phone": phone,
            "company": company or "Phone Booking - Needs Follow-up",
            "lifecyclestage": "lead",
            "lead_source": "RinglyPro Voice Assistant"
        }
        
        # Add note for phone bookings
        if email and "booking.ringlypro" in email:
            properties["hs_lead_status"] = "OPEN"
            properties["notes"] = "Phone booking - email needs verification"
        
        # Remove empty values
        properties = {k: v for k, v in properties.items() if v}
        
        contact_data = {"properties": properties}
        
        response = requests.post(
            f"{self.base_url}/crm/v3/objects/contacts",
            headers=self.headers,
            json=contact_data,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            contact = response.json()
            logger.info(f"✅ HubSpot contact created: {contact.get('id')} - {name}")
            return {
                "success": True,
                "message": f"Contact created: {name}",
                "contact_id": contact.get("id"),
                "contact": contact
            }
        else:
            logger.error(f"HubSpot contact creation failed: {response.status_code} - {response.text}")
            return {"success": False, "error": f"Failed to create contact: {response.text}"}
            
    except Exception as e:
        logger.error(f"Error creating HubSpot contact: {e}")
        return {"success": False, "error": f"Error creating contact: {str(e)}"}
            # Don't break the flow if HubSpot fails

# END OF PhoneCallHandler CLASS

# ==================== APPOINTMENT MANAGEMENT CLASS ====================

class AppointmentManager:
    
    def __init__(self):
        self.hubspot_service = HubSpotService()
    
    @staticmethod
    def generate_confirmation_code():
        """Generate unique confirmation code"""
        return str(uuid.uuid4())[:8].upper()
    
    @staticmethod
    def get_available_slots(date_str: str, timezone_str: str = 'Eastern') -> List[str]:
        """Get available appointment slots for a given date"""
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            target_tz = timezone(timedelta(hours=-5))
            
            day_name = target_date.strftime('%A').lower()
            
            if day_name not in business_hours or business_hours[day_name]['start'] == 'closed':
                return []
            
            start_time = datetime.strptime(business_hours[day_name]['start'], '%H:%M').time()
            end_time = datetime.strptime(business_hours[day_name]['end'], '%H:%M').time()
            
            slots = []
            current_time = datetime.combine(target_date, start_time)
            end_datetime = datetime.combine(target_date, end_time)
            
            while current_time < end_datetime:
                slot_time = current_time.strftime('%H:%M')
                
                if not AppointmentManager.is_slot_available(date_str, slot_time):
                    current_time += timedelta(minutes=30)
                    continue
                
                if target_date == datetime.now().date():
                    now = datetime.now(target_tz)
                    slot_datetime = datetime.combine(target_date, current_time.time()).replace(tzinfo=target_tz)
                    if slot_datetime <= now + timedelta(hours=1):
                        current_time += timedelta(minutes=30)
                        continue
                
                slots.append(slot_time)
                current_time += timedelta(minutes=30)
            
            return slots[:10]
            
        except Exception as e:
            logger.error(f"Error getting available slots: {e}")
            return []
    
    @staticmethod
    def is_slot_available(date_str: str, time_str: str) -> bool:
        """Check if a specific time slot is available"""
        try:
            conn = sqlite3.connect('ringlypro.db')
            cursor = conn.cursor()
            
            cursor.execute('''SELECT COUNT(*) FROM appointments 
                              WHERE appointment_date = ? AND appointment_time = ? AND status != 'cancelled' ''',
                           (date_str, time_str))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count == 0
        except Exception as e:
            logger.error(f"Error checking slot availability: {e}")
            return False
    
    def book_appointment(self, customer_data: dict) -> Tuple[bool, str, dict]:
        """Book a new appointment with ENHANCED HubSpot integration and notifications"""
        try:
            confirmation_code = self.generate_confirmation_code()
            logger.info(f"📅 Starting appointment booking with confirmation code: {confirmation_code}")
            
            # Validate required fields
            required_fields = ['name', 'email', 'phone', 'date', 'time']
            for field in required_fields:
                if not customer_data.get(field):
                    logger.error(f"Missing required field: {field}")
                    return False, f"Missing required field: {field}", {}
            
            # Fix phone number format
            phone_input = customer_data['phone']
            # Remove all non-digits
            phone_digits = re.sub(r'\D', '', phone_input)
            
            # Ensure proper format for US numbers
            if len(phone_digits) == 10:
                formatted_phone = f"+1{phone_digits}"
            elif len(phone_digits) == 11 and phone_digits[0] == '1':
                formatted_phone = f"+{phone_digits}"
            else:
                logger.error(f"Invalid phone format: {phone_input}")
                return False, "Invalid phone number format", {}
            
            logger.info(f"📞 Formatted phone: {phone_input} -> {formatted_phone}")
            
            # Check slot availability
            if not self.is_slot_available(customer_data['date'], customer_data['time']):
                return False, "Selected time slot is no longer available", {}
            
            # Create appointment datetime for HubSpot
            appointment_datetime = datetime.combine(
                datetime.strptime(customer_data['date'], '%Y-%m-%d').date(),
                datetime.strptime(customer_data['time'], '%H:%M').time()
            )
            
            # Initialize tracking variables
            hubspot_contact_id = None
            hubspot_meeting_id = None
            hubspot_success = False
            
            # Try HubSpot integration with better error handling
            if self.hubspot_service.api_token:
                logger.info("🔄 Attempting HubSpot integration...")
                
                try:
                    # Create/update contact in HubSpot
                    contact_result = self.hubspot_service.create_contact(
                        customer_data['name'], 
                        customer_data['email'], 
                        formatted_phone,  # Use formatted phone
                        "RinglyPro Prospect"
                    )
                    
                    if contact_result.get("success"):
                        hubspot_contact_id = contact_result.get("contact_id")
                        logger.info(f"✅ HubSpot contact created/updated: {hubspot_contact_id}")
                        
                        # Create meeting in HubSpot
                        meeting_title = f"RinglyPro Consultation - {customer_data.get('purpose', 'General consultation')}"
                        meeting_result = self.hubspot_service.create_meeting(
                            meeting_title, 
                            hubspot_contact_id, 
                            appointment_datetime,
                            30
                        )
                        
                        if meeting_result.get("success"):
                            hubspot_meeting_id = meeting_result.get("meeting_id")
                            hubspot_success = True
                            logger.info(f"✅ HubSpot meeting created: {hubspot_meeting_id}")
                        else:
                            logger.error(f"❌ HubSpot meeting creation failed: {meeting_result.get('error')}")
                    else:
                        logger.error(f"❌ HubSpot contact creation failed: {contact_result.get('error')}")
                        
                except Exception as hubspot_error:
                    logger.error(f"❌ HubSpot integration error: {hubspot_error}")
                    # Continue anyway - don't fail the booking
                    
            else:
                logger.warning("⚠️ HubSpot API token not configured - skipping CRM integration")
            
            # Save to local database (always do this)
            try:
                conn = sqlite3.connect('ringlypro.db')
                cursor = conn.cursor()
                
                cursor.execute('''INSERT INTO appointments 
                                  (customer_name, customer_email, customer_phone, appointment_date, 
                                   appointment_time, purpose, zoom_meeting_url, confirmation_code, 
                                   timezone, hubspot_contact_id, hubspot_meeting_id)
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
                    customer_data['name'],
                    customer_data['email'],
                    formatted_phone,  # Save formatted phone
                    customer_data['date'],
                    customer_data['time'],
                    customer_data.get('purpose', 'General consultation'),
                    zoom_meeting_url,
                    confirmation_code,
                    customer_data.get('timezone', 'Eastern'),
                    hubspot_contact_id,
                    hubspot_meeting_id
                ))
                
                appointment_id = cursor.lastrowid
                conn.commit()
                conn.close()
                logger.info(f"✅ Appointment saved to database with ID: {appointment_id}")
                
            except Exception as db_error:
                logger.error(f"❌ Database save error: {db_error}")
                return False, f"Database error: {str(db_error)}", {}
            
            # Create appointment object
            appointment = {
                'id': appointment_id,
                'confirmation_code': confirmation_code,
                'customer_name': customer_data['name'],
                'customer_email': customer_data['email'],
                'customer_phone': formatted_phone,
                'date': customer_data['date'],
                'time': customer_data['time'],
                'purpose': customer_data.get('purpose', 'General consultation'),
                'zoom_url': zoom_meeting_url,
                'zoom_id': zoom_meeting_id,
                'zoom_password': zoom_password,
                'hubspot_contact_id': hubspot_contact_id,
                'hubspot_meeting_id': hubspot_meeting_id
            }
            
            # Send confirmations with better error handling
            confirmation_results = self.send_appointment_confirmations(appointment)
            
            # Log final status
            logger.info(f"""
            📊 APPOINTMENT BOOKING SUMMARY:
            - Confirmation Code: {confirmation_code}
            - Database: ✅ Saved
            - HubSpot: {'✅ Integrated' if hubspot_success else '⚠️ Failed/Skipped'}
            - Email: {confirmation_results.get('email', '❌ Failed')}
            - SMS: {confirmation_results.get('sms', '❌ Failed')}
            """)
            
            return True, "Appointment booked successfully", appointment
            
        except Exception as e:
            logger.error(f"❌ Critical error booking appointment: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, f"Booking error: {str(e)}", {}
    
    @staticmethod
    def send_appointment_confirmations(appointment: dict) -> dict:
        """Send email and SMS confirmations with better error handling"""
        results = {'email': '❌ Failed', 'sms': '❌ Failed'}
        
        try:
            # Send email confirmation
            email_result = AppointmentManager.send_email_confirmation(appointment)
            results['email'] = '✅ Sent' if email_result else '❌ Failed'
            
            # Send SMS confirmation
            sms_result = AppointmentManager.send_sms_confirmation(appointment)
            results['sms'] = '✅ Sent' if sms_result else '❌ Failed'
            
        except Exception as e:
            logger.error(f"Error in send_appointment_confirmations: {e}")
        
        return results
    
    @staticmethod
    def send_email_confirmation(appointment: dict) -> bool:
        """Send detailed email confirmation with better error handling"""
        try:
            if not all([email_user, email_password]):
                logger.warning("⚠️ Email credentials not configured")
                return False
            
            logger.info(f"📧 Attempting to send email to: {appointment['customer_email']}")
            
            # Format date and time
            date_obj = datetime.strptime(appointment['date'], '%Y-%m-%d')
            formatted_date = date_obj.strftime('%A, %B %d, %Y')
            
            time_obj = datetime.strptime(appointment['time'], '%H:%M')
            formatted_time = time_obj.strftime('%I:%M %p')
            
            subject = f"RinglyPro Appointment Confirmation - {formatted_date}"
            
            body = f"""
Dear {appointment['customer_name']},

Your appointment with RinglyPro has been successfully scheduled!

📅 APPOINTMENT DETAILS:
- Date: {formatted_date}
- Time: {formatted_time} EST
- Duration: 30 minutes
- Purpose: {appointment['purpose']}
- Confirmation Code: {appointment['confirmation_code']}

💻 ZOOM MEETING DETAILS:
- Meeting Link: {appointment['zoom_url']}
- Meeting ID: {appointment['zoom_id']}
- Password: {appointment['zoom_password']}

📋 WHAT TO EXPECT:
Our team will discuss your specific needs and how RinglyPro can help streamline your business communications. Come prepared with any questions about our services.

📱 NEED TO RESCHEDULE?
Reply to this email or call us at (888) 610-3810 with your confirmation code.

We look forward to speaking with you!

Best regards,
The RinglyPro Team
Email: support@ringlypro.com
Phone: (888) 610-3810
Website: https://ringlypro.com
            """.strip()
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = appointment['customer_email']
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(email_user, email_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"✅ Email confirmation sent to {appointment['customer_email']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Email sending failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    @staticmethod
    def send_sms_confirmation(appointment: dict) -> bool:
        """Send SMS confirmation with better error handling"""
        try:
            if not all([twilio_account_sid, twilio_auth_token, twilio_phone]):
                logger.warning("⚠️ Twilio credentials not configured")
                return False
            
            logger.info(f"📱 Attempting to send SMS to: {appointment['customer_phone']}")
            
            client = Client(twilio_account_sid, twilio_auth_token)
            
            # Format date and time
            date_obj = datetime.strptime(appointment['date'], '%Y-%m-%d')
            formatted_date = date_obj.strftime('%m/%d/%Y')
            
            time_obj = datetime.strptime(appointment['time'], '%H:%M')
            formatted_time = time_obj.strftime('%I:%M %p')
            
            message_body = f"""
✅ RinglyPro Appointment Confirmed

📅 {formatted_date} at {formatted_time} EST
🔗 Join: {appointment['zoom_url']}
📋 Code: {appointment['confirmation_code']}

Meeting ID: {appointment['zoom_id']}
Password: {appointment['zoom_password']}

Need help? Reply to this message or call (888) 610-3810.
            """.strip()
            
            message = client.messages.create(
                body=message_body,
                from_=twilio_phone,
                to=appointment['customer_phone']
            )
            
            logger.info(f"✅ SMS confirmation sent. SID: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"❌ SMS sending failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    @staticmethod
    def get_appointment_by_code(confirmation_code: str) -> Optional[dict]:
        """Get appointment by confirmation code"""
        try:
            conn = sqlite3.connect('ringlypro.db')
            cursor = conn.cursor()
            
            cursor.execute('''SELECT * FROM appointments WHERE confirmation_code = ? AND status != 'cancelled' ''',
                           (confirmation_code,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
            
        except Exception as e:
            logger.error(f"Error getting appointment: {e}")
            return None

# END OF AppointmentManager CLASS
# ==================== SMS/PHONE HELPER FUNCTIONS ====================

def validate_phone_number(phone_str: str) -> Optional[str]:
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

def send_sms_notification(customer_phone: str, customer_question: str, source: str = "chat") -> Tuple[bool, str]:
    """Send SMS notification to customer service"""
    try:
        if not all([twilio_account_sid, twilio_auth_token, twilio_phone]):
            logger.warning("⚠️ Twilio credentials not configured - SMS notification skipped")
            return False, "SMS credentials not configured"
            
        client = Client(twilio_account_sid, twilio_auth_token)
        
        message_body = f"""
🔔 New RinglyPro Customer Inquiry

📞 Phone: {customer_phone}
💬 Question: {customer_question}
📱 Source: {source}
🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please follow up with this customer.
        """.strip()
        
        message = client.messages.create(
            body=message_body,
            from_=twilio_phone,
            to='+16566001400'
        )
        
        logger.info(f"✅ SMS sent successfully. SID: {message.sid}")
        return True, message.sid
        
    except Exception as e:
        logger.error(f"❌ SMS sending failed: {str(e)}")
        return False, str(e)

def save_customer_inquiry(phone: str, question: str, sms_sent: bool, sms_sid: str = "", source: str = "chat") -> bool:
    """Save customer inquiry to database"""
    try:
        conn = sqlite3.connect('ringlypro.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO inquiries (phone, question, sms_sent, sms_sid, source)
                          VALUES (?, ?, ?, ?, ?)''', (phone, question, sms_sent, sms_sid, source))
        conn.commit()
        conn.close()
        logger.info(f"💾 Customer inquiry saved: {phone}")
        return True
    except Exception as e:
        logger.error(f"❌ Database save failed: {e}")
        return False

def is_no_answer_response(response: str) -> bool:
    """Check if the FAQ response indicates no answer was found"""
    no_answer_indicators = [
        "I don't have information",
        "couldn't find a direct answer", 
        "please contact our customer service",
        "I don't have a specific answer",
        "contact our support team"
    ]
    return any(indicator in response.lower() for indicator in no_answer_indicators)

# ==================== EXTENSIVE FAQ BRAIN ====================

FAQ_BRAIN = {
    # ==================== BASIC PLATFORM INFORMATION ====================
    "what is ringlypro?": "RinglyPro.com is a 24/7 AI-powered call answering and client booking service designed for small businesses and professionals. It ensures you never miss a call by providing automated phone answering, appointment scheduling, and customer communication through AI technology.",

    "what does ringlypro do?": "RinglyPro provides 24/7 answering service, bilingual virtual receptionists (English/Spanish), AI-powered chat and text messaging, missed-call text-back, appointment scheduling, and integrations with existing business apps like CRMs and calendars.",

    "who owns ringlypro?": "RinglyPro.com is owned and operated by DIGIT2AI LLC, a company focused on building technology solutions that create better business opportunities.",

    "what is the history of ringlypro?": "RinglyPro was founded as part of DIGIT2AI's mission to help small businesses compete with larger companies by providing enterprise-level communication tools through artificial intelligence and automation.",

    # ==================== CORE FEATURES ====================
    "what are ringlypro main features?": "Key features include: 24/7 AI call answering, bilingual virtual receptionists, AI-powered chat & text, missed-call text-back, appointment scheduling, CRM integrations, call recording, automated booking tools, and mobile app access.",

    "does ringlypro support multiple languages?": "Yes, RinglyPro offers bilingual virtual receptionists that provide professional support in both English and Spanish to help businesses serve a wider audience.",

    "can ringlypro integrate with my existing tools?": "Yes, RinglyPro integrates seamlessly with existing CRMs, schedulers, calendars, and other business apps. Integration is available through online links or using Zapier for broader connectivity.",

    "does ringlypro offer appointment scheduling?": "Yes, clients can schedule appointments through phone, text, or online booking. All appointments sync with your existing calendar system for easy management.",

    "what is ai-powered call answering?": "RinglyPro's AI answering service uses advanced artificial intelligence to answer calls professionally, take messages, schedule appointments, and route calls according to your business needs, all while maintaining a natural conversation flow.",

    "what is missed-call text-back?": "Missed-call text-back is a feature that instantly re-engages callers you couldn't answer by automatically sending them a text message, keeping conversations and opportunities alive.",

    "does ringlypro record calls?": "Yes, call recording is available as a feature across all plans, allowing you to review conversations and maintain records of customer interactions.",

    "can i get a toll-free number?": "Yes, RinglyPro offers toll-free numbers and vanity numbers as part of their service options.",

    "does ringlypro have a mobile app?": "Yes, a mobile app is included with the Office Manager and Business Growth plans, allowing you to manage your service on the go.",

    "what is call forwarding?": "RinglyPro provides intelligent call forwarding that routes calls to the right person or department based on your customized rules and business hours.",

    "does ringlypro support call queuing?": "Yes, live call queuing is available with the Office Manager and Business Growth plans, ensuring callers are handled professionally during busy periods.",

    # ==================== PRICING & PLANS ====================
    "how much does ringlypro cost?": "RinglyPro offers three pricing tiers: Scheduling Assistant ($97/month), Office Manager ($297/month), and Marketing Director ($497/month). Each plan includes different amounts of minutes, text messages, and online replies.",

    "what is included in the starter plan?": "The Scheduling Assistant plan ($97/month) includes 1,000 minutes, 1,000 text messages, 1,000 online replies, self-guided setup, email support, premium voice options, call forwarding/porting, toll-free numbers, call recording, and automated booking tools.",

    "what is included in the office manager plan?": "The Office Manager plan ($297/month) includes 3,000 minutes, 3,000 texts, 3,000 online replies, all Starter features plus assisted onboarding, phone/email/text support, custom voice choices, live call queuing, Zapier integrations, CRM setup, invoice automation, payment gateway setup, and mobile app.",

    "what is included in the business growth plan?": "The Marketing Director plan ($497/month) includes 7,500 minutes, 7,500 texts, 7,500 online replies, everything in Office Manager plus professional onboarding, dedicated account manager, custom integrations, landing page design, lead capture automation, Google Ads campaign, email marketing, reputation management, conversion reporting, and monthly analytics.",

    "what is the cheapest plan?": "The most affordable plan is the Scheduling Assistant at $97/month, which includes essential features like 1,000 minutes, text messaging, appointment scheduling, and call recording.",

    "what is the most popular plan?": "The Office Manager plan ($297/month) is popular with growing businesses as it includes enhanced support, mobile app access, CRM integrations, and expanded capacity.",

    "are there any setup fees?": "Setup fees vary by plan. The Scheduling Assistant includes self-guided setup, while higher plans include assisted or professional onboarding.",

    "can i change plans later?": "Yes, you can upgrade or downgrade your plan as your business needs change. Contact customer service to discuss plan changes.",

    "what happens if i exceed my plan limits?": "RinglyPro offers overage protection and will work with you to find the right plan if you consistently exceed your current limits.",

    "is there a free trial?": "Contact RinglyPro directly for information about trial options and demonstrations of the service.",

    # ==================== TECHNICAL CAPABILITIES ====================
    "how does the ai work?": "RinglyPro uses advanced natural language processing and machine learning to understand caller intent, provide appropriate responses, and take actions like scheduling appointments or transferring calls.",

    "is the ai voice natural sounding?": "Yes, RinglyPro offers premium voice options that sound natural and professional, with the ability to customize voice choices on higher-tier plans.",

    "can the ai handle complex conversations?": "The AI is designed to handle a wide range of business conversations, from simple inquiries to appointment scheduling and call routing. For complex issues, it can seamlessly transfer to human agents.",

    "what about data security?": "RinglyPro follows industry-standard security practices to protect your business and customer data, including encrypted communications and secure data storage.",

    "how reliable is the service?": "RinglyPro provides 24/7 availability with enterprise-grade reliability and redundancy to ensure your business never misses important calls.",

    "can ringlypro work with my existing phone system?": "Yes, RinglyPro can integrate with most existing phone systems through call forwarding, number porting, or direct integration.",

    "what is call porting?": "Call porting allows you to transfer your existing business phone number to RinglyPro, so customers can continue calling the same number while benefiting from AI answering services.",

    # ==================== INTEGRATION QUESTIONS ====================
    "what crms does ringlypro work with?": "RinglyPro mentions working with CRMs and offers CRM setup for small businesses. They integrate through online links and Zapier, which supports hundreds of popular CRM systems including Salesforce, HubSpot, and others.",

    "can ringlypro integrate with zapier?": "Yes, Zapier integration is available with the Office Manager and Business Growth plans, allowing connection to thousands of business applications.",

    "does ringlypro work with stripe?": "Yes, Stripe/Payment Gateway Setup is included in the Office Manager and Business Growth plans.",

    "can ringlypro integrate with google calendar?": "Yes, RinglyPro integrates with popular calendar systems through our HubSpot CRM integration, which can sync with Google Calendar and other calendar platforms for seamless appointment scheduling.",

    "does ringlypro work with microsoft office?": "Integration with Microsoft Office tools is available through Zapier connections and direct integrations on higher-tier plans.",

    "can ringlypro connect to my website?": "Yes, RinglyPro offers website integration options including chat widgets, booking forms, and lead capture tools.",

    "what about social media integration?": "Social media management and integration tools are available with the Marketing Director plan.",

    # ==================== BUSINESS BENEFITS ====================
    "how will ringlypro help my business?": "RinglyPro helps businesses never miss opportunities, reduce staffing costs, improve customer service, automate routine tasks, and provide 24/7 availability without hiring additional staff.",

    "what industries does ringlypro serve?": "RinglyPro serves a wide range of industries including healthcare, legal services, real estate, home services, professional services, retail, and any business that relies on phone communications.",

    "is ringlypro good for small businesses?": "Yes, RinglyPro is specifically designed for small businesses and professionals who need enterprise-level communication tools without the complexity and cost of traditional systems.",

    "can ringlypro replace my receptionist?": "RinglyPro can handle many receptionist duties including answering calls, scheduling appointments, taking messages, and routing calls, while providing 24/7 availability.",

    "will ringlypro save me money?": "Many businesses save money by reducing staffing needs while improving service quality and availability. The cost is often less than hiring part-time reception staff.",

    "how quickly can i get started?": "Implementation time varies by plan. The Scheduling Assistant includes self-guided setup for quick deployment, while higher plans include assisted onboarding for more complex integrations.",

    # ==================== CUSTOMER SUPPORT ====================
    "how can i contact ringlypro support?": "You can contact RinglyPro customer service at (656) 213-3300 or via email. The level of support (email, phone, text) depends on your plan level.",

    "what are ringlypro business hours?": "RinglyPro provides 24/7 service availability. Their experts are available around the clock to support and grow your business.",

    "do you offer training?": "Yes, training and onboarding support is included with all plans, with more comprehensive training available on higher-tier plans.",

    "what if i need help setting up?": "Setup assistance varies by plan - from self-guided setup on the basic plan to professional onboarding and dedicated account management on premium plans.",

    "can i get a demo?": "Contact RinglyPro directly to schedule a demonstration of the platform and see how it can work for your specific business needs.",

    # ==================== APPOINTMENT BOOKING SPECIFIC ====================
    "how do i schedule an appointment?": "I can help you schedule an appointment right now! I'll need your name, email, phone number, preferred date, and what you'd like to discuss. Would you like to book an appointment?",
    
    "book an appointment": "Perfect! I'd be happy to help you schedule an appointment. Let me guide you through the booking process right now.",
    
    "schedule appointment": "Excellent! I can help you schedule an appointment immediately. Let me set up the booking form for you.",
    
    "i want to book": "Great! I'm ready to help you book an appointment. Let me get the scheduling process started for you right away.",
    
    "what are your available times?": "We're available Monday-Friday 9 AM to 5 PM, and Saturday 10 AM to 2 PM (Eastern Time). I can show you specific available slots once you let me know your preferred date.",
    
    "how far in advance can i book?": "You can schedule appointments up to 30 days in advance. For same-day appointments, we require at least 1 hour notice.",
    
    "can i reschedule my appointment?": "Yes! You can reschedule by providing your confirmation code. Would you like to reschedule an existing appointment?",
    
    "what happens in a consultation?": "Our consultations are 30-minute sessions via Zoom where we discuss your business needs and how RinglyPro can help. You'll receive all meeting details after booking.",
    
    "do you charge for consultations?": "Initial consultations are complimentary! This gives us a chance to understand your needs and show you how RinglyPro can benefit your business.",

    "what should i prepare for my appointment?": "Come prepared with information about your business, current communication challenges, call volume, and any specific features you're interested in. We'll tailor our discussion to your needs.",

    "can i bring team members to the consultation?": "Absolutely! Feel free to invite relevant team members to join the Zoom consultation. This can help ensure everyone understands how RinglyPro will benefit your business.",

    "what if i need to cancel my appointment?": "You can cancel or reschedule by contacting us with your confirmation code. We recommend giving at least 24 hours notice when possible.",

    "will i receive reminders about my appointment?": "Yes, you'll receive both email and SMS confirmations immediately after booking, and we typically send reminder notifications before your scheduled appointment."
}

# ==================== FAQ PROCESSING FUNCTIONS ====================

def get_faq_response(user_text: str) -> Tuple[str, bool]:
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
    except Exception as e:
        logger.warning(f"Web scraping failed: {e}")
    
    # Fallback to customer service
    return "I don't have a specific answer to that question. Please contact our Customer Service team for specialized assistance.", True

def get_faq_response_with_sms(user_text: str) -> Tuple[str, bool, bool]:
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
                return "I found some information on our website that might be related, but I'd like to connect you with our customer service team for personalized assistance with your specific question. Could you please provide your phone number so they can reach out to help you?", False, True
    except Exception as e:
        logger.warning(f"Web scraping failed: {e}")
    
    # Fallback to customer service with phone collection
    return "I don't have a specific answer to that question. I'd like to connect you with our customer service team. Could you please provide your phone number so they can reach out to help you?", False, True

def get_enhanced_faq_response(user_text: str) -> Tuple[str, bool, str]:
    """
    Enhanced FAQ with appointment booking capabilities
    Returns: (response_text, is_faq_match, action_needed)
    """
    user_text_lower = user_text.lower().strip()
    
    # Log for debugging
    logger.info(f"🔍 Enhanced FAQ processing: '{user_text_lower}'")
    
    # Check for appointment booking intent - PRIORITY CHECK
    booking_keywords = [
        'schedule', 'book', 'appointment', 'meeting', 'consultation', 
        'available', 'calendar', 'time', 'when can', 'set up', 'book an'
    ]
    
    booking_detected = any(keyword in user_text_lower for keyword in booking_keywords)
    logger.info(f"🎯 Booking keywords detected: {booking_detected}")
    
    if booking_detected:
        logger.info("✅ Returning booking action")
        return ("I'd be happy to help you schedule an appointment! Let me guide you through the booking process.", 
                True, "start_booking")
    
    # Check for rescheduling intent
    reschedule_keywords = ['reschedule', 'change', 'move', 'cancel', 'confirmation code']
    if any(keyword in user_text_lower for keyword in reschedule_keywords):
        return ("I can help you manage your existing appointment. Do you have your confirmation code?", 
                True, "manage_appointment")
    
    # Only check FAQ if no booking intent detected
    logger.info("📋 Checking FAQ database")
    
    # Try exact match first
    if user_text_lower in FAQ_BRAIN:
        return FAQ_BRAIN[user_text_lower], True, "none"
    
    # Try fuzzy matching
    matched = get_close_matches(user_text_lower, FAQ_BRAIN.keys(), n=1, cutoff=0.6)
    if matched:
        response = FAQ_BRAIN[matched[0]]
        # Add booking CTA to pricing questions
        if 'pricing' in matched[0] or 'cost' in matched[0] or 'plan' in matched[0]:
            response += " Would you like to schedule a free consultation to discuss your needs?"
            return response, True, "suggest_booking"
        return response, True, "none"
    
    # Fallback with booking option
    logger.info("❌ No FAQ match, offering booking")
    return ("I don't have a specific answer to that question, but I'd be happy to connect you with our team. Would you like to schedule a consultation or provide your phone number for a callback?", 
            False, "offer_booking")
    # ==================== EXTENSIVE HTML TEMPLATES ====================

# ==================== EXTENSIVE HTML TEMPLATES ====================

VOICE_HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
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

    /* Mobile-specific background - Navy Blue */
    @media (max-width: 768px) {
      html, body {
        background: linear-gradient(135deg, #1a237e 0%, #0d47a1 50%, #01579b 100%);
      }
    }

    /* Additional mobile detection for touch devices */
    @media (pointer: coarse) {
      html, body {
        background: linear-gradient(135deg, #1a237e 0%, #0d47a1 50%, #01579b 100%);
      }
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

    /* Enhance container for mobile with navy theme */
    @media (max-width: 768px) {
      .container {
        background: rgba(255, 255, 255, 0.12);
        box-shadow: 0 8px 32px rgba(13, 71, 161, 0.4);
      }
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

    .booking-button {
      position: absolute;
      top: 20px;
      left: 20px;
      background: linear-gradient(135deg, #4CAF50, #45a049);
      border: none;
      border-radius: 15px;
      color: white;
      padding: 0.75rem 1.5rem;
      cursor: pointer;
      font-size: 0.9rem;
      font-weight: 600;
      transition: all 0.3s ease;
      box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
      animation: bookingPulse 3s ease-in-out infinite;
    }

    .booking-button:hover {
      background: linear-gradient(135deg, #45a049, #388e3c);
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(76, 175, 80, 0.4);
      animation: none;
    }

    .booking-form-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(44, 62, 80, 0.95);
      backdrop-filter: blur(10px);
      display: none;
      justify-content: center;
      align-items: center;
      z-index: 1000;
      padding: 20px;
    }
    
    .booking-form-container {
      background: rgba(255, 255, 255, 0.98);
      border-radius: 20px;
      padding: 30px;
      max-width: 500px;
      width: 100%;
      max-height: 90vh;
      overflow-y: auto;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
      position: relative;
    }
    
    .booking-form-header {
      background: linear-gradient(135deg, #2196F3, #1976D2);
      color: white;
      padding: 20px;
      margin: -30px -30px 20px -30px;
      border-radius: 20px 20px 0 0;
      text-align: center;
    }
    
    .booking-form-header h2 {
      margin: 0;
      font-size: 1.5rem;
    }
    
    .booking-form-header p {
      margin: 5px 0 0 0;
      opacity: 0.9;
      font-size: 0.9rem;
    }
    
    .close-booking-form {
      position: absolute;
      top: 15px;
      right: 20px;
      background: rgba(255, 255, 255, 0.2);
      border: none;
      color: white;
      font-size: 20px;
      width: 30px;
      height: 30px;
      border-radius: 50%;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    
    .form-group {
      margin-bottom: 20px;
    }
    
    .form-group label {
      display: block;
      margin-bottom: 8px;
      color: #1565c0;
      font-weight: 600;
      font-size: 14px;
    }
    
    .form-group input,
    .form-group select,
    .form-group textarea {
      width: 100%;
      padding: 12px 15px;
      border: 2px solid #2196f3;
      border-radius: 10px;
      outline: none;
      font-size: 14px;
      background: white;
      color: #333;
      transition: border-color 0.3s ease;
    }
    
    .form-group input:focus,
    .form-group select:focus,
    .form-group textarea:focus {
      border-color: #1976d2;
    }
    
    .date-time-row {
      display: flex;
      gap: 15px;
    }
    
    .date-time-row .form-group {
      flex: 1;
    }
    
    .available-slots {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }
    
    .time-slot {
      padding: 8px 12px;
      background: #e3f2fd;
      border: 2px solid #2196f3;
      border-radius: 8px;
      cursor: pointer;
      font-size: 12px;
      color: #1565c0;
      transition: all 0.3s ease;
    }
    
    .time-slot:hover,
    .time-slot.selected {
      background: #2196f3;
      color: white;
    }
    
    .booking-submit-btn {
      width: 100%;
      padding: 15px;
      background: linear-gradient(135deg, #4caf50, #45a049);
      color: white;
      border: none;
      border-radius: 12px;
      cursor: pointer;
      font-weight: 600;
      font-size: 16px;
      transition: all 0.3s ease;
      margin-top: 10px;
    }
    
    .booking-submit-btn:hover {
      background: linear-gradient(135deg, #45a049, #388e3c);
      transform: translateY(-2px);
    }
    
    .booking-submit-btn:disabled {
      opacity: 0.6;
      cursor: not-allowed;
      transform: none;
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
      margin: 0 auto 2rem;
    }

    .mic-button:hover {
      transform: scale(1.05);
      box-shadow: 0 15px 50px rgba(76, 175, 80, 0.4);
    }

    .mic-button.listening {
      animation: listening 1.5s infinite;
      background: linear-gradient(135deg, #f44336, #d32f2f);
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
      0% { transform: scale(1); }
      50% { transform: scale(1.05); }
      100% { transform: scale(1); }
    }

    @keyframes processing {
      0%, 100% { transform: rotate(0deg); }
      25% { transform: rotate(90deg); }
      50% { transform: rotate(180deg); }
      75% { transform: rotate(270deg); }
    }

    @keyframes speaking {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.02); }
    }

    .mic-button svg {
      width: 60px;
      height: 60px;
      fill: #ffffff;
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

      .interface-switcher {
        top: 10px;
        right: 10px;
        font-size: 0.7rem;
        padding: 0.4rem 0.8rem;
      }

      .booking-button {
        top: 10px;
        left: 10px;
        font-size: 0.7rem;
        padding: 0.5rem 1rem;
      }
      
      .booking-form-container {
        margin: 10px;
        max-width: calc(100vw - 20px);
        max-height: calc(100vh - 20px);
        padding: 20px;
      }
      
      .booking-form-header {
        margin: -20px -20px 15px -20px;
        padding: 15px;
      }
      
      .date-time-row {
        flex-direction: column;
        gap: 10px;
      }
    }
  </style>
</head>
<!-- Add this right before </body> in VOICE_HTML_TEMPLATE -->

<!-- Subscription Popup Overlay -->
<div id="subscriptionPopup" class="subscription-popup-overlay" style="display: none;">
    <div class="subscription-popup-container">
        <button class="close-subscription-popup" onclick="closeSubscriptionPopup()">×</button>
        
        <div class="subscription-header">
            <h2>🚀 Start Your RinglyPro Journey</h2>
            <p>Choose the perfect plan for your business</p>
        </div>
        
        <div class="subscription-plans">
            <div class="plan-card">
                <div class="plan-badge">Most Popular</div>
                <h3>Scheduling Assistant</h3>
                <div class="plan-price">$97<span>/month</span></div>
                <ul class="plan-features">
                    <li>✅ 1,000 minutes</li>
                    <li>✅ 1,000 text messages</li>
                    <li>✅ Appointment scheduling</li>
                    <li>✅ Call recording</li>
                    <li>✅ Email support</li>
                </ul>
                <button class="plan-btn" onclick="selectPlan('starter')">Get Started</button>
            </div>
            
            <div class="plan-card featured">
                <div class="plan-badge">Best Value</div>
                <h3>Office Manager</h3>
                <div class="plan-price">$297<span>/month</span></div>
                <ul class="plan-features">
                    <li>✅ 3,000 minutes</li>
                    <li>✅ 3,000 text messages</li>
                    <li>✅ Everything in Starter</li>
                    <li>✅ CRM integrations</li>
                    <li>✅ Mobile app</li>
                    <li>✅ Priority support</li>
                </ul>
                <button class="plan-btn featured-btn" onclick="selectPlan('pro')">Get Started</button>
            </div>
            
            <div class="plan-card">
                <div class="plan-badge">Premium</div>
                <h3>Marketing Director</h3>
                <div class="plan-price">$497<span>/month</span></div>
                <ul class="plan-features">
                    <li>✅ 7,500 minutes</li>
                    <li>✅ 7,500 text messages</li>
                    <li>✅ Everything in Office Manager</li>
                    <li>✅ Dedicated account manager</li>
                    <li>✅ Marketing automation</li>
                    <li>✅ Custom integrations</li>
                </ul>
                <button class="plan-btn" onclick="selectPlan('premium')">Get Started</button>
            </div>
        </div>
        
        <div class="subscription-footer">
            <p>Questions? Call us at <strong>(888) 610-3810</strong></p>
            <button class="contact-sales-btn" onclick="contactSales()">💬 Talk to Sales</button>
        </div>
    </div>
</div>

<!-- Add this CSS in the <style> section of VOICE_HTML_TEMPLATE -->
<style>
/* Subscription Popup Styles */
.subscription-popup-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.8);
    backdrop-filter: blur(10px);
    display: none;
    justify-content: center;
    align-items: center;
    z-index: 2000;
    padding: 20px;
    animation: fadeIn 0.3s ease;
}

.subscription-popup-container {
    background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
    border-radius: 25px;
    padding: 40px;
    max-width: 1200px;
    width: 100%;
    max-height: 90vh;
    overflow-y: auto;
    box-shadow: 0 30px 60px rgba(0, 0, 0, 0.4);
    position: relative;
    animation: slideUp 0.4s ease;
}

@keyframes slideUp {
    from {
        opacity: 0;
        transform: translateY(30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.close-subscription-popup {
    position: absolute;
    top: 20px;
    right: 20px;
    background: rgba(0, 0, 0, 0.1);
    border: none;
    color: #333;
    font-size: 28px;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s ease;
}

.close-subscription-popup:hover {
    background: rgba(0, 0, 0, 0.2);
    transform: rotate(90deg);
}

.subscription-header {
    text-align: center;
    margin-bottom: 40px;
}

.subscription-header h2 {
    color: #2196F3;
    font-size: 2.5rem;
    margin-bottom: 10px;
    background: linear-gradient(45deg, #2196F3, #4CAF50);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.subscription-header p {
    color: #666;
    font-size: 1.2rem;
}

.subscription-plans {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 30px;
    margin-bottom: 30px;
}

.plan-card {
    background: white;
    border-radius: 20px;
    padding: 30px;
    position: relative;
    border: 2px solid #e0e0e0;
    transition: all 0.3s ease;
}

.plan-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 15px 30px rgba(0, 0, 0, 0.15);
}

.plan-card.featured {
    border-color: #4CAF50;
    transform: scale(1.05);
}

.plan-badge {
    position: absolute;
    top: -12px;
    left: 50%;
    transform: translateX(-50%);
    background: linear-gradient(135deg, #FF6B6B, #FF8E53);
    color: white;
    padding: 5px 20px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: bold;
}

.plan-card.featured .plan-badge {
    background: linear-gradient(135deg, #4CAF50, #45a049);
}

.plan-card h3 {
    color: #333;
    font-size: 1.5rem;
    margin: 20px 0;
    text-align: center;
}

.plan-price {
    font-size: 3rem;
    font-weight: bold;
    color: #2196F3;
    text-align: center;
    margin: 20px 0;
}

.plan-price span {
    font-size: 1rem;
    color: #666;
    font-weight: normal;
}

.plan-features {
    list-style: none;
    padding: 0;
    margin: 20px 0;
}

.plan-features li {
    padding: 10px 0;
    color: #555;
    border-bottom: 1px solid #f0f0f0;
}

.plan-features li:last-child {
    border-bottom: none;
}

.plan-btn {
    width: 100%;
    padding: 15px;
    background: linear-gradient(135deg, #2196F3, #1976D2);
    color: white;
    border: none;
    border-radius: 12px;
    font-size: 1.1rem;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.3s ease;
}

.plan-btn:hover {
    background: linear-gradient(135deg, #1976D2, #1565C0);
    transform: translateY(-2px);
    box-shadow: 0 10px 20px rgba(33, 150, 243, 0.3);
}

.plan-btn.featured-btn {
    background: linear-gradient(135deg, #4CAF50, #45a049);
}

.plan-btn.featured-btn:hover {
    background: linear-gradient(135deg, #45a049, #388e3c);
    box-shadow: 0 10px 20px rgba(76, 175, 80, 0.3);
}

.subscription-footer {
    text-align: center;
    padding-top: 20px;
    border-top: 1px solid #e0e0e0;
}

.subscription-footer p {
    color: #666;
    margin-bottom: 15px;
}

.contact-sales-btn {
    padding: 12px 30px;
    background: linear-gradient(135deg, #FF6B6B, #FF8E53);
    color: white;
    border: none;
    border-radius: 25px;
    font-size: 1rem;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.3s ease;
}

.contact-sales-btn:hover {
    background: linear-gradient(135deg, #FF8E53, #FF6B6B);
    transform: translateY(-2px);
    box-shadow: 0 10px 20px rgba(255, 107, 107, 0.3);
}

/* Mobile Responsive */
@media (max-width: 768px) {
    .subscription-popup-container {
        padding: 20px;
    }
    
    .subscription-header h2 {
        font-size: 1.8rem;
    }
    
    .subscription-plans {
        grid-template-columns: 1fr;
        gap: 20px;
    }
    
    .plan-card.featured {
        transform: scale(1);
    }
    
    .plan-card {
        padding: 20px;
    }
    
    .plan-price {
        font-size: 2.5rem;
    }
}
</style>
<body>
  <div class="container">
    <button class="booking-button" onclick="window.location.href='/chat-enhanced'">📅 Book Appointment</button>
    <button class="interface-switcher" onclick="window.location.href='/chat'">💬 Try Text Chat</button>
    
    <h1>RinglyPro AI</h1>
    <div class="subtitle">Your Intelligent Business Assistant<br><small style="opacity: 0.8;">Say "book appointment" for instant inline booking • Ask questions • Click "📅 Book"</small></div>
    
    <div class="language-selector">
      <button class="lang-btn active" data-lang="en-US">🇺🇸 English</button>
      <button class="lang-btn" data-lang="es-ES">🇪🇸 Español</button>
    </div>

    <button id="micBtn" class="mic-button" aria-label="Talk to RinglyPro AI">
      <svg xmlns="http://www.w3.org/2000/svg" height="60" viewBox="0 0 24 24" width="60" fill="#ffffff">
        <path d="M0 0h24v24H0V0z" fill="none"/>
        <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5-3c0 2.76-2.24 5-5 5s-5-2.24-5-5H6c0 3.31 2.69 6 6 6s6-2.69 6-6h-1zm-5 9c-3.87 0-7-3.13-7-7H3c0 5 4 9 9 9s9-4 9-9h-2c0 3.87-3.13 7-7 7z"/>
      </svg>
    </button>
    
    <div id="status">🎙️ Say "book appointment" for instant booking or tap to talk</div>
    
    <div class="controls">
      <button id="stopBtn" class="control-btn" disabled>⏹️ Stop</button>
      <button id="clearBtn" class="control-btn">🗑️ Clear</button>
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

  <!-- Inline Booking Form Overlay -->
  <div id="bookingFormOverlay" class="booking-form-overlay">
    <div class="booking-form-container">
      <div class="booking-form-header">
        <button class="close-booking-form" onclick="closeBookingForm()">×</button>
        <h2>📅 Schedule Your Appointment</h2>
        <p>Fill out the details below to book your consultation</p>
      </div>
      
      <form id="inlineBookingForm">
        <div class="form-group">
          <label>Full Name *</label>
          <input type="text" id="inlineCustomerName" placeholder="Your full name" required>
        </div>
        
        <div class="form-group">
          <label>Email Address *</label>
          <input type="email" id="inlineCustomerEmail" placeholder="your@email.com" required>
        </div>
        
        <div class="form-group">
          <label>Phone Number *</label>
          <input type="tel" id="inlineCustomerPhone" placeholder="(555) 123-4567" required>
        </div>
        
        <div class="form-group">
          <label>Preferred Date *</label>
          <input type="date" id="inlineAppointmentDate" min="" onchange="loadInlineAvailableSlots()" required>
        </div>
        
        <div class="form-group">
          <label>What would you like to discuss?</label>
          <textarea id="inlineAppointmentPurpose" placeholder="Brief description of your needs..." rows="3"></textarea>
        </div>
        
        <div id="inlineTimeSlotsContainer" style="display: none;">
          <label>Available Times *</label>
          <div id="inlineAvailableSlots" class="available-slots"></div>
        </div>
        
        <button type="button" class="booking-submit-btn" onclick="submitInlineBooking()">Book Appointment</button>
      </form>
    </div>
  </div>

<script>
    // Enhanced Voice Interface JavaScript with Mobile Text-Only Mode
    class EnhancedVoiceBot {
        constructor() {
            this.micBtn = document.getElementById('micBtn');
            this.status = document.getElementById('status');
            this.stopBtn = document.getElementById('stopBtn');
            this.clearBtn = document.getElementById('clearBtn');
            this.errorMessage = document.getElementById('errorMessage');
            this.langBtns = document.querySelectorAll('.lang-btn');
            
            this.isListening = false;
            this.isProcessing = false;
            this.isPlaying = false;
            this.currentLanguage = 'en-US';
            this.recognition = null;
            this.currentAudio = null;
            this.userInteracted = false;
            this.isMobile = /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
            this.processTimeout = null;
            this.audioContext = null;
            this.recognitionTimeout = null;
            
            // Initialize audio context on first user interaction (mobile)
            if (this.isMobile) {
                const initAudioContext = () => {
                    if (!this.audioContext) {
                        const AudioContext = window.AudioContext || window.webkitAudioContext;
                        if (AudioContext) {
                            this.audioContext = new AudioContext();
                            if (this.audioContext.state === 'suspended') {
                                this.audioContext.resume().then(() => {
                                    console.log('Mobile audio context initialized and resumed');
                                });
                            }
                        }
                    }
                    // Remove listener after first interaction
                    document.removeEventListener('touchstart', initAudioContext);
                    document.removeEventListener('click', initAudioContext);
                };
                
                // Add listeners for first user interaction
                document.addEventListener('touchstart', initAudioContext, { once: true });
                document.addEventListener('click', initAudioContext, { once: true });
            }
            
            this.init();
        }

        async init() {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            
            if (!SpeechRecognition) {
                this.showError('Speech recognition not supported. Please use Chrome or Edge.');
                return;
            }

            this.setupEventListeners();
            this.initSpeechRecognition();
        }

        initSpeechRecognition() {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            
            this.recognition = new SpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.interimResults = false;
            this.recognition.lang = this.currentLanguage;

            this.recognition.onstart = () => {
                console.log('Recognition started');
                this.isListening = true;
                this.updateUI('listening');
                this.updateStatus('🎙️ Listening... Speak now');
            };

            this.recognition.onresult = (event) => {
                console.log('Recognition result received');
                if (event.results && event.results.length > 0) {
                    const transcript = event.results[0][0].transcript.trim();
                    console.log('Transcript:', transcript);
                    this.processTranscript(transcript);
                }
            };

            this.recognition.onerror = (event) => {
                console.error('Recognition error:', event.error);
                
                // Handle no-speech error gracefully
                if (event.error === 'no-speech') {
                    this.isListening = false;
                    this.updateUI('ready');
                    this.updateStatus('🎙️ No speech detected. Tap to try again');
                    return;
                }
                
                this.handleError('Speech recognition error: ' + event.error);
            };

            this.recognition.onend = () => {
                console.log('Recognition ended');
                this.isListening = false;
                if (!this.isProcessing) {
                    this.updateUI('ready');
                    this.updateStatus('🎙️ Tap to talk');
                }
            };
        }

        async processTranscript(transcript) {
            if (!transcript || transcript.length < 2) {
                this.handleError('No speech detected');
                return;
            }

            console.log('Processing transcript:', transcript);
            this.isProcessing = true;
            this.updateUI('processing');
            this.updateStatus('🤖 Processing...');
            
            // Clear any existing timeout
            if (this.processTimeout) {
                clearTimeout(this.processTimeout);
            }
            
            // Add timeout for the entire processing
            this.processTimeout = setTimeout(() => {
                if (this.isProcessing) {
                    console.log('Processing timeout - resetting UI');
                    this.handleError('Processing took too long. Please try again.');
                }
            }, 15000);

            try {
                const response = await fetch('/process-text-enhanced', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: transcript,
                        language: this.currentLanguage,
                        mobile: this.isMobile
                    })
                });

                clearTimeout(this.processTimeout);

                if (!response.ok) throw new Error('Server error: ' + response.status);

                const data = await response.json();
                if (data.error) throw new Error(data.error);

                console.log('Received data:', data);

                // Always show text if available
                if (data.show_text && data.response) {
                    this.updateStatus('💬 ' + data.response.substring(0, 150) + (data.response.length > 150 ? '...' : ''));
                }

                // Check for subscription popup action (NEW)
                if (data.action === 'show_subscription_popup') {
                    console.log('🎯 Subscription popup triggered');
                    
                    // Play audio if available
                    if (data.audio) {
                        console.log('Playing audio response');
                        await this.playPremiumAudio(data.audio, data.response, data.show_text);
                    } else {
                        console.log('No audio, using browser TTS');
                        await this.playBrowserTTS(data.response);
                    }
                    
                    // Show subscription popup
                    setTimeout(() => {
                        showSubscriptionPopup();
                    }, 500);
                    return;
                }

                // Check for booking redirect action
                if (data.action === 'redirect_to_booking') {
                    console.log('🎯 Booking redirect detected');
                    
                    // Play audio if available
                    if (data.audio) {
                        console.log('Playing audio response');
                        await this.playPremiumAudio(data.audio, data.response, data.show_text);
                    } else {
                        console.log('No audio, using browser TTS');
                        await this.playBrowserTTS(data.response);
                    }
                    
                    // Show booking form
                    setTimeout(() => {
                        this.showInlineBookingForm();
                    }, 500);
                    return;
                }

                // Regular responses
                if (data.audio) {
                    console.log('Playing Rachel audio response');
                    await this.playPremiumAudio(data.audio, data.response, data.show_text);
                } else if (data.response) {
                    console.log('Using browser TTS');
                    await this.playBrowserTTS(data.response);
                } else {
                    this.audioFinished();
                }

            } catch (error) {
                clearTimeout(this.processTimeout);
                this.handleError('Processing error: ' + error.message);
            }
        }

        async playPremiumAudio(audioBase64, responseText, showText = false) {
            console.log('Playing premium audio, showText:', showText, 'isMobile:', this.isMobile);
            
            // MOBILE: Skip audio entirely and show text with good UX
            if (this.isMobile) {
                console.log('Mobile detected - using text-only mode');
                
                // Show the full response text clearly
                this.updateStatus('💬 ' + responseText);
                
                // Update UI to show we're "speaking" (even though it's text)
                this.isPlaying = true;
                this.updateUI('speaking');
                
                // INCREASED READING TIME: ~100ms per character, minimum 5 seconds, maximum 15 seconds
                const readingTime = Math.min(Math.max(responseText.length * 100, 5000), 15000);
                console.log(`Mobile reading time: ${readingTime}ms for ${responseText.length} characters`);
                
                return new Promise((resolve) => {
                    setTimeout(() => {
                        this.audioFinished();
                        resolve();
                    }, readingTime);
                });
            }
            
            // DESKTOP: Original working code
            try {
                // Keep text visible while audio plays
                if (showText) {
                    this.updateStatus('🔊 ' + responseText.substring(0, 150) + (responseText.length > 150 ? '...' : ''));
                }

                const audioData = atob(audioBase64);
                const arrayBuffer = new ArrayBuffer(audioData.length);
                const uint8Array = new Uint8Array(arrayBuffer);
                
                for (let i = 0; i < audioData.length; i++) {
                    uint8Array[i] = audioData.charCodeAt(i);
                }

                const audioBlob = new Blob([arrayBuffer], { type: 'audio/mpeg' });
                const audioUrl = URL.createObjectURL(audioBlob);
                
                this.currentAudio = new Audio(audioUrl);
                
                return new Promise((resolve) => {
                    let audioStarted = false;
                    
                    const playTimeout = setTimeout(() => {
                        if (!audioStarted) {
                            console.log('Audio timeout - fallback to text');
                            this.currentAudio = null;
                            URL.revokeObjectURL(audioUrl);
                            if (!showText) {
                                this.updateStatus('💬 ' + responseText.substring(0, 150) + '...');
                            }
                            setTimeout(() => {
                                this.audioFinished();
                                resolve();
                            }, 3000);
                        }
                    }, 5000);
                    
                    this.currentAudio.onplay = () => {
                        console.log('Audio started playing');
                        audioStarted = true;
                        clearTimeout(playTimeout);
                        this.isPlaying = true;
                        this.updateUI('speaking');
                        if (!showText) {
                            this.updateStatus('🔊 Rachel is speaking...');
                        }
                    };
                    
                    this.currentAudio.onended = () => {
                        console.log('Audio ended');
                        clearTimeout(playTimeout);
                        URL.revokeObjectURL(audioUrl);
                        this.audioFinished();
                        resolve();
                    };
                    
                    this.currentAudio.onerror = (error) => {
                        console.error('Audio error:', error);
                        clearTimeout(playTimeout);
                        this.currentAudio = null;
                        URL.revokeObjectURL(audioUrl);
                        if (!showText) {
                            this.updateStatus('💬 ' + responseText.substring(0, 150) + '...');
                        }
                        setTimeout(() => {
                            this.audioFinished();
                            resolve();
                        }, 3000);
                    };
                    
                    // Play audio (works on desktop)
                    this.currentAudio.play().catch((error) => {
                        console.log('Audio play failed:', error);
                        clearTimeout(playTimeout);
                        if (!showText) {
                            this.updateStatus('💬 ' + responseText.substring(0, 150) + '...');
                        }
                        setTimeout(() => {
                            this.audioFinished();
                            resolve();
                        }, 3000);
                    });
                });
                
            } catch (error) {
                console.error('Premium audio processing failed:', error);
                this.updateStatus('💬 ' + responseText.substring(0, 150) + '...');
                setTimeout(() => {
                    this.audioFinished();
                }, 3000);
                return Promise.resolve();
            }
        }

        async playBrowserTTS(text) {
            // Skip browser TTS on mobile too
            if (this.isMobile) {
                console.log('Mobile: Skipping browser TTS, showing text');
                this.updateStatus('💬 ' + text);
                
                // INCREASED READING TIME: ~100ms per character, minimum 5 seconds, maximum 15 seconds
                const readingTime = Math.min(Math.max(text.length * 100, 5000), 15000);
                console.log(`Mobile reading time: ${readingTime}ms for ${text.length} characters`);
                
                return new Promise((resolve) => {
                    setTimeout(() => {
                        this.audioFinished();
                        resolve();
                    }, readingTime);
                });
            }
            
            // Original browser TTS for desktop
            return new Promise((resolve) => {
                try {
                    const utterance = new SpeechSynthesisUtterance(text);
                    utterance.lang = this.currentLanguage;
                    utterance.onend = () => {
                        this.audioFinished();
                        resolve();
                    };
                    utterance.onerror = () => {
                        this.updateStatus('💬 ' + text.substring(0, 150) + '...');
                        setTimeout(() => {
                            this.audioFinished();
                            resolve();
                        }, 3000);
                    };
                    speechSynthesis.speak(utterance);
                } catch (error) {
                    this.updateStatus('💬 ' + text.substring(0, 150) + '...');
                    setTimeout(() => {
                        this.audioFinished();
                        resolve();
                    }, 3000);
                }
            });
        }

        audioFinished() {
            console.log('Audio finished');
            this.isPlaying = false;
            this.isProcessing = false;
            this.updateUI('ready');
            this.updateStatus('🎙️ Say "subscribe" or "book appointment" or tap to continue');
        }

        setupEventListeners() {
            this.micBtn.addEventListener('click', () => {
                console.log('Mic button clicked');
                this.toggleListening();
            });
            
            this.stopBtn.addEventListener('click', () => {
                if (this.isListening) this.stopListening();
                if (this.isPlaying) this.stopAudio();
            });
            
            this.clearBtn.addEventListener('click', () => this.clearAll());
            
            this.langBtns.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    this.changeLanguage(e.target.dataset.lang);
                });
            });
        }

        changeLanguage(lang) {
            this.currentLanguage = lang;
            if (this.recognition) this.recognition.lang = lang;
            
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
            if (this.isProcessing || !this.recognition) {
                console.log('Cannot start: processing or no recognition');
                return;
            }
            
            try {
                console.log('Starting speech recognition...');
                
                // Ensure audio context is active on mobile
                if (this.isMobile && this.audioContext && this.audioContext.state === 'suspended') {
                    await this.audioContext.resume();
                    console.log('Audio context resumed before listening');
                }
                
                this.clearError();
                speechSynthesis.cancel();
                this.recognition.start();
                this.stopBtn.disabled = false;
                
            } catch (error) {
                console.error('Failed to start:', error);
                this.handleError('Failed to start listening: ' + error.message);
            }
        }

        stopListening() {
            if (this.isListening && this.recognition) {
                this.recognition.stop();
            }
        }

        stopAudio() {
            if (this.currentAudio) {
                this.currentAudio.pause();
                this.currentAudio = null;
            }
            speechSynthesis.cancel();
            this.audioFinished();
        }

        updateUI(state) {
            this.micBtn.className = 'mic-button';
            
            switch (state) {
                case 'listening':
                    this.micBtn.classList.add('listening');
                    this.stopBtn.disabled = false;
                    break;
                case 'processing':
                    this.micBtn.classList.add('processing');
                    this.stopBtn.disabled = false;
                    break;
                case 'speaking':
                    this.micBtn.classList.add('speaking');
                    this.stopBtn.disabled = false;
                    break;
                case 'ready':
                default:
                    this.stopBtn.disabled = true;
                    break;
            }
        }

        updateStatus(message) {
            this.status.textContent = message;
        }

        handleError(message) {
            console.error('Error:', message);
            this.showError(message);
            this.isProcessing = false;
            this.isListening = false;
            this.isPlaying = false;
            this.updateUI('ready');
            
            if (this.processTimeout) {
                clearTimeout(this.processTimeout);
                this.processTimeout = null;
            }
            
            setTimeout(() => {
                this.updateStatus('🎙️ Say "subscribe" or "book appointment" or tap to try again');
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

        showInlineBookingForm() {
            const overlay = document.getElementById('bookingFormOverlay');
            const dateInput = document.getElementById('inlineAppointmentDate');
            
            const today = new Date().toISOString().split('T')[0];
            dateInput.min = today;
            
            overlay.style.display = 'flex';
            
            if (!this.isMobile) {
                setTimeout(() => {
                    document.getElementById('inlineCustomerName').focus();
                }, 100);
            }
            
            this.updateStatus('📅 Fill out the booking form above');
        }

        clearAll() {
            this.stopAudio();
            if (this.isListening) this.stopListening();
            
            if (this.processTimeout) {
                clearTimeout(this.processTimeout);
                this.processTimeout = null;
            }
            
            this.isProcessing = false;
            this.isListening = false;
            this.isPlaying = false;
            this.updateUI('ready');
            this.clearError();
            
            const overlay = document.getElementById('bookingFormOverlay');
            if (overlay) overlay.style.display = 'none';
            
            const subscriptionPopup = document.getElementById('subscriptionPopup');
            if (subscriptionPopup) subscriptionPopup.style.display = 'none';
            
            this.updateStatus('🎙️ Ready! Say "subscribe" or "book appointment"');
        }
    }

    // Subscription Popup Functions
    function showSubscriptionPopup() {
        const popup = document.getElementById('subscriptionPopup');
        if (popup) {
            popup.style.display = 'flex';
            
            // Animate entrance
            setTimeout(() => {
                popup.classList.add('active');
            }, 10);
            
            // Log analytics event
            console.log('📊 Subscription popup shown');
            
            // Update status
            if (window.voiceBot) {
                window.voiceBot.updateStatus('🎯 Choose your perfect plan above!');
            }
        }
    }

    function closeSubscriptionPopup() {
        const popup = document.getElementById('subscriptionPopup');
        if (popup) {
            popup.style.display = 'none';
            
            // Update status
            if (window.voiceBot) {
                window.voiceBot.updateStatus('🎙️ Ready! Say "subscribe" to see plans again');
            }
        }
    }

    function selectPlan(planType) {
        // Log the plan selection
        console.log(`📊 Plan selected: ${planType}`);
        
        // Redirect to subscription page with plan parameter
        const subscriptionUrl = `https://ringlypro.com/subscribe?plan=${planType}`;
        
        // Show confirmation before redirect
        const planNames = {
            'starter': 'Scheduling Assistant ($97/month)',
            'pro': 'Office Manager ($297/month)',
            'premium': 'Marketing Director ($497/month)'
        };
        
        const selectedPlanName = planNames[planType] || planType;
        
        // Update the popup content to show confirmation
        const container = document.querySelector('.subscription-popup-container');
        if (container) {
            container.innerHTML = `
                <div class="subscription-header" style="padding: 60px 20px;">
                    <h2>🎉 Excellent Choice!</h2>
                    <p style="font-size: 1.3rem; margin: 20px 0;">You selected: <strong>${selectedPlanName}</strong></p>
                    <p style="color: #666; margin-bottom: 30px;">Redirecting you to complete your subscription...</p>
                    <div style="display: flex; gap: 20px; justify-content: center; flex-wrap: wrap;">
                        <button class="plan-btn" style="width: auto; padding: 15px 40px;" onclick="window.open('${subscriptionUrl}', '_blank')">
                            Complete Subscription →
                        </button>
                        <button class="contact-sales-btn" style="width: auto; padding: 15px 40px;" onclick="contactSales()">
                            Talk to Sales First
                        </button>
                    </div>
                    <p style="margin-top: 30px; color: #999;">
                        Or call us directly at <strong>(888) 610-3810</strong>
                    </p>
                </div>
            `;
        }
        
        // Redirect after a short delay
        setTimeout(() => {
            window.open(subscriptionUrl, '_blank');
        }, 2000);
    }

    function contactSales() {
        // Close the subscription popup
        closeSubscriptionPopup();
        
        // Show the booking form for sales consultation
        if (window.voiceBot && window.voiceBot.showInlineBookingForm) {
            window.voiceBot.showInlineBookingForm();
            
            // Pre-fill the purpose field if possible
            setTimeout(() => {
                const purposeField = document.getElementById('inlineAppointmentPurpose');
                if (purposeField) {
                    purposeField.value = 'Sales consultation - Interested in RinglyPro subscription plans';
                }
            }, 100);
        } else {
            // Fallback: redirect to contact page
            window.location.href = '/chat-enhanced';
        }
    }

    // Initialize when page loads
    document.addEventListener('DOMContentLoaded', () => {
        try {
            window.voiceBot = new EnhancedVoiceBot();
            console.log('Voice bot initialized successfully');
        } catch (error) {
            console.error('Failed to create voice bot:', error);
        }
    });

    // Booking form functions remain the same
    let selectedInlineTimeSlot = null;

    function closeBookingForm() {
        const overlay = document.getElementById('bookingFormOverlay');
        overlay.style.display = 'none';
        if (window.voiceBot) {
            window.voiceBot.updateStatus('🎙️ Ready! Say "book appointment" for instant booking');
        }
    }

    function loadInlineAvailableSlots() {
        const date = document.getElementById('inlineAppointmentDate').value;
        if (!date) return;
        
        fetch('/get-available-slots', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date: date })
        })
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('inlineTimeSlotsContainer');
            const slotsDiv = document.getElementById('inlineAvailableSlots');
            
            if (data.slots && data.slots.length > 0) {
                slotsDiv.innerHTML = '';
                data.slots.forEach(slot => {
                    const slotBtn = document.createElement('div');
                    slotBtn.className = 'time-slot';
                    slotBtn.textContent = formatTimeSlot(slot);
                    slotBtn.onclick = () => selectInlineTimeSlot(slot, slotBtn);
                    slotsDiv.appendChild(slotBtn);
                });
                container.style.display = 'block';
            } else {
                slotsDiv.innerHTML = '<p style="color: #f44336; margin: 10px 0;">No available slots for this date. Please choose another date.</p>';
                container.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Error loading slots:', error);
        });
    }

    function selectInlineTimeSlot(time, element) {
        document.querySelectorAll('#inlineAvailableSlots .time-slot').forEach(slot => 
            slot.classList.remove('selected')
        );
        element.classList.add('selected');
        selectedInlineTimeSlot = time;
    }

    function formatTimeSlot(time) {
        const [hours, minutes] = time.split(':');
        const hour = parseInt(hours);
        const ampm = hour >= 12 ? 'PM' : 'AM';
        const displayHour = hour > 12 ? hour - 12 : (hour === 0 ? 12 : hour);
        return `${displayHour}:${minutes} ${ampm}`;
    }

    function submitInlineBooking() {
        const name = document.getElementById('inlineCustomerName').value.trim();
        const email = document.getElementById('inlineCustomerEmail').value.trim();
        const phone = document.getElementById('inlineCustomerPhone').value.trim();
        const date = document.getElementById('inlineAppointmentDate').value;
        const purpose = document.getElementById('inlineAppointmentPurpose').value.trim();
        
        if (!name || !email || !phone || !date || !selectedInlineTimeSlot) {
            alert('Please fill in all required fields and select a time slot.');
            return;
        }
        
        const submitBtn = document.querySelector('.booking-submit-btn');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Booking...';
        
        const bookingData = {
            name: name,
            email: email,
            phone: phone,
            date: date,
            time: selectedInlineTimeSlot,
            purpose: purpose || 'General consultation'
        };
        
        fetch('/book-appointment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(bookingData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showInlineBookingConfirmation(data.appointment);
            } else {
                showInlineBookingError(data.message);
            }
        })
        .catch(error => {
            console.error('Booking error:', error);
            showInlineBookingError('There was an error booking your appointment. Please try again.');
        })
        .finally(() => {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Book Appointment';
        });
    }

    function showInlineBookingConfirmation(appointment) {
        const container = document.querySelector('.booking-form-container');
        
        const date = new Date(appointment.date + 'T' + appointment.time);
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        const formattedDate = date.toLocaleDateString('en-US', options);
        const formattedTime = formatTimeSlot(appointment.time);
        
        container.innerHTML = `
            <div class="booking-form-header">
                <button class="close-booking-form" onclick="closeBookingForm()">×</button>
                <h2>✅ Appointment Confirmed!</h2>
                <p>Your appointment has been successfully scheduled</p>
            </div>
            
            <div style="background: linear-gradient(135deg, #e8f5e8, #c8e6c9); color: #2e7d32; padding: 20px; border-radius: 12px; margin-bottom: 20px;">
                <div style="background: white; padding: 15px; border-radius: 8px;">
                    <strong>📅 Date:</strong> ${formattedDate}<br>
                    <strong>🕐 Time:</strong> ${formattedTime} EST<br>
                    <strong>👤 Name:</strong> ${appointment.customer_name}<br>
                    <strong>📧 Email:</strong> ${appointment.customer_email}<br>
                    <strong>📞 Phone:</strong> ${appointment.customer_phone}<br>
                    <strong>🔗 Zoom:</strong> <a href="${appointment.zoom_url}" target="_blank" style="color: #2196F3;">Join Meeting</a><br>
                    <strong>📋 Confirmation:</strong> <span style="font-family: monospace; background: #f0f0f0; padding: 4px 8px; border-radius: 4px;">${appointment.confirmation_code}</span><br>
                    <strong>💬 Purpose:</strong> ${appointment.purpose}
                </div>
                <p style="margin-top: 15px; font-size: 14px;">
                    You'll receive email and SMS confirmations shortly. Save your confirmation code for any changes needed.
                </p>
            </div>
            
            <button type="button" class="booking-submit-btn" onclick="closeBookingForm()" style="background: linear-gradient(135deg, #2196F3, #1976D2);">
                Close & Continue
            </button>
        `;
        
        if (window.voiceBot) {
            window.voiceBot.updateStatus('✅ Appointment booked successfully!');
        }
    }

    function showInlineBookingError(message) {
        const form = document.getElementById('inlineBookingForm');
        
        const existingError = form.querySelector('.error-message');
        if (existingError) existingError.remove();
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.style.cssText = 'background: linear-gradient(135deg, #ffebee, #ffcdd2); border: 2px solid #f44336; color: #c62828; padding: 15px; border-radius: 12px; margin: 15px 0;';
        errorDiv.innerHTML = `<strong>❌ Error:</strong><br>${message}`;
        
        form.insertBefore(errorDiv, form.firstChild);
        errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
</script>
</body>
</html>
'''

CHAT_HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RinglyPro Chat Assistant</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .chat-container {
            width: 100%;
            max-width: 500px;
            height: 600px;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            position: relative;
        }
        
        .header {
            background: linear-gradient(135deg, #2196F3, #1976D2);
            color: white;
            padding: 20px;
            text-align: center;
            position: relative;
        }
        
        .interface-switcher {
            position: absolute;
            top: 15px;
            right: 15px;
            background: rgba(255, 255, 255, 0.2);
            border: none;
            border-radius: 12px;
            color: white;
            padding: 8px 12px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.3s ease;
        }
        
        .interface-switcher:hover {
            background: rgba(255, 255, 255, 0.3);
        }
        
        .header h1 {
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 5px;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 0.9rem;
        }
        
        .chat-messages {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            background: white;
        }
        
        .message {
            margin-bottom: 15px;
            max-width: 85%;
            animation: fadeIn 0.3s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .message.user {
            margin-left: auto;
        }
        
        .message-content {
            padding: 12px 16px;
            border-radius: 18px;
            font-size: 14px;
            line-height: 1.4;
        }
        
        .message.bot .message-content {
            background: #f1f3f4;
            color: #333;
            border-bottom-left-radius: 6px;
        }
        
        .message.user .message-content {
            background: #2196F3;
            color: white;
            text-align: right;
            border-bottom-right-radius: 6px;
        }
        
        .input-area {
            padding: 20px;
            background: white;
            border-top: 1px solid #e0e0e0;
        }
        
        .input-container {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        .input-container input {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            outline: none;
            font-size: 14px;
            transition: border-color 0.3s ease;
        }
        
        .input-container input:focus {
            border-color: #2196F3;
        }
        
        .send-btn {
            width: 45px;
            height: 45px;
            background: #2196F3;
            border: none;
            border-radius: 50%;
            color: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
            font-size: 18px;
        }
        
        .send-btn:hover {
            background: #1976D2;
            transform: scale(1.05);
        }
        
        .phone-form { 
            background: #fff3e0; 
            border: 2px solid #ff9800; 
            border-radius: 12px; 
            padding: 15px; 
            margin: 10px 0;
        }
        
        .phone-form h4 { color: #e65100; margin-bottom: 8px; font-size: 14px; }
        .phone-form p { color: #bf360c; margin-bottom: 12px; font-size: 13px; }
        
        .phone-inputs { display: flex; gap: 8px; margin-top: 10px; }
        
        .phone-inputs input { 
            flex: 1; 
            padding: 10px; 
            border: 1px solid #ff9800; 
            border-radius: 8px; 
            background: white;
            color: #333;
            outline: none;
        }
        
        .phone-inputs input::placeholder {
            color: #999;
        }
        
        .phone-btn { 
            padding: 10px 16px; 
            background: #4caf50; 
            color: white; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer;
        }
        
        .success { 
            background: #e8f5e8; 
            border: 2px solid #4caf50; 
            color: #2e7d32; 
            padding: 12px; 
            border-radius: 8px; 
            margin: 10px 0;
        }
        
        .error { 
            background: #ffebee; 
            border: 2px solid #f44336; 
            color: #c62828; 
            padding: 12px; 
            border-radius: 8px; 
            margin: 10px 0;
        }

        .chat::-webkit-scrollbar {
            width: 4px;
        }
        
        .chat::-webkit-scrollbar-track {
            background: #f1f1f1;
        }
        
        .chat::-webkit-scrollbar-thumb {
            background: #c1c1c1;
            border-radius: 2px;
        }
        
        .chat::-webkit-scrollbar-thumb:hover {
            background: #a1a1a1;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="header">
            <button class="interface-switcher" onclick="window.location.href='/'">🎤 Voice Chat</button>
            <h1>💬 RinglyPro Assistant</h1>
            <p>Ask me anything about our services!</p>
        </div>
        
        <div class="chat-messages" id="chatMessages">
            <div class="message bot">
                <div class="message-content">
                    👋 Hello! I'm your RinglyPro assistant. Ask me about our services, pricing, features, or how to get started. If I can't answer your question, I'll connect you with our customer service team!
                </div>
            </div>
        </div>
        
        <div class="input-area">
            <div class="input-container">
                <input type="text" id="userInput" placeholder="Ask about RinglyPro services..." onkeypress="handleKeyPress(event)">
                <button class="send-btn" onclick="sendMessage()">→</button>
            </div>
        </div>
    </div>

    <script>
        let isWaitingForResponse = false;

        function handleKeyPress(event) {
            if (event.key === 'Enter' && !isWaitingForResponse) {
                sendMessage();
            }
        }

        function sendMessage() {
            if (isWaitingForResponse) return;
            
            const input = document.getElementById('userInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            addMessage(message, 'user');
            input.value = '';
            showTypingIndicator();
            
            isWaitingForResponse = true;
            
            fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            })
            .then(response => response.json())
            .then(data => {
                hideTypingIndicator();
                addMessage(data.response, 'bot');
                
                if (data.needs_phone_collection) {
                    setTimeout(() => showPhoneForm(), 500);
                }
                
                isWaitingForResponse = false;
            })
            .catch(error => {
                console.error('Error:', error);
                hideTypingIndicator();
                addMessage('Sorry, there was an error processing your request. Please try again.', 'bot');
                isWaitingForResponse = false;
            });
        }

        function addMessage(message, sender) {
            const chatMessages = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.textContent = message;
            
            messageDiv.appendChild(contentDiv);
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function showTypingIndicator() {
            const chatMessages = document.getElementById('chatMessages');
            const typingDiv = document.createElement('div');
            typingDiv.id = 'typingIndicator';
            typingDiv.className = 'typing-indicator';
            typingDiv.innerHTML = `
                RinglyPro is typing
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            `;
            chatMessages.appendChild(typingDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function hideTypingIndicator() {
            const typingIndicator = document.getElementById('typingIndicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }
        }

        function showPhoneForm() {
            const chatMessages = document.getElementById('chatMessages');
            const phoneFormDiv = document.createElement('div');
            phoneFormDiv.className = 'phone-form';
            phoneFormDiv.innerHTML = `
                <h4>📞 Let's connect you with our team!</h4>
                <p>Please enter your phone number so our customer service team can provide personalized assistance:</p>
                <div class="phone-inputs">
                    <input type="tel" id="phoneInput" placeholder="(555) 123-4567" style="flex: 1;">
                    <button class="phone-btn" onclick="submitPhone()">Submit</button>
                </div>
            `;
            chatMessages.appendChild(phoneFormDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            setTimeout(() => {
                const phoneInput = document.getElementById('phoneInput');
                if (phoneInput) phoneInput.focus();
            }, 100);
        }

        function submitPhone() {
            const phoneInput = document.getElementById('phoneInput');
            const phoneNumber = phoneInput.value.trim();
            
            if (!phoneNumber) {
                alert('Please enter a phone number.');
                return;
            }
            
            fetch('/submit_phone', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    phone: phoneNumber,
                    last_question: sessionStorage.getItem('lastQuestion') || 'Chat inquiry'
                })
            })
            .then(response => response.json())
            .then(data => {
                const chatMessages = document.getElementById('chatMessages');
                
                const responseDiv = document.createElement('div');
                responseDiv.className = data.success ? 'success-message' : 'error-message';
                responseDiv.innerHTML = `
                    <strong>${data.success ? '✅ Success!' : '❌ Error:'}</strong><br>
                    ${data.message}
                `;
                chatMessages.appendChild(responseDiv);
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

ENHANCED_CHAT_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RinglyPro Appointment Assistant</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh; display: flex; justify-content: center; align-items: center;
        }
        
        .chat-container {
            width: 100%; max-width: 500px; height: 600px;
            background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(20px);
            border-radius: 20px; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            display: flex; flex-direction: column; overflow: hidden; position: relative;
        }
        
        .header {
            background: linear-gradient(135deg, #2196F3, #1976D2); color: white;
            padding: 20px; text-align: center; position: relative;
        }
        
        .interface-switcher {
            position: absolute; top: 15px; right: 15px;
            background: rgba(255, 255, 255, 0.2); border: none; border-radius: 12px;
            color: white; padding: 8px 12px; cursor: pointer; font-size: 12px;
            transition: all 0.3s ease;
        }
        
        .interface-switcher:hover { background: rgba(255, 255, 255, 0.3); }
        
        .header h1 { font-size: 1.5rem; font-weight: 700; margin-bottom: 5px; }
        .header p { opacity: 0.9; font-size: 0.9rem; }
        
        .chat-messages {
            flex: 1; padding: 20px; overflow-y: auto; background: white;
        }
        
        .message {
            margin-bottom: 15px; max-width: 85%; animation: fadeIn 0.3s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .message.user { margin-left: auto; }
        
        .message-content {
            padding: 12px 16px; border-radius: 18px; font-size: 14px; line-height: 1.4;
        }
        
        .message.bot .message-content {
            background: #f1f3f4; color: #333; border-bottom-left-radius: 6px;
        }
        
        .message.user .message-content {
            background: #2196F3; color: white; text-align: right; border-bottom-right-radius: 6px;
        }
        
        .booking-form {
            background: linear-gradient(135deg, #e3f2fd, #bbdefb);
            border: 2px solid #2196f3; border-radius: 15px; padding: 20px; margin: 15px 0;
            animation: slideIn 0.5s ease;
        }
        
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .booking-form h4 { color: #0d47a1; margin-bottom: 15px; font-size: 16px; }
        
        .form-group { margin-bottom: 15px; }
        
        .form-group label {
            display: block; margin-bottom: 5px; color: #1565c0; font-weight: 600;
        }
        
        .form-group input, .form-group select, .form-group textarea {
            width: 100%; padding: 10px 12px; border: 2px solid #2196f3;
            border-radius: 10px; outline: none; font-size: 14px;
        }
        
        .form-group input:focus, .form-group select:focus, .form-group textarea:focus {
            border-color: #1976d2;
        }
        
        .date-time-row { display: flex; gap: 10px; }
        .date-time-row .form-group { flex: 1; }
        
        .available-slots {
            display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px;
        }
        
        .time-slot {
            padding: 8px 12px; background: #e3f2fd; border: 2px solid #2196f3;
            border-radius: 8px; cursor: pointer; font-size: 12px; color: #1565c0;
            transition: all 0.3s ease;
        }
        
        .time-slot:hover, .time-slot.selected {
            background: #2196f3; color: white;
        }
        
        .submit-btn {
            width: 100%; padding: 12px; background: linear-gradient(135deg, #4caf50, #45a049);
            color: white; border: none; border-radius: 10px; cursor: pointer;
            font-weight: 600; font-size: 14px; transition: all 0.3s ease;
        }
        
        .submit-btn:hover {
            background: linear-gradient(135deg, #45a049, #388e3c);
            transform: translateY(-2px);
        }
        
        .submit-btn:disabled {
            opacity: 0.6; cursor: not-allowed; transform: none;
        }
        
        .input-area {
            padding: 20px; background: white; border-top: 1px solid #e0e0e0;
        }
        
        .input-container {
            display: flex; gap: 10px; align-items: center;
        }
        
        .input-container input {
            flex: 1; padding: 12px 16px; border: 2px solid #e0e0e0;
            border-radius: 25px; outline: none; font-size: 14px;
            transition: border-color 0.3s ease;
        }
        
        .input-container input:focus { border-color: #2196F3; }
        
        .send-btn {
            width: 45px; height: 45px; background: #2196F3; border: none;
            border-radius: 50%; color: white; cursor: pointer;
            display: flex; align-items: center; justify-content: center;
            transition: all 0.3s ease; font-size: 18px;
        }
        
        .send-btn:hover {
            background: #1976D2; transform: scale(1.05);
        }
        
        .success-message {
            background: linear-gradient(135deg, #e8f5e8, #c8e6c9);
            border: 2px solid #4caf50; color: #2e7d32;
            padding: 15px; border-radius: 12px; margin: 15px 0;
        }
        
        .error-message {
            background: linear-gradient(135deg, #ffebee, #ffcdd2);
            border: 2px solid #f44336; color: #c62828;
            padding: 15px; border-radius: 12px; margin: 15px 0;
        }
        
        .chat-messages::-webkit-scrollbar { width: 4px; }
        .chat-messages::-webkit-scrollbar-track { background: #f1f1f1; }
        .chat-messages::-webkit-scrollbar-thumb { background: #c1c1c1; border-radius: 2px; }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="header">
            <button class="interface-switcher" onclick="window.location.href='/'">🎤 Voice Chat</button>
            <h1>📅 RinglyPro Booking Assistant</h1>
            <p>Schedule appointments & get answers instantly!</p>
        </div>
        
        <div class="chat-messages" id="chatMessages">
            <div class="message bot">
                <div class="message-content">
                    👋 Hello! I'm your RinglyPro booking assistant. I can help you:
                    
                    📅 Schedule a free consultation
                    💬 Answer questions about our services
                    💰 Explain our pricing plans
                    🔧 Describe our features
                    
                    Just type "book appointment" or ask me anything!
                </div>
            </div>
        </div>
        
        <div class="input-area">
            <div class="input-container">
                <input type="text" id="userInput" placeholder="Type 'book appointment' or ask a question..." onkeypress="handleKeyPress(event)">
                <button class="send-btn" onclick="sendMessage()">→</button>
            </div>
        </div>
    </div>

    <script>
        let isWaitingForResponse = false;
        let bookingStep = 'none';
        let bookingData = {};
        let selectedTimeSlot = null;

        function handleKeyPress(event) {
            if (event.key === 'Enter' && !isWaitingForResponse) {
                sendMessage();
            }
        }

        function sendMessage() {
            if (isWaitingForResponse) return;
            
            const input = document.getElementById('userInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            addMessage(message, 'user');
            input.value = '';
            
            isWaitingForResponse = true;
            
            fetch('/chat-enhanced', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    message: message,
                    booking_step: bookingStep,
                    booking_data: bookingData
                })
            })
            .then(response => response.json())
            .then(data => {
                console.log('Response data:', data);
                
                addMessage(data.response, 'bot');
                
                if (data.action === 'start_booking') {
                    console.log('Starting booking process');
                    bookingStep = 'form_ready';
                    setTimeout(() => showBookingForm(), 500);
                } else if (data.booking_step) {
                    bookingStep = data.booking_step;
                }
                
                isWaitingForResponse = false;
            })
            .catch(error => {
                console.error('Error:', error);
                addMessage('Sorry, there was an error. Please try again.', 'bot');
                isWaitingForResponse = false;
            });
        }

        function addMessage(message, sender) {
            const chatMessages = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.textContent = message;
            
            messageDiv.appendChild(contentDiv);
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function showBookingForm() {
            const chatMessages = document.getElementById('chatMessages');
            const formDiv = document.createElement('div');
            formDiv.className = 'booking-form';
            formDiv.innerHTML = `
                <h4>📅 Schedule Your Free Consultation</h4>
                <form id="appointmentForm">
                    <div class="form-group">
                        <label>Full Name *</label>
                        <input type="text" id="customerName" required>
                    </div>
                    
                    <div class="form-group">
                        <label>Email Address *</label>
                        <input type="email" id="customerEmail" required>
                    </div>
                    
                    <div class="form-group">
                        <label>Phone Number *</label>
                        <input type="tel" id="customerPhone" placeholder="(555) 123-4567" required>
                    </div>
                    
                    <div class="date-time-row">
                        <div class="form-group">
                            <label>Preferred Date *</label>
                            <input type="date" id="appointmentDate" min="${new Date().toISOString().split('T')[0]}" onchange="loadAvailableSlots()" required>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label>What would you like to discuss?</label>
                        <textarea id="appointmentPurpose" rows="3" placeholder="Brief description of your needs..."></textarea>
                    </div>
                    
                    <div id="timeSlotsContainer" style="display: none;">
                        <label>Available Times *</label>
                        <div id="availableSlots" class="available-slots"></div>
                    </div>
                    
                    <button type="button" class="submit-btn" onclick="submitBooking()">Book Appointment</button>
                </form>
            `;
            
            chatMessages.appendChild(formDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            // Focus on first field
            setTimeout(() => {
                document.getElementById('customerName').focus();
            }, 100);
        }

        function loadAvailableSlots() {
            const date = document.getElementById('appointmentDate').value;
            if (!date) return;
            
            fetch('/get-available-slots', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ date: date })
            })
            .then(response => response.json())
            .then(data => {
                const container = document.getElementById('timeSlotsContainer');
                const slotsDiv = document.getElementById('availableSlots');
                
                if (data.slots && data.slots.length > 0) {
                    slotsDiv.innerHTML = '';
                    data.slots.forEach(slot => {
                        const slotBtn = document.createElement('div');
                        slotBtn.className = 'time-slot';
                        slotBtn.textContent = formatTimeSlot(slot);
                        slotBtn.onclick = () => selectTimeSlot(slot, slotBtn);
                        slotsDiv.appendChild(slotBtn);
                    });
                    container.style.display = 'block';
                } else {
                    slotsDiv.innerHTML = '<p style="color: #f44336;">No available slots for this date. Please choose another date.</p>';
                    container.style.display = 'block';
                }
            })
            .catch(error => {
                console.error('Error loading slots:', error);
            });
        }

        function selectTimeSlot(time, element) {
            // Remove previous selection
            document.querySelectorAll('.time-slot').forEach(slot => {
                slot.classList.remove('selected');
            });
            
            // Add selection to clicked slot
            element.classList.add('selected');
            selectedTimeSlot = time;
        }

        function formatTimeSlot(time) {
            const [hours, minutes] = time.split(':');
            const hour = parseInt(hours);
            const ampm = hour >= 12 ? 'PM' : 'AM';
            const displayHour = hour > 12 ? hour - 12 : (hour === 0 ? 12 : hour);
            return `${displayHour}:${minutes} ${ampm}`;
        }

        function submitBooking() {
            const name = document.getElementById('customerName').value.trim();
            const email = document.getElementById('customerEmail').value.trim();
            const phone = document.getElementById('customerPhone').value.trim();
            const date = document.getElementById('appointmentDate').value;
            const purpose = document.getElementById('appointmentPurpose').value.trim();
            
            if (!name || !email || !phone || !date || !selectedTimeSlot) {
                alert('Please fill in all required fields and select a time slot.');
                return;
            }
            
            // Disable submit button
            const submitBtn = document.querySelector('.submit-btn');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Booking...';
            
            const bookingData = {
                name: name,
                email: email,
                phone: phone,
                date: date,
                time: selectedTimeSlot,
                purpose: purpose || 'General consultation'
            };
            
            fetch('/book-appointment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(bookingData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showBookingConfirmation(data.appointment);
                } else {
                    showBookingError(data.message);
                }
            })
            .catch(error => {
                console.error('Booking error:', error);
                showBookingError('There was an error booking your appointment. Please try again.');
            })
            .finally(() => {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Book Appointment';
            });
        }

        function showBookingConfirmation(appointment) {
            const chatMessages = document.getElementById('chatMessages');
            
            // Remove the booking form
            const bookingForm = document.querySelector('.booking-form');
            if (bookingForm) bookingForm.remove();
            
            // Format date and time for display
            const date = new Date(appointment.date + 'T' + appointment.time);
            const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
            const formattedDate = date.toLocaleDateString('en-US', options);
            const formattedTime = formatTimeSlot(appointment.time);
            
            // Add confirmation message
            const confirmDiv = document.createElement('div');
            confirmDiv.className = 'success-message';
            confirmDiv.innerHTML = `
                <strong>✅ Appointment Confirmed!</strong><br><br>
                📅 <strong>Date:</strong> ${formattedDate}<br>
                🕐 <strong>Time:</strong> ${formattedTime} EST<br>
                👤 <strong>Name:</strong> ${appointment.customer_name}<br>
                📧 <strong>Email:</strong> ${appointment.customer_email}<br>
                📞 <strong>Phone:</strong> ${appointment.customer_phone}<br>
                🔗 <strong>Zoom Link:</strong> <a href="${appointment.zoom_url}" target="_blank" style="color: #2196F3;">Join Meeting</a><br>
                📋 <strong>Confirmation Code:</strong> ${appointment.confirmation_code}<br><br>
                
                You'll receive email and SMS confirmations shortly. Save your confirmation code for any changes.
            `;
            
            chatMessages.appendChild(confirmDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            // Reset booking state
            bookingStep = 'none';
            bookingData = {};
            selectedTimeSlot = null;
        }

        function showBookingError(message) {
            const chatMessages = document.getElementById('chatMessages');
            
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            errorDiv.innerHTML = `<strong>❌ Booking Error:</strong><br>${message}`;
            
            chatMessages.appendChild(errorDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    </script>
</body>
</html>
'''
# ==================== ROUTES ====================

@app.route('/')
def serve_index():
    """Voice interface"""
    return render_template_string(VOICE_HTML_TEMPLATE)

@app.route('/chat')
def serve_chat():
    """Text chat interface"""
    return render_template_string(CHAT_HTML_TEMPLATE)

@app.route('/chat-enhanced')
def serve_enhanced_chat():
    """Enhanced chat interface with appointment booking"""
    return render_template_string(ENHANCED_CHAT_TEMPLATE)

@app.route('/chat', methods=['POST'])
def handle_chat():
    """Handle chat messages with SMS integration"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'response': 'Please enter a question.', 'needs_phone_collection': False})
        
        # Store the question in session for potential phone collection
        session['last_question'] = user_message
        
        logger.info(f"💬 Chat message received: {user_message}")
        
        # Get FAQ response with SMS capability
        response, is_faq_match, needs_phone_collection = get_faq_response_with_sms(user_message)
        
        logger.info(f"📋 FAQ match: {is_faq_match}, Phone collection needed: {needs_phone_collection}")
        
        return jsonify({
            'response': response,
            'needs_phone_collection': needs_phone_collection,
            'is_faq_match': is_faq_match
        })
        
    except Exception as e:
        logger.error(f"❌ Error in chat endpoint: {str(e)}")
        return jsonify({
            'response': 'Sorry, there was an error processing your request. Please try again.',
            'needs_phone_collection': False
        }), 500

@app.route('/chat-enhanced', methods=['POST'])
def handle_enhanced_chat():
    """Enhanced chat handler with appointment booking capabilities"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        booking_step = data.get('booking_step', 'none')
        booking_data = data.get('booking_data', {})
        
        if not user_message:
            return jsonify({'response': 'Please enter a question.', 'action': 'none'})
        
        logger.info(f"💬 Enhanced chat message: {user_message}")
        logger.info(f"📊 Current booking step: {booking_step}")
        
        user_message_lower = user_message.lower().strip()
        
        # Handle follow-up responses based on conversation context
        if booking_step == 'awaiting_confirmation':
            logger.info("🔄 Processing follow-up response")
            if user_message_lower in ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'y']:
                logger.info("✅ User confirmed booking")
                return jsonify({
                    'response': 'Perfect! Let me set up the booking form for you.',
                    'action': 'start_booking',
                    'booking_step': 'form_ready',
                    'is_faq_match': True
                })
            elif user_message_lower in ['no', 'nope', 'not now', 'maybe later', 'n']:
                logger.info("❌ User declined booking")
                return jsonify({
                    'response': 'No problem! Feel free to ask me any questions about RinglyPro services, or let me know if you change your mind about scheduling.',
                    'action': 'none',
                    'booking_step': 'none',
                    'is_faq_match': True
                })
        
        # Get enhanced FAQ response
        response, is_faq_match, action_needed = get_enhanced_faq_response(user_message)
        
        logger.info(f"📤 Response: {response[:50]}...")
        logger.info(f"🎬 Action needed: {action_needed}")
        
        response_data = {
            'response': response,
            'is_faq_match': is_faq_match,
            'action': action_needed,
            'booking_step': booking_step
        }
        
        # Handle specific booking actions
        if action_needed == "start_booking":
            logger.info("🚀 Setting action to start_booking")
            response_data['action'] = 'start_booking'
            response_data['booking_step'] = 'form_ready'
        elif action_needed == "suggest_booking":
            response_data['response'] += " Type 'yes' if you'd like to schedule a consultation."
            response_data['booking_step'] = 'awaiting_confirmation'
        elif action_needed == "offer_booking":
            response_data['booking_step'] = 'awaiting_confirmation'
        
        logger.info(f"📨 Final response data: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"❌ Error in enhanced chat endpoint: {str(e)}")
        return jsonify({
            'response': 'Sorry, there was an error processing your request. Please try again.',
            'action': 'none'
        }), 500

@app.route('/get-available-slots', methods=['POST'])
def get_available_slots():
    """Get available appointment slots for a date"""
    try:
        data = request.get_json()
        date = data.get('date')
        
        if not date:
            return jsonify({'error': 'Date is required'}), 400
        
        slots = AppointmentManager.get_available_slots(date)
        
        return jsonify({
            'success': True,
            'date': date,
            'slots': slots
        })
        
    except Exception as e:
        logger.error(f"Error getting available slots: {e}")
        return jsonify({'error': 'Failed to get available slots'}), 500

@app.route('/book-appointment', methods=['POST'])
def book_appointment():
    """Book a new appointment"""
    try:
        data = request.get_json()
        
        appointment_manager = AppointmentManager()
        success, message, appointment = appointment_manager.book_appointment(data)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'appointment': appointment
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error booking appointment: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to book appointment'
        }), 500

@app.route('/appointment/<confirmation_code>')
def get_appointment(confirmation_code):
    """Get appointment details by confirmation code"""
    try:
        appointment = AppointmentManager.get_appointment_by_code(confirmation_code)
        
        if appointment:
            return jsonify({
                'success': True,
                'appointment': appointment
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Appointment not found'
            }), 404
            
    except Exception as e:
        logger.error(f"Error getting appointment: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve appointment'
        }), 500

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
        
        logger.info(f"📞 Phone submitted: {validated_phone}, Question: {last_question}")
        
        # Send SMS notification
        sms_success, sms_result = send_sms_notification(validated_phone, last_question)
        
        # Save to database
        db_saved = save_customer_inquiry(validated_phone, last_question, sms_success, sms_result)
        
        if sms_success:
            success_message = f'Perfect! We\'ve received your phone number ({validated_phone}) and notified our customer service team about your question: "{last_question}". They\'ll reach out to you shortly to provide personalized assistance.'
        else:
            success_message = f'Thank you for providing your phone number ({validated_phone}). We\'ve recorded your inquiry about "{last_question}" and our customer service team will contact you soon.'
        
        return jsonify({
            'success': True,
            'message': success_message
        })
            
    except Exception as e:
        logger.error(f"❌ Error in submit_phone endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'There was an error processing your request. Please try again or contact us directly at (656) 213-3300.'
        })
@app.route('/test-appointment-system', methods=['GET'])
def test_appointment_system():
    """Test appointment system configuration and integrations"""
    try:
        results = {
            "timestamp": datetime.now().isoformat(),
            "configurations": {},
            "tests": {}
        }
        
        # Check environment variables
        results["configurations"] = {
            "hubspot": {
                "api_token_configured": bool(hubspot_api_token),
                "token_preview": hubspot_api_token[:20] + "..." if hubspot_api_token else None,
                "portal_id": hubspot_portal_id,
                "owner_id": hubspot_owner_id
            },
            "email": {
                "smtp_server": smtp_server,
                "smtp_port": smtp_port,
                "email_user_configured": bool(email_user),
                "email_password_configured": bool(email_password),
                "from_email": from_email
            },
            "twilio": {
                "account_sid_configured": bool(twilio_account_sid),
                "auth_token_configured": bool(twilio_auth_token),
                "phone_number": twilio_phone
            },
            "zoom": {
                "meeting_url": zoom_meeting_url,
                "meeting_id": zoom_meeting_id,
                "password": zoom_password
            }
        }
        
        # Test HubSpot connection
        if hubspot_api_token:
            hubspot_service = HubSpotService()
            hubspot_test = hubspot_service.test_connection()
            results["tests"]["hubspot"] = hubspot_test
        else:
            results["tests"]["hubspot"] = {"success": False, "error": "No API token configured"}
        
        # Test email configuration
        if email_user and email_password:
            try:
                import smtplib
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
                server.login(email_user, email_password)
                server.quit()
                results["tests"]["email"] = {"success": True, "message": "Email configuration valid"}
            except Exception as e:
                results["tests"]["email"] = {"success": False, "error": str(e)}
        else:
            results["tests"]["email"] = {"success": False, "error": "Email credentials not configured"}
        
        # Test Twilio configuration
        if twilio_account_sid and twilio_auth_token:
            try:
                from twilio.rest import Client
                client = Client(twilio_account_sid, twilio_auth_token)
                # Just try to fetch account info
                account = client.api.accounts(twilio_account_sid).fetch()
                results["tests"]["twilio"] = {
                    "success": True, 
                    "message": "Twilio configuration valid",
                    "account_status": account.status
                }
            except Exception as e:
                results["tests"]["twilio"] = {"success": False, "error": str(e)}
        else:
            results["tests"]["twilio"] = {"success": False, "error": "Twilio credentials not configured"}
        
        # Check recent appointments in database
        try:
            conn = sqlite3.connect('ringlypro.db')
            cursor = conn.cursor()
            
            # Get last 5 appointments
            cursor.execute('''SELECT customer_name, customer_email, customer_phone, 
                             appointment_date, appointment_time, confirmation_code,
                             hubspot_contact_id, hubspot_meeting_id, created_at
                             FROM appointments 
                             ORDER BY created_at DESC 
                             LIMIT 5''')
            recent_appointments = cursor.fetchall()
            
            results["recent_appointments"] = []
            for apt in recent_appointments:
                results["recent_appointments"].append({
                    "name": apt[0],
                    "email": apt[1],
                    "phone": apt[2],
                    "date": apt[3],
                    "time": apt[4],
                    "confirmation": apt[5],
                    "hubspot_contact": apt[6],
                    "hubspot_meeting": apt[7],
                    "created": apt[8]
                })
            
            conn.close()
        except Exception as e:
            results["database_error"] = str(e)
        
        # Format as HTML for easy reading
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Appointment System Test</title>
            <style>
                body {{ font-family: monospace; padding: 20px; background: #f0f0f0; }}
                .success {{ color: green; font-weight: bold; }}
                .error {{ color: red; font-weight: bold; }}
                .warning {{ color: orange; font-weight: bold; }}
                pre {{ background: white; padding: 15px; border-radius: 5px; }}
                h2 {{ color: #2196F3; }}
            </style>
        </head>
        <body>
            <h1>🔍 Appointment System Configuration Test</h1>
            <h2>Environment Status:</h2>
            <pre>{json.dumps(results["configurations"], indent=2)}</pre>
            
            <h2>Integration Tests:</h2>
            <pre>{json.dumps(results["tests"], indent=2)}</pre>
            
            <h2>Recent Appointments:</h2>
            <pre>{json.dumps(results.get("recent_appointments", []), indent=2)}</pre>
            
            <h2>Quick Fix Checklist:</h2>
            <ul>
        """
        
        # Add recommendations based on test results
        if not results["tests"].get("hubspot", {}).get("success"):
            html += "<li class='error'>❌ HubSpot: Check HUBSPOT_ACCESS_TOKEN environment variable</li>"
        else:
            html += "<li class='success'>✅ HubSpot: Connected</li>"
            
        if not results["tests"].get("email", {}).get("success"):
            html += "<li class='error'>❌ Email: Check EMAIL_USER and EMAIL_PASSWORD environment variables</li>"
        else:
            html += "<li class='success'>✅ Email: Connected</li>"
            
        if not results["tests"].get("twilio", {}).get("success"):
            html += "<li class='error'>❌ Twilio: Check TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables</li>"
        else:
            html += "<li class='success'>✅ Twilio: Connected</li>"
        
        html += """
            </ul>
            <h2>Test Booking:</h2>
            <button onclick="testBooking()">Test Book Appointment</button>
            <div id="result"></div>
            
            <script>
            function testBooking() {
                fetch('/book-appointment', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        name: 'Test User',
                        email: 'test@example.com',
                        phone: '(555) 123-4567',
                        date: new Date().toISOString().split('T')[0],
                        time: '14:00',
                        purpose: 'System test booking'
                    })
                })
                .then(r => r.json())
                .then(data => {
                    document.getElementById('result').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                });
            }
            </script>
        </body>
        </html>
        """
        
        return html
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/process-text-enhanced', methods=['POST'])
def process_text_enhanced():
    """Enhanced text processing with premium audio and subscription detection"""
    logger.info("🎤 Enhanced text processing request")
    
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            logger.error("❌ Missing text data")
            return jsonify({"error": "Missing text data"}), 400
            
        user_text = data['text'].strip()
        user_language = data.get('language', 'en-US')
        is_mobile = data.get('mobile', False)
        
        # Backend echo detection
        echo_phrases = [
            'ringly pro', 'i can help', 'scheduling', 'perfect', 'wonderful',
            'how can i help', 'i\'m here to help', 'that\'s great', 'absolutely'
        ]
        
        user_lower = user_text.lower()
        is_echo = any(phrase in user_lower for phrase in echo_phrases) and len(user_text) > 30
        
        if is_echo:
            logger.warning(f"🔄 Echo detected: {user_text[:50]}...")
            return jsonify({
                "response": "I think I heard an echo. Please speak again.",
                "language": user_language,
                "context": "clarification",
                "show_text": is_mobile
            })
        
        if not user_text or len(user_text) < 2:
            error_msg = ("Texto muy corto. Por favor intenta de nuevo." 
                        if user_language.startswith('es') 
                        else "Text too short. Please try again.")
            return jsonify({"error": error_msg}), 400
        
        logger.info(f"📝 Processing: {user_text}")
        
        # ENHANCED: Check for subscription intent FIRST (before booking)
        subscription_keywords = [
            'subscribe', 'subscription', 'sign up', 'signup', 'get started',
            'join', 'register', 'start service', 'want to subscribe',
            'i want to subscribe', 'interested in subscribing', 'how to subscribe',
            'ready to subscribe', 'start my subscription', 'become a member'
        ]
        
        subscription_detected = any(keyword in user_lower for keyword in subscription_keywords)
        
        if subscription_detected:
            logger.info("🎯 Subscription intent detected in voice!")
            subscription_response = "Wonderful! I'm excited to help you get started with RinglyPro. I'm opening our subscription options for you right now. You'll see our plans and can choose the one that best fits your business needs."
            
            # Try to generate premium audio with Rachel's voice
            audio_data = None
            engine_used = "browser_fallback"
            
            if elevenlabs_api_key:
                try:
                    voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel's voice
                    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
                    
                    headers = {
                        "Accept": "audio/mpeg",
                        "Content-Type": "application/json",
                        "xi-api-key": elevenlabs_api_key
                    }
                    
                    tts_data = {
                        "text": subscription_response,
                        "model_id": "eleven_monolingual_v1",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75
                        }
                    }
                    
                    timeout = 10
                    tts_response = requests.post(url, json=tts_data, headers=headers, timeout=timeout)
                    
                    if tts_response.status_code == 200 and len(tts_response.content) > 1000:
                        audio_data = base64.b64encode(tts_response.content).decode('utf-8')
                        engine_used = "elevenlabs_rachel"
                        logger.info("✅ Rachel's voice audio generated for subscription")
                    else:
                        logger.warning(f"⚠️ ElevenLabs failed: {tts_response.status_code}")
                    
                except Exception as tts_error:
                    logger.error(f"❌ ElevenLabs Rachel error: {tts_error}")
            
            response_payload = {
                "response": subscription_response,
                "language": user_language,
                "context": "subscription_redirect",
                "action": "show_subscription_popup",  # NEW ACTION
                "engine_used": engine_used,
                "show_text": True
            }
            
            if audio_data:
                response_payload["audio"] = audio_data
                logger.info("✅ Subscription response with Rachel's voice")
            else:
                logger.info("✅ Subscription response with browser TTS fallback")
            
            return jsonify(response_payload)
        
        # Check for booking intent (after subscription check)
        booking_keywords = [
            'book', 'schedule', 'appointment', 'meeting', 'consultation',
            'want to book', 'book an appointment', 'schedule meeting',
            'yes i want to book', 'book appointment', 'schedule appointment'
        ]
        
        booking_detected = any(keyword in user_lower for keyword in booking_keywords)
        
        if booking_detected:
            logger.info("🎯 Booking intent detected in voice!")
            booking_response = "Perfect! Thank you for wanting to book an appointment. I'm opening the appointment form for you right here. Please fill out your details and I'll get you scheduled right away."
            
            # Try to generate premium audio with Rachel's voice
            audio_data = None
            engine_used = "browser_fallback"
            
            if elevenlabs_api_key:
                try:
                    voice_id = "21m00Tcm4TlvDq8ikWAM"
                    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
                    
                    headers = {
                        "Accept": "audio/mpeg",
                        "Content-Type": "application/json",
                        "xi-api-key": elevenlabs_api_key
                    }
                    
                    tts_data = {
                        "text": booking_response,
                        "model_id": "eleven_monolingual_v1",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75
                        }
                    }
                    
                    timeout = 10
                    tts_response = requests.post(url, json=tts_data, headers=headers, timeout=timeout)
                    
                    if tts_response.status_code == 200 and len(tts_response.content) > 1000:
                        audio_data = base64.b64encode(tts_response.content).decode('utf-8')
                        engine_used = "elevenlabs_rachel"
                        logger.info("✅ Rachel's voice audio generated successfully")
                    else:
                        logger.warning(f"⚠️ ElevenLabs failed: {tts_response.status_code}")
                    
                except Exception as tts_error:
                    logger.error(f"❌ ElevenLabs Rachel error: {tts_error}")
            
            response_payload = {
                "response": booking_response,
                "language": user_language,
                "context": "booking_redirect",
                "action": "redirect_to_booking",
                "engine_used": engine_used,
                "show_text": True
            }
            
            if audio_data:
                response_payload["audio"] = audio_data
                logger.info("✅ Booking response with Rachel's voice")
            else:
                logger.info("✅ Booking response with browser TTS fallback")
            
            return jsonify(response_payload)
        
        # Regular FAQ processing for non-booking/non-subscription requests
        faq_response, is_faq = get_faq_response(user_text)
        response_text = faq_response
        context = "professional" if is_faq else "friendly"
        
        # Try to generate premium audio with Rachel's voice
        audio_data = None
        engine_used = "browser_fallback"
        
        if elevenlabs_api_key:
            try:
                voice_id = "21m00Tcm4TlvDq8ikWAM"
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
                
                headers = {
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": elevenlabs_api_key
                }
                
                speech_text = response_text.replace("RinglyPro", "Ringly Pro")
                speech_text = speech_text.replace("AI", "A.I.")
                speech_text = speech_text.replace("$", " dollars")
                
                tts_data = {
                    "text": speech_text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75
                    }
                }
                
                timeout = 10
                tts_response = requests.post(url, json=tts_data, headers=headers, timeout=timeout)
                
                if tts_response.status_code == 200 and len(tts_response.content) > 1000:
                    audio_data = base64.b64encode(tts_response.content).decode('utf-8')
                    engine_used = "elevenlabs_rachel"
                    logger.info(f"✅ Rachel's voice audio generated ({len(tts_response.content)} bytes)")
                else:
                    logger.warning(f"⚠️ ElevenLabs failed: Status {tts_response.status_code}")
                    
            except Exception as tts_error:
                logger.error(f"❌ ElevenLabs Rachel error: {tts_error}")
        
        response_payload = {
            "response": response_text,
            "language": user_language,
            "context": context,
            "is_faq": is_faq,
            "engine_used": engine_used,
            "show_text": True
        }
        
        if audio_data:
            response_payload["audio"] = audio_data
            logger.info("✅ Response with Rachel's voice audio")
        else:
            logger.info("✅ Response with browser TTS fallback")
        
        return jsonify(response_payload)
        
    except Exception as e:
        logger.error(f"❌ Processing error: {e}")
        return jsonify({"error": "I had a technical issue. Please try again."}), 5000

# ==================== TELEPHONY WEBHOOK ROUTES ====================

@app.route('/audio/<filename>')
def serve_audio(filename):
    """Serve audio files for Twilio to play"""
    try:
        audio_path = f'/tmp/{filename}'
        if os.path.exists(audio_path):
            from flask import make_response
            with open(audio_path, 'rb') as f:
                audio_data = f.read()
            
            response = make_response(audio_data)
            response.headers['Content-Type'] = 'audio/mpeg'
            response.headers['Cache-Control'] = 'no-cache'
            return response
        else:
            return "Audio file not found", 404
    except Exception as e:
        logger.error(f"Error serving audio: {e}")
        return "Error serving audio", 500
        
@app.route('/phone/webhook', methods=['POST'])
def phone_webhook():
    """Main entry point for incoming phone calls"""
    try:
        logger.info("📞 Incoming phone call received")
        
        # Get call details from Twilio
        from_number = request.form.get('From', 'Unknown')
        to_number = request.form.get('To', '')
        call_sid = request.form.get('CallSid', '')
        
        logger.info(f"Call from {from_number} to {to_number} (SID: {call_sid})")
        
        # Log the call in database
        try:
            conn = sqlite3.connect('ringlypro.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO inquiries (phone, question, source, notes)
                             VALUES (?, ?, ?, ?)''',
                          (from_number, 'Incoming phone call', 'phone', f'Call SID: {call_sid}'))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log call: {e}")
        
        # Create greeting response
        handler = PhoneCallHandler()
        response = handler.create_greeting_response()
        
        return str(response), 200, {'Content-Type': 'text/xml'}
        
    except Exception as e:
        logger.error(f"Phone webhook error: {e}")
        response = VoiceResponse()
        response.say("We're experiencing technical difficulties. Please call back later or visit ringly pro dot com.")
        return str(response), 200, {'Content-Type': 'text/xml'}

@app.route('/phone/process-speech', methods=['POST'])
def process_phone_speech():
    """Process speech input from phone call"""
    try:
        speech_result = request.form.get('SpeechResult', '')
        confidence = request.form.get('Confidence', '0')
        
        logger.info(f"🎤 Speech detected: '{speech_result}' (confidence: {confidence})")
        
        if not speech_result:
            response = VoiceResponse()
            response.say("I didn't catch that. Please try again.", voice='Polly.Joanna')
            response.redirect('/phone/webhook')
            return str(response), 200, {'Content-Type': 'text/xml'}
        
        handler = PhoneCallHandler()
        response = handler.process_speech_input(speech_result)
        
        return str(response), 200, {'Content-Type': 'text/xml'}
        
    except Exception as e:
        logger.error(f"Speech processing error: {e}")
        response = VoiceResponse()
        response.say("I'm having trouble understanding. Let me transfer you to someone who can help.")
        response.dial('+16566001400')
        return str(response), 200, {'Content-Type': 'text/xml'}

@app.route('/phone/pricing-followup', methods=['POST'])
def pricing_followup():
    """Handle follow-up after pricing information"""
    try:
        speech_result = request.form.get('SpeechResult', '').lower()
        
        response = VoiceResponse()
        
        if 'yes' in speech_result or 'book' in speech_result or 'demo' in speech_result:
            handler = PhoneCallHandler()
            return str(handler.handle_demo_booking()), 200, {'Content-Type': 'text/xml'}
        elif 'repeat' in speech_result or 'again' in speech_result:
            handler = PhoneCallHandler()
            return str(handler.handle_pricing_inquiry()), 200, {'Content-Type': 'text/xml'}
        else:
            response.say("Thank you for calling Ringly Pro. Have a great day!", voice='Polly.Joanna')
            response.hangup()
        
        return str(response), 200, {'Content-Type': 'text/xml'}
        
    except Exception as e:
        logger.error(f"Pricing followup error: {e}")
        response = VoiceResponse()
        response.say("Thank you for your interest. Please visit ringly pro dot com for more information.")
        return str(response), 200, {'Content-Type': 'text/xml'}

@app.route('/phone/collect-name', methods=['POST'])
def collect_name():
    """Collect customer name for booking"""
    try:
        speech_result = request.form.get('SpeechResult', '')
        call_sid = request.form.get('CallSid', '')
        
        if not speech_result:
            response = VoiceResponse()
            response.say("I didn't get your name. Let's try again.", voice='Polly.Joanna')
            response.redirect('/phone/webhook')
            return str(response), 200, {'Content-Type': 'text/xml'}
        
        # Store name in session or temporary storage
        session[f'call_{call_sid}_name'] = speech_result
        
        handler = PhoneCallHandler()
        response = handler.collect_booking_info('name', speech_result)
        
        return str(response), 200, {'Content-Type': 'text/xml'}
        
    except Exception as e:
        logger.error(f"Name collection error: {e}")
        response = VoiceResponse()
        response.say("Let me transfer you to schedule your appointment.")
        response.dial('+16566001400')
        return str(response), 200, {'Content-Type': 'text/xml'}

@app.route('/phone/collect-phone', methods=['POST'])
def collect_phone():
    """Collect customer phone for booking"""
    try:
        # Try speech first, then DTMF
        phone_number = request.form.get('SpeechResult', '')
        if not phone_number:
            phone_number = request.form.get('Digits', '')
        
        call_sid = request.form.get('CallSid', '')
        from_number = request.form.get('From', '')
        
        # Clean up phone number
        phone_digits = re.sub(r'\D', '', phone_number)
        
        if len(phone_digits) < 10:
            # Use caller's number
            phone_digits = re.sub(r'\D', '', from_number)
        
        # Format phone number
        if len(phone_digits) == 10:
            formatted_phone = f"+1{phone_digits}"
        elif len(phone_digits) == 11 and phone_digits[0] == '1':
            formatted_phone = f"+{phone_digits}"
        else:
            formatted_phone = from_number
        
        # Get name from session
        customer_name = session.get(f'call_{call_sid}_name', 'Customer')
        
        # Save to database
        try:
            conn = sqlite3.connect('ringlypro.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO inquiries (phone, question, source, notes)
                             VALUES (?, ?, ?, ?)''',
                          (formatted_phone, f'Demo booking request from {customer_name}', 
                           'phone', f'Call SID: {call_sid}'))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to save booking request: {e}")
        
        handler = PhoneCallHandler()
        response = handler.collect_booking_info('phone', formatted_phone)
        
        return str(response), 200, {'Content-Type': 'text/xml'}
        
    except Exception as e:
        logger.error(f"Phone collection error: {e}")
        response = VoiceResponse()
        response.say("I'll send you information to the number you're calling from.")
        handler = PhoneCallHandler()
        handler.send_booking_sms(request.form.get('From', ''))
        response.say("The information has been sent. Thank you for calling!")
        return str(response), 200, {'Content-Type': 'text/xml'}

@app.route('/phone/call-complete', methods=['POST'])
def call_complete():
    """Handle call completion and logging"""
    try:
        call_sid = request.form.get('CallSid', '')
        dial_status = request.form.get('DialCallStatus', '')
        duration = request.form.get('DialCallDuration', '0')
        
        logger.info(f"📞 Call completed: {call_sid} - Status: {dial_status}, Duration: {duration}s")
        
        response = VoiceResponse()
        
        if dial_status != 'completed':
            response.say(
                "We couldn't connect your call. Please try again later or visit ringly pro dot com.",
                voice='Polly.Joanna'
            )
        else:
            response.say("Thank you for calling Ringly Pro. Have a great day!", voice='Polly.Joanna')
        
        response.hangup()
        return str(response), 200, {'Content-Type': 'text/xml'}
        
    except Exception as e:
        logger.error(f"Call completion error: {e}")
        response = VoiceResponse()
        response.hangup()
        return str(response), 200, {'Content-Type': 'text/xml'}

@app.route('/phone/voicemail', methods=['POST'])
def handle_voicemail():
    """Handle voicemail recording"""
    try:
        response = VoiceResponse()
        
        response.say(
            "Please leave your message after the beep. Press star when you're finished.",
            voice='Polly.Joanna'
        )
        
        response.record(
            action='/phone/voicemail-complete',
            method='POST',
            maxLength=120,
            finishOnKey='*',
            transcribe=True,
            transcribeCallback='/phone/transcription-ready'
        )
        
        response.say("I didn't receive a recording. Goodbye.", voice='Polly.Joanna')
        response.hangup()
        
        return str(response), 200, {'Content-Type': 'text/xml'}
        
    except Exception as e:
        logger.error(f"Voicemail error: {e}")
        response = VoiceResponse()
        response.say("Unable to record message. Please call back.")
        response.hangup()
        return str(response), 200, {'Content-Type': 'text/xml'}

@app.route('/phone/test-call', methods=['GET'])
def test_call():
    """Test endpoint to initiate an outbound call"""
    try:
        if not all([twilio_account_sid, twilio_auth_token, twilio_phone]):
            return jsonify({'error': 'Twilio not configured'}), 500
        
        client = Client(twilio_account_sid, twilio_auth_token)
        
        # Use the actual URL directly
        webhook_url = os.getenv("WEBHOOK_BASE_URL", "https://voice-bot-r91r.onrender.com")
        
        call = client.calls.create(
            url=f'{webhook_url}/phone/webhook',
            to='+16566001400',  # Test number
            from_='+18886103810'  # Use the actual number
        )
        
        return jsonify({
            'success': True,
            'call_sid': call.sid,
            'status': 'Call initiated'
        })
        
    except Exception as e:
        logger.error(f"Test call error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/admin')
def admin_dashboard():
    """Enhanced admin dashboard with appointments and inquiries"""
    try:
        conn = sqlite3.connect('ringlypro.db')
        cursor = conn.cursor()
        
        # Get inquiries
        cursor.execute('''SELECT phone, question, timestamp, status, sms_sent, source 
                          FROM inquiries ORDER BY timestamp DESC LIMIT 50''')
        inquiries = cursor.fetchall()
        
        # Get appointments
        cursor.execute('''SELECT customer_name, customer_email, customer_phone, appointment_date, 
                          appointment_time, purpose, status, confirmation_code, created_at,
                          hubspot_contact_id, hubspot_meeting_id
                          FROM appointments ORDER BY appointment_date DESC, appointment_time DESC LIMIT 50''')
        appointments = cursor.fetchall()
        
        conn.close()
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>RinglyPro Admin Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }}
        h1 {{ color: #2196F3; text-align: center; margin-bottom: 30px; }}
        .stats {{ display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap; }}
        .stat-card {{ background: linear-gradient(135deg, #2196F3, #1976D2); color: white; padding: 20px; border-radius: 10px; text-align: center; flex: 1; min-width: 200px; }}
        .stat-card h3 {{ font-size: 2.5em; margin: 0; }}
        .stat-card p {{ margin: 10px 0 0 0; opacity: 0.9; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background: white; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; font-weight: bold; color: #333; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 RinglyPro Admin Dashboard</h1>
        
        <div class="stats">
            <div class="stat-card">
                <h3>{len(inquiries)}</h3>
                <p>Recent Inquiries</p>
            </div>
            <div class="stat-card">
                <h3>{len(appointments)}</h3>
                <p>Total Appointments</p>
            </div>
        </div>
        
        <h2>Recent Appointments</h2>
        <table>
            <thead>
                <tr>
                    <th>Customer</th>
                    <th>Contact Info</th>
                    <th>Date & Time</th>
                    <th>Purpose</th>
                    <th>Status</th>
                    <th>Confirmation</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for apt in appointments[:10]:  # Show first 10
            name, email, phone, date, time, purpose, status, code, created, hubspot_contact_id, hubspot_meeting_id = apt
            html += f"""
                <tr>
                    <td>{name}</td>
                    <td>{email}<br>{phone}</td>
                    <td>{date} {time}</td>
                    <td>{purpose[:50]}</td>
                    <td>{status}</td>
                    <td>{code}</td>
                </tr>
            """
        
        html += """
            </tbody>
        </table>
        
        <h2>Recent Inquiries</h2>
        <table>
            <thead>
                <tr>
                    <th>Phone</th>
                    <th>Question</th>
                    <th>Timestamp</th>
                    <th>Source</th>
                    <th>SMS Sent</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for inquiry in inquiries[:10]:  # Show first 10
            phone, question, timestamp, status, sms_sent, source = inquiry
            html += f"""
                <tr>
                    <td>{phone}</td>
                    <td>{question[:100]}</td>
                    <td>{timestamp}</td>
                    <td>{source}</td>
                    <td>{'✅' if sms_sent else '❌'}</td>
                </tr>
            """
        
        html += """
            </tbody>
        </table>
    </div>
</body>
</html>
        """
        
        return html
        
    except Exception as e:
        logger.error(f"❌ Admin dashboard error: {e}")
        return f"<h1>Admin Dashboard Error</h1><p>{e}</p>"

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        conn = sqlite3.connect('ringlypro.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM inquiries')
        inquiry_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM appointments')
        appointment_count = cursor.fetchone()[0]
        conn.close()
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "3.0.0",
            "database": {
                "inquiries": inquiry_count,
                "appointments": appointment_count
            },
            "services": {
                "anthropic": bool(anthropic_api_key),
                "elevenlabs": bool(elevenlabs_api_key),
                "twilio": bool(twilio_account_sid and twilio_auth_token),
                "email": bool(email_user and email_password),
                "hubspot": bool(hubspot_api_token)
            }
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==================== IFRAME EMBEDDING SUPPORT ====================

@app.after_request
def allow_iframe_embedding(response):
    """Allow iframe embedding for widget"""
    response.headers['X-Frame-Options'] = 'ALLOWALL'
    response.headers['Content-Security-Policy'] = "frame-ancestors *"
    return response

# ==================== DATABASE INITIALIZATION ====================

# Setup database on startup
init_database()

# ==================== MAIN APPLICATION STARTUP ====================

if __name__ == "__main__":
    print("🚀 Starting RinglyPro AI Assistant v3.0")
    print("\n" + "="*60)
    print("📋 API STATUS:")
    print(f"   • Claude API: {'✅ Ready' if anthropic_api_key else '❌ Missing'}")
    print(f"   • ElevenLabs TTS: {'✅ Ready' if elevenlabs_api_key else '⚠️ Browser Fallback'}")
    print(f"   • Twilio SMS: {'✅ Ready' if (twilio_account_sid and twilio_auth_token) else '⚠️ Disabled'}")
    print(f"   • Email SMTP: {'✅ Ready' if (email_user and email_password) else '⚠️ Disabled'}")
    print(f"   • HubSpot CRM: {'✅ Ready' if hubspot_api_token else '⚠️ Disabled'}")
    print("\n🌐 ACCESS URLS:")
    print("   • Voice Interface: http://localhost:5000")
    print("   • Text Chat: http://localhost:5000/chat")
    print("   • Enhanced Chat: http://localhost:5000/chat-enhanced")
    print("   • Admin Dashboard: http://localhost:5000/admin")
    print("   • Health Check: http://localhost:5000/health")
    print("\n" + "="*60)
    
    # Start the application
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
