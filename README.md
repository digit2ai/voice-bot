RinglyPro AI Voice Assistant
A comprehensive AI-powered business assistant that provides 24/7 call answering, appointment scheduling, and customer engagement through voice and text interfaces.
Overview
RinglyPro AI Assistant is a Flask-based web application that leverages advanced AI technologies to provide intelligent business communication solutions. The system integrates voice recognition, natural language processing, text-to-speech synthesis, and CRM functionalities to deliver a seamless customer experience.
Features
Core Functionality

24/7 AI Call Answering - Intelligent phone call handling with natural conversation flow
Voice Interface - Browser-based voice chat with premium TTS
Text Chat - Real-time text-based customer support
Appointment Booking - Integrated scheduling system with calendar management
Bilingual Support - English and Spanish language capabilities

Integrations

Anthropic Claude - Advanced natural language processing
ElevenLabs - Premium text-to-speech synthesis with custom voices
Twilio - Phone calls, SMS, and voice webhooks
HubSpot CRM - Customer relationship management
PostgreSQL - Database backend via CRM API
Email SMTP - Automated email confirmations

User Interfaces

Voice Chat - Mobile-optimized voice interaction
Text Chat - Traditional chat interface
Enhanced Chat - Booking-enabled chat with inline forms
Phone System - Twilio webhook integration for call handling

Installation
Prerequisites

Python 3.8+
PostgreSQL database (via CRM API)
Required API keys (see Configuration section)

Setup

Clone the repository:

bashgit clone <repository-url>
cd ringlypro-ai-assistant

Install dependencies:

bashpip install -r requirements.txt

Create environment file:

bashcp .env.example .env

Configure environment variables (see Configuration section)
Run the application:

bashpython app.py
Configuration
Required Environment Variables
Create a .env file with the following configurations:
Core API Keys
env# Anthropic Claude API
ANTHROPIC_API_KEY=your_anthropic_api_key

# ElevenLabs Text-to-Speech (Optional - falls back to browser TTS)
ELEVENLABS_API_KEY=your_elevenlabs_api_key

# Twilio (for phone/SMS functionality)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# Email Configuration
EMAIL_USER=your_email@domain.com
EMAIL_PASSWORD=your_email_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
FROM_EMAIL=your_from_email@domain.com
CRM and Database
env# PostgreSQL via CRM API
CRM_BASE_URL=https://your-crm-api.com/api
CLIENT_ID=your_client_id
CLIENT_NAME=YourBusinessName

# HubSpot Integration (Optional)
HUBSPOT_ACCESS_TOKEN=your_hubspot_token
HUBSPOT_PORTAL_ID=your_portal_id
HUBSPOT_OWNER_ID=your_owner_id
Application Settings
env# Flask Configuration
SECRET_KEY=your_secret_key_here
WEBHOOK_BASE_URL=https://your-domain.com

# Zoom Meeting Configuration
ZOOM_MEETING_URL=https://zoom.us/j/your_meeting_id
ZOOM_MEETING_ID=123456789
ZOOM_PASSWORD=your_meeting_password
API Integrations
Anthropic Claude

Purpose: Natural language processing and conversation generation
Setup: Obtain API key from Anthropic Console
Model: claude-sonnet-4-20250514

ElevenLabs

Purpose: Premium text-to-speech synthesis
Setup: Create account at ElevenLabs and get API key
Voice ID: 21m00Tcm4TlvDq8ikWAM (Rachel voice)
Fallback: Browser speechSynthesis API

Twilio

Purpose: Phone calls, SMS notifications, and voice webhooks
Setup: Create Twilio account and configure phone number
Webhooks: Configure /phone/webhook as voice webhook URL

HubSpot CRM

Purpose: Contact management and meeting scheduling
Setup: Create private app in HubSpot and generate access token
Permissions: contacts, engagements, timeline events

Usage
Accessing the Application
Voice Interface

URL: http://localhost:5000/
Features: Voice chat with premium TTS, inline booking
Mobile: Optimized for mobile devices with touch controls

Text Chat

URL: http://localhost:5000/chat
Features: Traditional text-based chat interface
Use Case: Users who prefer typing over voice

Enhanced Chat

URL: http://localhost:5000/chat-enhanced
Features: Chat with integrated appointment booking forms
Best For: Lead generation and appointment scheduling

Phone Integration

Setup: Configure Twilio webhook to point to your domain
Webhook URL: https://yourdomain.com/phone/webhook
Features: Intelligent call routing, booking, transfers

Admin Interfaces
Health Check

URL: /health
Purpose: Monitor system status and API connectivity

Appointment Management

URL: /admin/appointments
Purpose: View all scheduled appointments from PostgreSQL

System Testing

URL: /test-appointment-system
Purpose: Test all integrations and configurations

Deployment
Environment Setup

Set RENDER=true for Render.com deployment
Configure all environment variables in deployment platform
Ensure webhook URLs point to production domain

Database

Application uses PostgreSQL via CRM API
No direct database setup required in application
Ensure CRM API endpoint is accessible

SSL/HTTPS

Required for microphone access in voice interface
Required for Twilio webhook security
Configure SSL certificate for production domain

File Structure
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── speech_optimized_claude.py      # Enhanced Claude integration
├── voice_customization_guide.py    # Voice configuration options
├── index.html                      # Static voice interface
└── README.md                       # This file
Key Components
PhoneCallHandler
Manages Twilio voice webhooks and call routing:

Greeting generation with premium TTS
Speech processing and intent detection
Call transfers and booking flows

AppointmentManager
Handles appointment scheduling via PostgreSQL:

Slot availability checking
Booking creation and confirmation
Email and SMS notifications

CRMAPIClient
Interface for PostgreSQL database operations:

Customer data management
Appointment storage
Call logging and analytics

Enhanced Voice Interface
Browser-based voice chat with:

Speech recognition
Premium audio playback
Mobile optimization
Subscription and booking flows

Troubleshooting
Common Issues
Voice Not Working

Check microphone permissions in browser
Verify HTTPS is enabled
Test with different browsers (Chrome/Edge recommended)

Audio Not Playing

Check ElevenLabs API key and credits
Verify audio format compatibility
Test fallback to browser TTS

Appointments Not Saving

Check CRM API connectivity at /health
Verify PostgreSQL database is accessible
Test with /test-appointment-system

Phone Calls Not Working

Verify Twilio webhook URL configuration
Check Twilio account balance and phone number
Test webhook endpoint accessibility

Debug Endpoints

/health - System health and API status
/test-appointment-system - Comprehensive system test
/admin/appointments - View appointment data
Check application logs for detailed error information

Support
For technical support or questions:

Review application logs for error details
Test individual components using debug endpoints
Verify all API keys and environment variables
Check integration service status pages

License
This project is proprietary software for RinglyPro business communications.
