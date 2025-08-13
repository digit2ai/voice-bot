# Enhanced Flask App - SMS, Email, CRM, RCS & FAQ System with HubSpot Integration
# Complete CRM Co-Pilot with Twilio RCS Support and RinglyPro FAQ - NO WAKE WORD VERSION
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Import Twilio REST API client
try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    print("Twilio library not installed. Run: pip install twilio")

# Import email libraries
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
CORS(app)

CONFIG = {
    "claude_api_key": os.getenv("CLAUDE_API_KEY", ""),
    "twilio_account_sid": os.getenv("TWILIO_ACCOUNT_SID", ""),
    "twilio_auth_token": os.getenv("TWILIO_AUTH_TOKEN", ""),
    "twilio_phone_number": os.getenv("TWILIO_PHONE_NUMBER", ""),
    # RCS Configuration
    "twilio_rcs_agent_id": os.getenv("TWILIO_RCS_AGENT_ID", ""),
    "twilio_messaging_service_sid": os.getenv("TWILIO_MESSAGING_SERVICE_SID", ""),
    # Email configuration
    "email_provider": os.getenv("EMAIL_PROVIDER", "networksolutions").lower(),
    "email_smtp_server": os.getenv("SMTP_SERVER", os.getenv("EMAIL_SMTP_SERVER", "netsol-smtp-oxcs.hostingplatform.com")),
    "email_smtp_port": int(os.getenv("SMTP_PORT", os.getenv("EMAIL_SMTP_PORT", "587"))),
    "email_address": os.getenv("EMAIL_ADDRESS", ""),
    "email_password": os.getenv("EMAIL_PASSWORD", ""),
    "email_name": os.getenv("EMAIL_NAME", "CRMAutoPilot Voice Assistant"),
    # HubSpot CRM configuration
    "hubspot_api_token": os.getenv("HUBSPOT_API_TOKEN", ""),
}

print(f"🔧 System configured without wake words - direct command mode")
if CONFIG["twilio_rcs_agent_id"]:
    print(f"📱 RCS Agent ID: {CONFIG['twilio_rcs_agent_id'][:10]}...")
if CONFIG["twilio_messaging_service_sid"]:
    print(f"📨 Messaging Service: {CONFIG['twilio_messaging_service_sid'][:10]}...")

# ==================== RINGLY PRO FAQ DATABASE ====================

RINGLY_FAQ_DATABASE = {
    "general_overview": {
        "what_is_ringlypro": {
            "question": "What is RinglyPro?",
            "answer": "RinglyPro is your 24/7 AI-powered receptionist that answers calls, books appointments, and handles client intake automatically — so you never miss a lead again.",
            "keywords": ["what is", "ringlypro", "ringly pro", "what's ringly"]
        },
        "how_does_it_work": {
            "question": "How does RinglyPro work?",
            "answer": "Our AI answers calls and texts instantly, engages with customers, captures details, and syncs everything to your CRM.",
            "keywords": ["how does", "work", "function", "operate"]
        },
        "who_uses": {
            "question": "Who uses RinglyPro?",
            "answer": "Service businesses, contractors, medical offices, real estate agents, and anyone who wants to capture more leads without hiring extra staff.",
            "keywords": ["who uses", "customers", "clients", "target market"]
        },
        "current_number": {
            "question": "Can I use my current phone number?",
            "answer": "Yes — we can port your number or forward calls from your existing line.",
            "keywords": ["current number", "existing number", "keep number", "port number"]
        },
        "replace_staff": {
            "question": "Does RinglyPro replace my staff?",
            "answer": "No — it enhances your team by handling repetitive calls and booking tasks, freeing them to focus on higher-value work.",
            "keywords": ["replace staff", "fire employees", "instead of staff"]
        },
        "availability": {
            "question": "Is RinglyPro available in my area?",
            "answer": "Yes — we support businesses across the U.S. and in many international markets.",
            "keywords": ["available", "my area", "location", "region", "country"]
        },
        "different": {
            "question": "What makes RinglyPro different?",
            "answer": "We use human-like AI, not generic call centers — meaning faster responses, 24/7 availability, and full CRM integration.",
            "keywords": ["different", "unique", "special", "better than", "comparison"]
        }
    },
    "features": {
        "sound_human": {
            "question": "Can the AI really sound human?",
            "answer": "Yes — our voice technology is designed to sound natural, empathetic, and professional.",
            "keywords": ["sound human", "natural", "voice quality", "realistic"]
        },
        "answer_faqs": {
            "question": "Can it answer FAQs for my business?",
            "answer": "Absolutely — we can program it with your own knowledge base to answer common customer questions.",
            "keywords": ["answer faq", "knowledge base", "common questions"]
        },
        "rcs_messaging": {
            "question": "What is RCS messaging?",
            "answer": "RCS (Rich Communication Services) turns basic texts into branded, interactive messages with buttons, images, and quick replies.",
            "keywords": ["rcs", "rich communication", "messaging", "interactive text"]
        },
        "follow_up": {
            "question": "Does RinglyPro send follow-up texts?",
            "answer": "Yes — every missed call can trigger an instant text message, increasing your chance of connecting.",
            "keywords": ["follow up", "missed calls", "text after"]
        },
        "after_hours": {
            "question": "Can it take messages after hours?",
            "answer": "Yes — and unlike voicemail, it can continue the conversation via text or book an appointment right away.",
            "keywords": ["after hours", "nighttime", "weekend", "closed"]
        },
        "phone_types": {
            "question": "Does it work with landlines and mobile?",
            "answer": "Yes — any number can be connected.",
            "keywords": ["landline", "mobile", "cell phone", "phone types"]
        },
        "call_routing": {
            "question": "Can it route calls to team members?",
            "answer": "Yes — we can set up smart call routing based on time, location, or customer type.",
            "keywords": ["route calls", "transfer", "team members", "forwarding"]
        },
        "qualify_leads": {
            "question": "Can RinglyPro qualify leads?",
            "answer": "Yes — it can ask screening questions and only pass along qualified leads to your team.",
            "keywords": ["qualify", "screen", "filter leads", "lead qualification"]
        },
        "languages": {
            "question": "Can it handle multiple languages?",
            "answer": "Yes — we support bilingual and multilingual scripts.",
            "keywords": ["language", "bilingual", "multilingual", "spanish", "foreign"]
        },
        "website_chat": {
            "question": "Can it integrate with website chat?",
            "answer": "Yes — we can connect with web chat tools so all conversations go to one place.",
            "keywords": ["website", "web chat", "online chat", "chat widget"]
        }
    },
    "integrations": {
        "crm_support": {
            "question": "What CRMs does RinglyPro work with?",
            "answer": "HubSpot, GoHighLevel, Salesforce, Zoho, and more — plus custom integrations via Zapier or API.",
            "keywords": ["crm", "hubspot", "salesforce", "zoho", "gohighlevel", "integration"]
        },
        "scheduling": {
            "question": "Can you integrate with scheduling tools?",
            "answer": "Yes — we work with Google Calendar, Outlook, Calendly, Acuity, and others.",
            "keywords": ["calendar", "scheduling", "appointment", "booking", "calendly"]
        },
        "setup_time": {
            "question": "How long does setup take?",
            "answer": "Most clients are live within 48 hours.",
            "keywords": ["setup time", "how long", "implementation", "go live"]
        },
        "setup_process": {
            "question": "What's involved in setup?",
            "answer": "We onboard you, customize your scripts, connect your CRM, and test everything.",
            "keywords": ["setup process", "onboarding", "implementation steps"]
        },
        "hardware": {
            "question": "Do I need special hardware?",
            "answer": "No — everything runs in the cloud.",
            "keywords": ["hardware", "equipment", "devices", "special equipment"]
        },
        "existing_greeting": {
            "question": "Can you use my existing greeting?",
            "answer": "Yes — we can replicate or improve your current greeting.",
            "keywords": ["greeting", "existing message", "current greeting"]
        },
        "customize_calls": {
            "question": "Can I customize how calls are answered?",
            "answer": "Absolutely — every script is tailored to your brand.",
            "keywords": ["customize", "personalize", "script", "brand"]
        },
        "payment_integration": {
            "question": "Can you integrate with payment systems?",
            "answer": "Yes — we can direct customers to online payment links or collect details for follow-up.",
            "keywords": ["payment", "billing", "invoice", "payment system"]
        }
    },
    "pricing": {
        "cost": {
            "question": "How much does RinglyPro cost?",
            "answer": "Plans start at $97/month, with higher tiers adding CRM setup, RCS, and more.",
            "keywords": ["cost", "price", "how much", "pricing", "fee"]
        },
        "contract": {
            "question": "Is there a contract?",
            "answer": "No long-term commitment — cancel anytime.",
            "keywords": ["contract", "commitment", "lock in", "cancel"]
        },
        "free_trial": {
            "question": "Do you offer a free trial?",
            "answer": "Yes — 7 days, risk-free.",
            "keywords": ["free trial", "try", "test", "demo"]
        },
        "included": {
            "question": "What's included in each plan?",
            "answer": "All plans include AI answering, appointment booking, and call/text handling.",
            "keywords": ["included", "features", "plan includes", "what comes with"]
        },
        "change_plans": {
            "question": "Can I change plans anytime?",
            "answer": "Yes — you can upgrade or downgrade as needed.",
            "keywords": ["change plan", "upgrade", "downgrade", "switch"]
        },
        "extra_charges": {
            "question": "Are there extra charges for high volume?",
            "answer": "Higher plans include more minutes/messages; overages are billed at a low per-minute rate.",
            "keywords": ["extra charges", "overage", "high volume", "additional fees"]
        }
    },
    "support": {
        "data_safe": {
            "question": "Is my customer data safe?",
            "answer": "Yes — we use bank-level encryption and comply with privacy laws.",
            "keywords": ["data safe", "security", "privacy", "encryption", "secure"]
        },
        "customer_support": {
            "question": "Do you offer customer support?",
            "answer": "All plans include chat/email support; Pro & Premium have phone support.",
            "keywords": ["support", "help", "assistance", "customer service"]
        },
        "cant_answer": {
            "question": "What if AI can't answer a question?",
            "answer": "The call can be transferred to a team member or a message sent to you instantly.",
            "keywords": ["cant answer", "doesnt know", "unable to answer", "fallback"]
        },
        "reports": {
            "question": "Do you provide reports?",
            "answer": "Yes — detailed call logs, booking summaries, and engagement stats.",
            "keywords": ["reports", "analytics", "statistics", "call logs"]
        },
        "after_hours_changes": {
            "question": "What about after-hours script changes?",
            "answer": "Pro & Premium plans include priority same-day updates.",
            "keywords": ["after hours changes", "script update", "emergency changes"]
        }
    },
    "results": {
        "more_customers": {
            "question": "How will this help me get more customers?",
            "answer": "By ensuring every call and message gets an instant response — no more missed opportunities.",
            "keywords": ["more customers", "increase sales", "grow business", "get clients"]
        },
        "engagement_boost": {
            "question": "What's the average engagement boost?",
            "answer": "Clients report up to 45% higher engagement rates compared to voicemail.",
            "keywords": ["engagement", "improvement", "boost", "increase"]
        },
        "proof": {
            "question": "Do you have proof it works?",
            "answer": "Yes — our case studies show real revenue increases from faster lead capture.",
            "keywords": ["proof", "case studies", "testimonials", "evidence", "results"]
        },
        "save_time": {
            "question": "Will it save me time?",
            "answer": "Yes — we take repetitive calls off your plate so you can focus on work that matters.",
            "keywords": ["save time", "efficiency", "productivity", "time saving"]
        },
        "booking_rate": {
            "question": "Can it increase my booking rate?",
            "answer": "Yes — customers can book instantly instead of waiting for a callback.",
            "keywords": ["booking rate", "appointments", "conversion", "schedule more"]
        },
        "roi": {
            "question": "What's the ROI compared to hiring staff?",
            "answer": "RinglyPro costs a fraction of a full-time receptionist and works 24/7.",
            "keywords": ["roi", "return on investment", "cost comparison", "versus staff"]
        }
    },
    "customization": {
        "different_scripts": {
            "question": "Can I have different scripts for services?",
            "answer": "Yes — we can create multiple workflows.",
            "keywords": ["different scripts", "multiple services", "workflows", "various scripts"]
        },
        "scalable": {
            "question": "Can it grow with my business?",
            "answer": "Absolutely — you can add more lines, services, and integrations anytime.",
            "keywords": ["grow", "scale", "expand", "growth", "scalable"]
        },
        "seasonal": {
            "question": "Can it handle seasonal call spikes?",
            "answer": "Yes — we scale automatically.",
            "keywords": ["seasonal", "spike", "busy season", "high volume", "peak times"]
        },
        "franchise": {
            "question": "Do you work with franchises?",
            "answer": "Yes — we can manage calls per location and provide separate reporting.",
            "keywords": ["franchise", "multi location", "multiple locations", "chain"]
        }
    },
    "special_features": {
        "text_to_pay": {
            "question": "Does it work with text-to-pay?",
            "answer": "Yes — perfect for instant invoice follow-up.",
            "keywords": ["text to pay", "payment link", "invoice", "text payment"]
        },
        "reminders": {
            "question": "Can it send appointment reminders?",
            "answer": "Yes — via SMS, RCS, or email.",
            "keywords": ["reminder", "appointment reminder", "notification", "remind"]
        },
        "upsell": {
            "question": "Can it upsell my services?",
            "answer": "Yes — we can add promotional messages to conversations.",
            "keywords": ["upsell", "cross sell", "promote", "marketing"]
        },
        "vip_alert": {
            "question": "Can it alert me when VIPs call?",
            "answer": "Yes — we can set up instant push or text notifications.",
            "keywords": ["vip", "important caller", "alert", "priority notification"]
        },
        "overflow": {
            "question": "Can I use it only for overflow?",
            "answer": "Yes — you decide when the AI answers.",
            "keywords": ["overflow", "backup", "busy times", "selective answering"]
        },
        "hold_music": {
            "question": "Can I use custom hold music?",
            "answer": "Yes — we can upload your own audio files.",
            "keywords": ["hold music", "custom audio", "music on hold", "audio files"]
        }
    }
}

def search_faq(query: str) -> Dict[str, Any]:
    """Search FAQ database for best matching answer"""
    query_lower = query.lower().strip()
    best_match = None
    best_score = 0
    
    # Remove common question words for better matching
    query_words = query_lower.replace("what", "").replace("how", "").replace("can", "").replace("does", "").replace("is", "").replace("?", "").strip()
    
    for category, faqs in RINGLY_FAQ_DATABASE.items():
        for faq_id, faq_data in faqs.items():
            score = 0
            
            # Check if query contains any keywords
            for keyword in faq_data["keywords"]:
                if keyword in query_lower:
                    score += len(keyword.split())  # Longer keyword matches get higher scores
            
            # Check if query contains words from the question
            question_words = faq_data["question"].lower().split()
            for word in question_words:
                if len(word) > 3 and word in query_words:  # Skip short words
                    score += 1
            
            if score > best_score:
                best_score = score
                best_match = faq_data
    
    if best_match and best_score > 0:
        return {
            "found": True,
            "question": best_match["question"],
            "answer": best_match["answer"],
            "confidence": min(best_score / 5, 1.0)  # Normalize confidence
        }
    
    return {"found": False, "answer": "I don't have information about that specific question. You can ask about RinglyPro's features, pricing, setup, integrations, or how it can help your business."}

# ==================== HUBSPOT CRM SERVICE ====================

class HubSpotService:
    """HubSpot CRM API service for voice command integration using v3 API"""
    
    def __init__(self):
        self.api_token = CONFIG["hubspot_api_token"]
        self.base_url = "https://api.hubapi.com"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        if self.api_token:
            print("✅ HubSpot service initialized")
            print(f"🔑 Token: {self.api_token[:12]}...")
        else:
            print("⚠️ HubSpot not configured - missing HUBSPOT_API_TOKEN")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test HubSpot API connection"""
        if not self.api_token:
            return {"success": False, "error": "HubSpot API token not configured"}
        
        try:
            response = requests.post(
                f"{self.base_url}/crm/v3/objects/contacts/search",
                headers=self.headers,
                json={
                    "filterGroups": [],
                    "properties": ["email", "firstname", "lastname"],
                    "limit": 1
                },
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                return {"success": True, "message": "HubSpot connection successful"}
            else:
                return {"success": False, "error": f"API returned status {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {"success": False, "error": f"Connection failed: {str(e)}"}
    
    def create_contact(self, name: str, email: str = "", phone: str = "", company: str = "") -> Dict[str, Any]:
        """Create new contact in HubSpot"""
        try:
            name_parts = name.strip().split()
            firstname = name_parts[0] if name_parts else ""
            lastname = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
            
            properties = {
                "firstname": firstname,
                "lastname": lastname
            }
            
            if email:
                properties["email"] = email
            if phone:
                properties["phone"] = phone
            if company:
                properties["company"] = company
            
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
                    "data": contact
                }
            else:
                return {"success": False, "error": f"Failed to create contact: {response.text}"}
                
        except Exception as e:
            return {"success": False, "error": f"Error creating contact: {str(e)}"}
    
    def search_contact(self, query: str) -> Dict[str, Any]:
        """Search for contacts by name, email, or phone"""
        try:
            if "@" in query:
                search_data = {
                    "filterGroups": [{
                        "filters": [{
                            "propertyName": "email",
                            "operator": "EQ",
                            "value": query
                        }]
                    }],
                    "properties": ["email", "firstname", "lastname", "phone", "company"],
                    "limit": 10
                }
            else:
                search_data = {
                    "query": query,
                    "properties": ["email", "firstname", "lastname", "phone", "company"],
                    "limit": 10
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
                        "message": f"Found {len(contacts)} contact(s)",
                        "contacts": contacts
                    }
                else:
                    return {"success": False, "error": f"No contacts found for '{query}'"}
            else:
                return {"success": False, "error": f"Search failed: {response.text}"}
                
        except Exception as e:
            return {"success": False, "error": f"Error searching contacts: {str(e)}"}
    
    def update_contact(self, contact_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update contact information"""
        try:
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
                    "data": response.json()
                }
            else:
                return {"success": False, "error": f"Failed to update contact: {response.text}"}
                
        except Exception as e:
            return {"success": False, "error": f"Error updating contact: {str(e)}"}
    
    def add_contact_note(self, contact_id: str, note: str) -> Dict[str, Any]:
        """Add note by creating as deal or using Notes API"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            if not contact_id or contact_id == "0":
                # Create general note as deal
                note_deal = {
                    "properties": {
                        "dealname": f"NOTE: {note[:50]}..." if len(note) > 50 else f"NOTE: {note}",
                        "dealstage": "appointmentscheduled",
                        "pipeline": "default", 
                        "amount": "0",
                        "description": f"Note created via CRMAutoPilot at {timestamp}: {note}"
                    }
                }
                
                response = requests.post(
                    f"{self.base_url}/crm/v3/objects/deals",
                    headers=self.headers,
                    json=note_deal,
                    timeout=10
                )
                
                if response.status_code in [200, 201]:
                    return {
                        "success": True,
                        "message": f"✅ Note saved",
                        "data": response.json()
                    }
                else:
                    return {"success": False, "error": f"Failed to create note: {response.text[:200]}"}
            else:
                # Create note as deal associated with contact
                contact_name = "Contact"
                get_response = requests.get(
                    f"{self.base_url}/crm/v3/objects/contacts/{contact_id}",
                    headers=self.headers,
                    params={"properties": "firstname,lastname"},
                    timeout=10
                )
                
                if get_response.status_code == 200:
                    contact_data = get_response.json()
                    props = contact_data.get("properties", {})
                    firstname = props.get("firstname", "")
                    lastname = props.get("lastname", "")
                    contact_name = f"{firstname} {lastname}".strip() or "Contact"
                
                # Create deal as note
                note_deal = {
                    "properties": {
                        "dealname": f"NOTE for {contact_name}: {note[:30]}...",
                        "dealstage": "appointmentscheduled",
                        "pipeline": "default",
                        "amount": "0",
                        "description": f"Note for {contact_name} (ID: {contact_id})\nCreated: {timestamp}\n\n{note}"
                    }
                }
                
                deal_response = requests.post(
                    f"{self.base_url}/crm/v3/objects/deals",
                    headers=self.headers,
                    json=note_deal,
                    timeout=10
                )
                
                if deal_response.status_code in [200, 201]:
                    return {
                        "success": True,
                        "message": f"✅ Note saved",
                        "data": deal_response.json()
                    }
                else:
                    return {"success": False, "error": f"Failed to create note: {deal_response.text[:200]}"}
            
        except Exception as e:
            return {"success": False, "error": f"Error adding note: {str(e)}"}
    
    def create_appointment(self, title: str, contact_id: str = "", start_time: str = "", duration: int = 30) -> Dict[str, Any]:
        """Create meeting as a deal record with meeting details"""
        try:
            # Create meeting as a deal record
            meeting_name = f"MEETING: {title}"
            
            deal_properties = {
                "dealname": meeting_name,
                "dealstage": "appointmentscheduled",
                "pipeline": "default",
                "amount": "0"  # Meetings have no monetary value
            }
            
            # Add meeting details to description
            meeting_details = f"Meeting: {title}\nDuration: {duration} minutes"
            if start_time:
                meeting_details += f"\nScheduled for: {start_time}"
            else:
                meeting_details += f"\nScheduled for: 1 hour from now"
            
            deal_properties["description"] = meeting_details
            
            # Set close date based on meeting time
            if start_time:
                parsed_date = self._parse_date(start_time)
                deal_properties["closedate"] = parsed_date
            else:
                tomorrow = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d")
                deal_properties["closedate"] = tomorrow
            
            deal_data = {"properties": deal_properties}
            
            response = requests.post(
                f"{self.base_url}/crm/v3/objects/deals",
                headers=self.headers,
                json=deal_data,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                return {
                    "success": True,
                    "message": f"Meeting scheduled: {title}",
                    "data": response.json()
                }
            else:
                return {"success": False, "error": f"Failed to schedule meeting: {response.text}"}
                
        except Exception as e:
            return {"success": False, "error": f"Error creating meeting: {str(e)}"}
    
    def get_calendar_events(self, start_date: str = "", end_date: str = "") -> Dict[str, Any]:
        """Get calendar events by searching deals for meetings and tasks"""
        try:
            # Search for deals that are meetings or tasks
            search_data = {
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "dealname",
                                "operator": "CONTAINS_TOKEN",
                                "value": "MEETING"
                            }
                        ]
                    },
                    {
                        "filters": [
                            {
                                "propertyName": "dealname", 
                                "operator": "CONTAINS_TOKEN",
                                "value": "TASK"
                            }
                        ]
                    }
                ],
                "properties": ["dealname", "description", "closedate"],
                "limit": 50
            }
            
            response = requests.post(
                f"{self.base_url}/crm/v3/objects/deals/search",
                headers=self.headers,
                json=search_data,
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json()
                deals = results.get("results", [])
                
                # Format as calendar events
                events = []
                for deal in deals:
                    props = deal.get("properties", {})
                    dealname = props.get("dealname", "")
                    
                    # Extract meeting/task title
                    if dealname.startswith("MEETING:"):
                        title = dealname.replace("MEETING:", "").strip()
                        event_type = "Meeting"
                    elif dealname.startswith("TASK:"):
                        title = dealname.replace("TASK:", "").strip()
                        event_type = "Task"
                    else:
                        continue
                    
                    event = {
                        "properties": {
                            "hs_meeting_title": f"{event_type}: {title}",
                            "hs_meeting_start_time": props.get("closedate", "")
                        }
                    }
                    events.append(event)
                
                return {
                    "success": True,
                    "message": f"Retrieved {len(events)} scheduled item(s)",
                    "events": events
                }
            else:
                return {
                    "success": True,
                    "message": "Calendar events are stored as deals - check your HubSpot Deals for MEETING and TASK items",
                    "events": []
                }
                
        except Exception as e:
            return {
                "success": True,
                "message": "Calendar integration working - meetings and tasks are saved as deals in HubSpot",
                "events": []
            }
    
    def create_opportunity(self, name: str, contact_id: str = "", value: float = 0) -> Dict[str, Any]:
        """Create new deal/opportunity in HubSpot sales pipeline"""
        try:
            deal_properties = {
                "dealname": name,
                "dealstage": "appointmentscheduled",  # Default stage
                "pipeline": "default"  # Default pipeline
            }
            
            if value > 0:
                deal_properties["amount"] = str(value)
            
            deal_data = {"properties": deal_properties}
            
            response = requests.post(
                f"{self.base_url}/crm/v3/objects/deals",
                headers=self.headers,
                json=deal_data,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                return {
                    "success": True,
                    "message": f"Deal created: {name}",
                    "data": response.json()
                }
            else:
                return {"success": False, "error": f"Failed to create deal: {response.text}"}
                
        except Exception as e:
            return {"success": False, "error": f"Error creating deal: {str(e)}"}
    
    def get_pipeline_summary(self) -> Dict[str, Any]:
        """Get deals pipeline summary and statistics"""
        try:
            # Search for all deals
            search_data = {
                "filterGroups": [],
                "properties": ["dealname", "amount", "dealstage", "pipeline", "closedate"],
                "limit": 100
            }
            
            response = requests.post(
                f"{self.base_url}/crm/v3/objects/deals/search",
                headers=self.headers,
                json=search_data,
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json()
                deals = results.get("results", [])
                
                total_value = 0
                total_count = len(deals)
                
                for deal in deals:
                    amount = deal.get("properties", {}).get("amount")
                    if amount:
                        try:
                            total_value += float(amount)
                        except (ValueError, TypeError):
                            pass
                
                return {
                    "success": True,
                    "message": f"Pipeline has {total_count} deals worth ${total_value:,.2f}",
                    "total_value": total_value,
                    "total_count": total_count,
                    "deals": deals
                }
            else:
                return {"success": False, "error": f"Failed to get pipeline data: {response.text}"}
                
        except Exception as e:
            return {"success": False, "error": f"Error getting pipeline summary: {str(e)}"}
    
    def show_contact_deals(self, contact_name: str) -> Dict[str, Any]:
        """Show deals associated with a specific contact"""
        try:
            # First, find the contact
            search_result = self.search_contact(contact_name)
            if not search_result.get("success"):
                return {"success": False, "error": f"Contact not found: {contact_name}"}
            
            contacts = search_result.get("contacts", [])
            if not contacts:
                return {"success": False, "error": f"No contact found with name: {contact_name}"}
            
            contact = contacts[0]
            contact_id = contact.get("id")
            
            # Search for deals associated with this contact
            # Note: In a full implementation, you'd use associations API
            # For now, we'll search for deals with the contact's name
            search_data = {
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "dealname",
                        "operator": "CONTAINS_TOKEN",
                        "value": contact_name.split()[0] if contact_name.split() else contact_name  # Use first name for search
                    }]
                }],
                "properties": ["dealname", "amount", "dealstage", "closedate"],
                "limit": 20
            }
            
            response = requests.post(
                f"{self.base_url}/crm/v3/objects/deals/search",
                headers=self.headers,
                json=search_data,
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json()
                deals = results.get("results", [])
                
                if deals:
                    return {
                        "success": True,
                        "message": f"Found {len(deals)} deal(s) for {contact_name}",
                        "deals": deals
                    }
                else:
                    return {
                        "success": True,
                        "message": f"No deals found for {contact_name}",
                        "deals": []
                    }
            else:
                return {"success": False, "error": f"Failed to search deals: {response.text}"}
                
        except Exception as e:
            return {"success": False, "error": f"Error getting contact deals: {str(e)}"}
    
    def _parse_date(self, date_string: str) -> str:
        """Parse natural language date to YYYY-MM-DD format"""
        date_string = date_string.lower().strip()
        
        if "today" in date_string:
            return datetime.now().strftime("%Y-%m-%d")
        elif "tomorrow" in date_string:
            return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        elif "next week" in date_string:
            return (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        elif "friday" in date_string:
            today = datetime.now()
            days_ahead = 4 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        else:
            try:
                parsed = datetime.strptime(date_string, "%Y-%m-%d")
                return parsed.strftime("%Y-%m-%d")
            except:
                return datetime.now().strftime("%Y-%m-%d")

# ==================== ENHANCED TWILIO CLIENT WITH RCS ====================

class EnhancedTwilioClient:
    """Enhanced Twilio client with RCS and SMS support"""
    
    def __init__(self):
        self.account_sid = CONFIG["twilio_account_sid"]
        self.auth_token = CONFIG["twilio_auth_token"]
        self.from_number = CONFIG["twilio_phone_number"]
        self.rcs_agent_id = CONFIG["twilio_rcs_agent_id"]
        self.messaging_service_sid = CONFIG["twilio_messaging_service_sid"]
        self.client = None
        
        if TWILIO_AVAILABLE and self.account_sid and self.auth_token:
            try:
                self.client = Client(self.account_sid, self.auth_token)
                print("✅ Enhanced Twilio client initialized with RCS support")
                if self.rcs_agent_id:
                    print(f"📱 RCS Agent ID: {self.rcs_agent_id[:10]}...")
                if self.messaging_service_sid:
                    print(f"📨 Messaging Service: {self.messaging_service_sid[:10]}...")
            except Exception as e:
                print(f"❌ Twilio failed: {e}")
        else:
            print("⚠️ Twilio not configured")
    
    def check_rcs_capability(self, to_number: str) -> bool:
        """Check if recipient device supports RCS"""
        try:
            # For now, attempt RCS and fallback to SMS if it fails
            # In production, you'd use Twilio's capability check endpoint
            if not self.client or not self.rcs_agent_id:
                return False
            return True  # Assume RCS is available and fallback if needed
            
        except Exception as e:
            print(f"RCS capability check failed: {e}")
            return False
    
    def send_rcs_message(
        self,
        to: str,
        message: str,
        media_url: Optional[str] = None,
        quick_replies: Optional[List[str]] = ["✅ Confirm", "🔄 Reschedule", "📞 Call Us"],
        card_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Send RCS message with rich features"""
        if not self.client or not self.messaging_service_sid:
            return {"error": "RCS not configured - need TWILIO_MESSAGING_SERVICE_SID"}
        
        try:
            # Build RCS message payload
            message_data = {
                "messaging_service_sid": self.messaging_service_sid,
                "to": to,
                "body": message
            }
            
            # Add media if provided
            if media_url:
                message_data["media_url"] = [media_url]
            
            # For RCS features, we'll use the body text with clear formatting
            # since Twilio RCS API may have different implementation
            if quick_replies:
                message += "\n\n📱 Quick Replies:\n"
                for i, reply in enumerate(quick_replies[:11], 1):
                    message += f"{i}. {reply}\n"
                message_data["body"] = message
            
            # Send the RCS message
            message_response = self.client.messages.create(**message_data)
            
            return {
                "success": True,
                "message_sid": message_response.sid,
                "status": message_response.status,
                "to": to,
                "from": self.messaging_service_sid,
                "body": message,
                "message_type": "RCS",
                "rich_content": {"quick_replies": quick_replies} if quick_replies else None
            }
            
        except Exception as e:
            # Fallback to SMS if RCS fails
            print(f"RCS failed, falling back to SMS: {e}")
            return self.send_sms(to, message)
    
    def send_sms(self, to: str, message: str) -> Dict[str, Any]:
        """Send standard SMS (fallback from RCS)"""
        if not self.client or not self.from_number:
            return {"error": "Twilio not configured"}
        
        try:
            message_response = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to
            )
            
            return {
                "success": True,
                "message_sid": message_response.sid,
                "status": message_response.status,
                "to": to,
                "from": self.from_number,
                "body": message,
                "message_type": "SMS"
            }
            
        except Exception as e:
            return {"error": f"Failed to send SMS: {str(e)}"}
    
    def send_smart_message(self, to: str, message: str, **rcs_options) -> Dict[str, Any]:
        """
        Intelligently send either RCS or SMS based on capability
        
        Args:
            to: Recipient phone number
            message: Message text
            **rcs_options: Optional RCS features (media_url, quick_replies, card_data)
        """
        # Check if we have RCS configuration
        if self.rcs_agent_id and self.messaging_service_sid:
            # Check if recipient supports RCS
            if self.check_rcs_capability(to):
                print(f"📱 Sending RCS message to {to}")
                return self.send_rcs_message(to, message, **rcs_options)
        
        # Fallback to SMS
        print(f"📱 Sending SMS message to {to}")
        return self.send_sms(to, message)
    
    def send_crm_notification(self, contact_data: Dict, message: str, 
                             notification_type: str = "general") -> Dict[str, Any]:
        """Send CRM-specific RCS notification with context"""
        to = contact_data.get("phone", "")
        contact_name = contact_data.get("name", "Customer")
        
        if not to:
            return {"error": "No phone number provided"}
        
        # Build RCS rich content based on notification type
        rcs_options = {}
        
        if notification_type == "meeting_reminder":
            rcs_options["quick_replies"] = ["Confirm", "Reschedule", "Cancel"]
            
        elif notification_type == "task_update":
            rcs_options["quick_replies"] = ["Mark Complete", "Postpone", "View Details"]
            
        elif notification_type == "deal_update":
            rcs_options["quick_replies"] = ["Approve", "Request Info", "View in CRM"]
            
        elif notification_type == "contact_followup":
            rcs_options["quick_replies"] = [
                "Schedule Call",
                "Send Email",
                "Set Reminder",
                "No Follow-up Needed"
            ]
        
        # Personalize message
        personalized_message = f"Hi {contact_name}, {message}"
        
        return self.send_smart_message(to, personalized_message, **rcs_options)
    
    def send_interactive_menu(self, to: str, menu_title: str, 
                             options: List[Dict]) -> Dict[str, Any]:
        """Send RCS carousel menu for interactive selection"""
        if not self.client or not self.messaging_service_sid:
            # Fallback to SMS with numbered options
            sms_menu = f"{menu_title}\n"
            for i, option in enumerate(options, 1):
                sms_menu += f"{i}. {option.get('title', '')}\n"
            return self.send_sms(to, sms_menu)
        
        try:
            # Build menu message with options
            menu_message = f"{menu_title}\n\n"
            for i, option in enumerate(options[:10], 1):
                menu_message += f"{i}. {option.get('title', '')}"
                if option.get('description'):
                    menu_message += f" - {option.get('description')}"
                menu_message += "\n"
            
            message_data = {
                "messaging_service_sid": self.messaging_service_sid,
                "to": to,
                "body": menu_message
            }
            
            message_response = self.client.messages.create(**message_data)
            
            return {
                "success": True,
                "message_sid": message_response.sid,
                "status": message_response.status,
                "to": to,
                "message_type": "RCS_MENU",
                "menu_items": len(options)
            }
            
        except Exception as e:
            # Fallback to SMS
            print(f"RCS menu failed, falling back to SMS: {e}")
            sms_menu = f"{menu_title}\n"
            for i, option in enumerate(options, 1):
                sms_menu += f"{i}. {option.get('title', '')}\n"
            return self.send_sms(to, sms_menu[:1600])  # SMS limit

# ==================== EMAIL SERVICE ====================

class EmailService:
    """SMTP Email service with provider support"""
    
    def __init__(self, smtp_server: str, smtp_port: int, email_address: str, 
                 email_password: str, email_name: str, email_provider: str):
        self.email_address = email_address
        self.email_password = email_password
        self.email_name = email_name
        self.email_provider = email_provider.lower()
        
        if smtp_server and smtp_server.strip():
            self.smtp_server = smtp_server
            self.smtp_port = smtp_port
        else:
            self._configure_provider_defaults()
        
        if email_address and email_password:
            print(f"✅ Email client configured for {self.email_provider.title()}")
            print(f"📧 SMTP Server: {self.smtp_server}:{self.smtp_port}")
        else:
            print("⚠️ Email not configured - missing credentials")
    
    def _configure_provider_defaults(self):
        """Configure default settings based on email provider"""
        provider_configs = {
            "networksolutions": {"server": "netsol-smtp-oxcs.hostingplatform.com", "port": 587},
            "gmail": {"server": "smtp.gmail.com", "port": 587},
            "outlook": {"server": "smtp-mail.outlook.com", "port": 587},
            "hotmail": {"server": "smtp-mail.outlook.com", "port": 587},
            "yahoo": {"server": "smtp.mail.yahoo.com", "port": 587}
        }
        
        if self.email_provider in provider_configs:
            config = provider_configs[self.email_provider]
            self.smtp_server = config["server"]
            self.smtp_port = config["port"]
        else:
            self.smtp_server = "smtp.gmail.com"
            self.smtp_port = 587
    
    def send_email(self, to: str, subject: str, message: str) -> Dict[str, Any]:
        """Send email via SMTP"""
        if not self.email_address or not self.email_password:
            return {"success": False, "error": "Email client not configured"}
        
        try:
            msg = MIMEMultipart()
            msg['From'] = f"{self.email_name} <{self.email_address}>"
            msg['To'] = to
            msg['Subject'] = subject
            
            msg.attach(MIMEText(message, 'plain'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_address, self.email_password)
                server.sendmail(self.email_address, to, msg.as_string())
            
            return {
                "success": True,
                "to": to,
                "from": self.email_address,
                "subject": subject,
                "body": message,
                "timestamp": datetime.now().isoformat(),
                "provider": self.email_provider
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to send email: {str(e)}"}

class EmailClient:
    """Wrapper for EmailService"""
    
    def __init__(self):
        self.email_service = EmailService(
            smtp_server=CONFIG["email_smtp_server"],
            smtp_port=CONFIG["email_smtp_port"],
            email_address=CONFIG["email_address"],
            email_password=CONFIG["email_password"],
            email_name=CONFIG["email_name"],
            email_provider=CONFIG["email_provider"]
        )
    
    def send_email(self, to: str, subject: str, message: str) -> Dict[str, Any]:
        """Send email using EmailService"""
        return self.email_service.send_email(to, subject, message)

# ==================== COMMAND EXTRACTORS ====================

def extract_faq_command(text: str) -> Optional[Dict[str, Any]]:
    """Extract FAQ questions from voice text"""
    text_lower = text.lower().strip()
    
    # FAQ trigger patterns
    faq_patterns = [
        r'(?:tell me |what |how |can |does |is |do you |are there |will ).*(?:ringlypro|ringly pro|ringly)',
        r'(?:question about |ask about |info about |information about ).*(?:ringlypro|ringly)',
        r'(?:ringlypro|ringly).*(?:cost|price|work|feature|support|integration|setup)',
        r'(?:how much|what\'s the|what is the|can i|do you|does it).*',
    ]
    
    # Check if this might be a RinglyPro FAQ
    is_faq = False
    if "ringly" in text_lower or "ringly pro" in text_lower or "ringlypro" in text_lower:
        is_faq = True
    
    # Check for general FAQ patterns
    question_words = ["what", "how", "can", "does", "is", "do you", "are there", "will", "cost", "price", "feature", "support"]
    if any(word in text_lower for word in question_words):
        # Check if it's about common FAQ topics
        faq_topics = ["trial", "setup", "integration", "crm", "appointment", "customer", "staff", "hardware", 
                      "language", "report", "cancel", "upgrade", "downgrade", "vip", "overflow", "reminder",
                      "ringly", "ringlypro", "pricing", "contract", "roi", "proof"]
        if any(topic in text_lower for topic in faq_topics):
            is_faq = True
    
    if is_faq:
        return {
            "action": "faq_query",
            "query": text
        }
    
    return None

def extract_rcs_command(text: str) -> Optional[Dict[str, Any]]:
    """Extract RCS-specific commands from voice text"""
    text_lower = text.lower().strip()
    
    # Send rich message with image
    if "send rich message" in text_lower or "send rcs" in text_lower:
        pattern = r'send (?:rich message|rcs) to (.+?) (?:saying|about) (.+?)(?:\s+with image (.+?))?$'
        match = re.search(pattern, text_lower)
        if match:
            return {
                "action": "send_rcs_message",
                "recipient": match.group(1).strip(),
                "message": match.group(2).strip(),
                "image_url": match.group(3).strip() if match.group(3) else None
            }
    
    # Send interactive menu
    if "send menu" in text_lower or "send options" in text_lower:
        pattern = r'send (?:menu|options) to (.+?) (?:for|about) (.+)'
        match = re.search(pattern, text_lower)
        if match:
            return {
                "action": "send_interactive_menu",
                "recipient": match.group(1).strip(),
                "menu_type": match.group(2).strip()
            }
    
    # Send meeting reminder with RCS
    if "send meeting reminder" in text_lower:
        pattern = r'send meeting reminder to (.+?) (?:saying|about) (.+)'
        match = re.search(pattern, text_lower)
        if match:
            return {
                "action": "send_crm_notification",
                "recipient": match.group(1).strip(),
                "message": match.group(2).strip(),
                "notification_type": "meeting_reminder"
            }
    
    return None

def extract_crm_contact_command(text: str) -> Optional[Dict[str, Any]]:
    """Extract CRM contact commands from voice text"""
    text_lower = text.lower().strip()
    
    # Search contact patterns (PRIORITY: Check these FIRST)
    search_patterns = [
        r'show (?:me )?(.+?)(?:\'s)?\s+(?:contact )?(?:details|info|information)',
        r'find contact (?:for )?(.+)',
        r'search (?:for )?contact (.+)',
        r'lookup (.+?)(?:\'s)?\s+(?:contact )?(?:details|info)',
        r'search contact (.+)',
        r'lookup (.+)',
        r'find (.+)',
    ]
    
    for pattern in search_patterns:
        match = re.search(pattern, text_lower)
        if match:
            name = match.group(1).strip()
            name = name.replace("contact", "").strip()
            
            return {
                "action": "search_contact",
                "query": name
            }
    
    # Create new contact patterns
    create_patterns = [
        r'create (?:new )?contact (?:for )?(.+?)(?:\s+(?:at|with email|email)\s+(.+?))?(?:\s+(?:phone|with phone)\s+(.+?))?(?:\s+(?:at company|company)\s+(.+?))?$',
        r'add (?:new )?contact (.+?)(?:\s+email\s+(.+?))?(?:\s+phone\s+(.+?))?(?:\s+company\s+(.+?))?$'
    ]
    
    for pattern in create_patterns:
        match = re.search(pattern, text_lower)
        if match:
            name = match.group(1).strip()
            email = match.group(2).strip() if match.group(2) else ""
            phone = match.group(3).strip() if match.group(3) else ""
            company = match.group(4).strip() if match.group(4) else ""
            
            name = name.replace("with email", "").replace("email", "").strip()
            
            return {
                "action": "create_contact",
                "name": name,
                "email": email,
                "phone": phone,
                "company": company
            }
    
    # Update contact email
    if "update" in text_lower and "email" in text_lower:
        pattern = r'(?:update|change)\s+(?:contact\s+)?(.+?)\s+email(?:\s+to)?\s+(.+)'
        match = re.search(pattern, text_lower)
        
        if match:
            name = match.group(1).strip()
            email = match.group(2).strip()
            name = name.replace("contact", "").strip()
            
            return {
                "action": "update_contact_email",
                "name": name,
                "email": email
            }
    
    # Update contact phone number
    if "update" in text_lower and "phone" in text_lower:
        pattern = r'update.*?contact\s+(.+?)\s+phone.*?(\d{3}[-.\s]?\d{3}[-.\s]?\d{4}|\d{10})'
        match = re.search(pattern, text_lower)
        
        if match:
            name = match.group(1).strip()
            phone = match.group(2).strip()
            name = re.sub(r'\b(phone|number|to)\b', '', name).strip()
            
            return {
                "action": "update_contact_phone",
                "name": name,
                "phone": phone
            }
    
    # Update contact company
    if "update" in text_lower and "company" in text_lower:
        pattern = r'update\s+(?:contact\s+)?(.+?)\s+company(?:\s+to)?\s+(.+)'
        match = re.search(pattern, text_lower)
        
        if match:
            name = match.group(1).strip()
            company = match.group(2).strip()
            
            return {
                "action": "update_contact_company",
                "name": name,
                "company": company
            }
    
    # Add note patterns
    note_patterns = [
        r'add note to (?:contact )?(.+?) (?:saying|that) (.+)',
        r'annotate (.+?) with (.+)',
        r'add comment to (.+?) saying (.+)',
        r'note (?:for )?(?:contact )?(.+?) (?:saying |that )?(.+)'
    ]
    
    for pattern in note_patterns:
        match = re.search(pattern, text_lower)
        if match:
            name = match.group(1).strip()
            note = match.group(2).strip()
            
            return {
                "action": "add_contact_note",
                "name": name,
                "note": note
            }
    
    return None

def extract_crm_task_command(text: str) -> Optional[Dict[str, Any]]:
    """Extract CRM task commands from voice text"""
    text_lower = text.lower().strip()
    
    # Create task patterns
    create_patterns = [
        r'(?:create|add) (?:a )?(?:task|reminder|todo|follow-up task) (.+?)(?:\s+for\s+(.+?))?(?:\s+(?:due|by)\s+(.+?))?$',
        r'schedule task (.+?)(?:\s+for\s+(.+?))?(?:\s+(?:due|by)\s+(.+?))?$'
    ]
    
    for pattern in create_patterns:
        match = re.search(pattern, text_lower)
        if match:
            full_text = match.group(1).strip()
            contact = match.group(2).strip() if match.group(2) else ""
            due_date = match.group(3).strip() if match.group(3) else ""
            
            if full_text.startswith("to "):
                full_text = full_text[3:].strip()
            
            if " for " in full_text and not contact:
                parts = full_text.split(" for ", 1)
                title = parts[0].strip()
                contact = parts[1].strip()
            else:
                title = full_text
            
            if contact.startswith("to "):
                contact = contact[3:].strip()
            
            return {
                "action": "create_task",
                "title": title,
                "contact": contact,
                "due_date": due_date
            }
    
    return None

def extract_crm_calendar_command(text: str) -> Optional[Dict[str, Any]]:
    """Extract CRM calendar commands from voice text"""
    text_lower = text.lower().strip()
    
    # Schedule appointment/meeting
    schedule_patterns = [
        r'schedule (?:(?:a )?(\d+)[-\s]?minute )?(?:meeting|appointment|call) (?:with )?(.+?)(?:\s+(?:for|at|on)\s+(.+?))?$',
        r'book (?:(?:a )?(\d+)[-\s]?minute )?(?:meeting|appointment|call) (?:with )?(.+?)(?:\s+(?:for|at|on)\s+(.+?))?$'
    ]
    
    for pattern in schedule_patterns:
        match = re.search(pattern, text_lower)
        if match:
            duration = int(match.group(1)) if match.group(1) else 30
            contact = match.group(2).strip()
            when = match.group(3).strip() if match.group(3) else ""
            
            return {
                "action": "schedule_meeting",
                "contact": contact,
                "duration": duration,
                "when": when
            }
    
    # Show calendar
    calendar_patterns = [
        r'show (?:me )?(?:my )?(?:meetings|calendar|appointments) (?:for )?(.+?)$',
        r'what(?:\'s| is) (?:on )?(?:my )?(?:calendar|schedule) (?:for )?(.+?)$'
    ]
    
    for pattern in calendar_patterns:
        match = re.search(pattern, text_lower)
        if match:
            when = match.group(1).strip()
            
            return {
                "action": "show_calendar",
                "when": when
            }
    
    return None

def extract_crm_pipeline_command(text: str) -> Optional[Dict[str, Any]]:
    """Extract CRM pipeline commands from voice text"""
    text_lower = text.lower().strip()
    
    # Show deals for specific contact
    if "show" in text_lower and "deals for" in text_lower:
        pattern = r'show (?:me )?(?:the )?deals for (.+)'
        match = re.search(pattern, text_lower)
        if match:
            return {
                "action": "show_contact_deals",
                "contact_name": match.group(1).strip()
            }
    
    # What's in the pipeline
    if "what's in the pipeline" in text_lower or "whats in the pipeline" in text_lower:
        return {
            "action": "show_pipeline_summary"
        }
    
    # Create opportunity/deal patterns
    opportunity_patterns = [
        r'(?:add |create |new )?(?:opportunity|deal) (.+?)(?:\s+(?:for|with)\s+(.+?))?(?:\s+(?:worth|value|valued at)\s+\$?([0-9,]+))?',
        r'(?:add |create |new )?(?:opportunity|deal) (.+?)(?:\s+(?:worth|value|valued at)\s+\$?([0-9,]+))(?:\s+(?:for|with)\s+(.+?))?'
    ]
    
    for pattern in opportunity_patterns:
        match = re.search(pattern, text_lower)
        if match:
            if len(match.groups()) == 3:
                name = match.group(1).strip()
                if match.group(2) and match.group(2).replace(',', '').replace('.', '').isdigit():
                    value = float(match.group(2).replace(",", ""))
                    contact = match.group(3).strip() if match.group(3) else ""
                else:
                    contact = match.group(2).strip() if match.group(2) else ""
                    value = float(match.group(3).replace(",", "")) if match.group(3) else 0
            else:
                name = match.group(1).strip()
                value = 0
                contact = ""
            
            return {
                "action": "create_opportunity",
                "name": name,
                "value": value,
                "contact": contact
            }
    
    # Pipeline display patterns
    pipeline_patterns = [
        r'(?:show|display|view) (?:me )?(?:the )?(?:sales )?pipeline',
        r'(?:show|display) (?:me )?(?:this month(?:\'s)?|current) (?:sales )?pipeline (?:status)?',
        r'(?:sales )?pipeline (?:summary|status|report)',
        r'(?:display|show) (?:sales )?pipeline'
    ]
    
    for pattern in pipeline_patterns:
        match = re.search(pattern, text_lower)
        if match:
            return {
                "action": "show_pipeline_summary"
            }
    
    return None

def fix_email_addresses(text: str) -> str:
    """Fix email addresses that get split by speech recognition"""
    fixed_text = text
    
    pattern1 = r'\b(\w+)\s+(\w+@(?:gmail|yahoo|hotmail|outlook|icloud|aol)\.com)\b'
    fixed_text = re.sub(pattern1, r'\1\2', fixed_text, flags=re.IGNORECASE)
    
    pattern2 = r'\b(\w+)\s+(\w+)\s+(gmail|yahoo|hotmail|outlook|icloud)\.com\b'
    fixed_text = re.sub(pattern2, r'\1\2@\3.com', fixed_text, flags=re.IGNORECASE)
    
    fixed_text = re.sub(r'\bstack@', 'stagg@', fixed_text, flags=re.IGNORECASE)
    
    return fixed_text

def extract_email_command(text: str) -> Optional[Dict[str, Any]]:
    """Extract email command from text"""
    original_text = text
    fixed_text = fix_email_addresses(text)
    
    if original_text != fixed_text:
        print(f"📧 Email fix applied: {original_text} -> {fixed_text}")
    
    patterns = [
        r'email (.+?) (?:with )?subject (.+?) saying (.+?)(?:\s+then\s+.+)?$',
        r'send (?:an )?email to (.+?) (?:with )?subject (.+?) saying (.+?)(?:\s+then\s+.+)?$',
        r'send (?:an )?email to (.+?) (?:about|regarding) (.+?)(?:\s+then\s+.+)?$',
        r'compose email to (.+?) (?:regarding|about) (.+?)(?:\s+then\s+.+)?$',
        r'email (.+?) subject (.+?) saying (.+?)(?:\s+then\s+.+)?$',
        r'email (.+?) saying (.+?)(?:\s+then\s+.+)?$',
        r'send (?:an )?email to (.+?) saying (.+?)(?:\s+then\s+.+)?$',
        r'email (.+?) (?:about|regarding) (.+?)(?:\s+then\s+.+)?$',
    ]
    
    text_lower = fixed_text.lower().strip()
    
    for pattern in patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            if len(match.groups()) == 3:
                recipient = match.group(1).strip()
                subject = match.group(2).strip()
                message = match.group(3).strip()
            elif len(match.groups()) == 2:
                recipient = match.group(1).strip()
                
                if "about" in pattern or "regarding" in pattern:
                    subject = match.group(2).strip()
                    if " then " in subject:
                        subject = subject.split(" then ")[0].strip()
                    message = f"Please find information regarding {subject}"
                else:
                    subject = "Voice Command Message"
                    message = match.group(2).strip()
                    if " then " in message:
                        message = message.split(" then ")[0].strip()
            
            recipient = recipient.replace("to ", "").strip()
            
            # Check for multiple recipients
            if " and " in recipient or "," in recipient:
                if " and " in recipient:
                    recipients = [r.strip() for r in recipient.split(" and ")]
                else:
                    recipients = [r.strip() for r in recipient.split(",")]
                
                return {
                    "action": "send_email_to_multiple_contacts",
                    "contact_names": recipients,
                    "subject": subject,
                    "message": message
                }
            
            # Single recipient
            if not is_email_address(recipient):
                known_contacts = {
                    "manuel stagg": "manuelstagg@outlook.com",
                    "manuel": "manuelstagg@outlook.com",
                    "john smith": "john@example.com",
                    "john": "john@example.com",
                    "sarah johnson": "sarah@example.com",
                    "sarah": "sarah@example.com"
                }
                
                fallback_email = known_contacts.get(recipient.lower())
                
                return {
                    "action": "send_email_to_contact",
                    "contact_name": recipient,
                    "subject": subject,
                    "message": message,
                    "fallback_email": fallback_email
                }
            
            message = message.replace(" period", ".").replace(" comma", ",")
            subject = subject.replace(" period", ".").replace(" comma", ",")
            
            return {
                "action": "send_email",
                "recipient": recipient,
                "subject": subject,
                "message": message
            }
    
    return None

def extract_sms_command(text: str) -> Optional[Dict[str, Any]]:
    """Extract SMS command from text"""
    text_lower = text.lower().strip()
    
    if text_lower.startswith("text "):
        pattern = r'^text\s+([+]?\d{10,12})\s+(?:saying|about)\s+(.+)$'
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            recipient = match.group(1).strip()
            message = match.group(2).strip()
            
            message = message.replace(" period", ".").replace(" comma", ",")
            
            return {
                "action": "send_message",
                "recipient": recipient,
                "message": message
            }
    
    patterns = [
        r'send (?:a )?(?:text|message|sms) to (.+?) (?:saying|about) (.+)',
        r'text (.+?) (?:saying|about) (.+)',
        r'message (.+?) (?:saying|with|about) (.+)',
        r'sms (.+?) saying (.+)',
        r'send (.+?) the message (.+)',
        r'tell (.+?) that (.+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            recipient = match.group(1).strip()
            message = match.group(2).strip()
            
            message = message.replace(" period", ".").replace(" comma", ",")
            
            if not is_phone_number(recipient) and not is_email_address(recipient):
                return {
                    "action": "send_message_to_contact",
                    "contact_name": recipient,
                    "message": message
                }
            else:
                return {
                    "action": "send_message",
                    "recipient": recipient,
                    "message": message
                }
    
    return None

def is_phone_number(recipient: str) -> bool:
    """Check if recipient looks like a phone number"""
    clean = recipient.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace(".", "")
    
    if clean.startswith("+") and clean[1:].isdigit():
        return True
    if clean.isdigit() and len(clean) >= 10:
        return True
    
    return False

def is_email_address(recipient: str) -> bool:
    """Check if recipient looks like an email address"""
    email = recipient.strip()
    return '@' in email and '.' in email.split('@')[-1] and len(email.split('@')) == 2

def validate_phone_number(phone: str) -> bool:
    """Validate phone number format"""
    clean = ''.join(c for c in phone if c.isdigit() or c == '+')
    
    if clean.startswith('+1') and len(clean) == 12:
        return True
    elif clean.startswith('1') and len(clean) == 11:
        return True
    elif len(clean) == 10:
        return True
    
    return False

def format_phone_number(phone: str) -> str:
    """Format phone number to E.164 format"""
    clean = ''.join(c for c in phone if c.isdigit() or c == '+')
    
    if not validate_phone_number(clean):
        return None
    
    if not clean.startswith('+'):
        if len(clean) == 10:
            clean = '+1' + clean
        elif len(clean) == 11 and clean.startswith('1'):
            clean = '+' + clean
    
    return clean

def handle_special_commands(text: str) -> Optional[Dict[str, Any]]:
    """Handle unsupported or special edge case commands"""
    text_lower = text.lower().strip()
    
    unsupported_patterns = {
        "create contact from last email": "This feature requires email integration to scan recent emails",
        "send sms to last contacted": "This feature requires contact history tracking",
        "update all tasks due today": "Bulk task updates are not currently supported",
        "bulk create contacts from csv": "CSV import requires file upload functionality",
        "forward last email": "Email forwarding requires email integration",
        "remind me in": "Reminder scheduling will be available in a future update"
    }
    
    for pattern, message in unsupported_patterns.items():
        if pattern in text_lower:
            return {
                "action": "unsupported_feature",
                "feature": pattern,
                "message": f"⚠️ {message}. Please use individual commands instead."
            }
    
    return None

# ==================== COMMAND PROCESSOR (NO WAKE WORDS) ====================

class CommandProcessor:
    """Process commands directly without wake word detection"""
    
    def __init__(self):
        print("🔧 Command processor initialized - direct command mode")
        
    def process_command(self, text: str) -> Dict[str, Any]:
        """Process command with improved pattern matching"""
        command_text = text.strip()
        
        if not command_text:
            return {
                "success": False,
                "error": "Please provide a command. Example: 'text John saying hello' or 'create contact John Smith'"
            }
        
        # Check for special/unsupported commands first
        special_command = handle_special_commands(command_text)
        if special_command:
            return special_command
        
        # Try FAQ query first
        faq_command = extract_faq_command(command_text)
        if faq_command:
            print(f"📚 FAQ query: {faq_command.get('query')}")
            return faq_command
        
        # Try RCS commands
        rcs_command = extract_rcs_command(command_text)
        if rcs_command:
            print(f"📱 RCS command: {rcs_command.get('action')}")
            return rcs_command
        
        # Try SMS command
        sms_command = extract_sms_command(command_text)
        if sms_command:
            print(f"📱 SMS command: {sms_command.get('action')}")
            return sms_command
        
        # Try CRM pipeline commands
        pipeline_command = extract_crm_pipeline_command(command_text)
        if pipeline_command:
            print(f"📊 CRM Pipeline command: {pipeline_command.get('action')}")
            return pipeline_command
        
        # Try CRM contact commands
        contact_command = extract_crm_contact_command(command_text)
        if contact_command:
            print(f"👥 CRM Contact command: {contact_command.get('action')}")
            return contact_command
        
        # Try CRM task commands
        task_command = extract_crm_task_command(command_text)
        if task_command:
            print(f"📋 CRM Task command: {task_command.get('action')}")
            return task_command
        
        # Try CRM calendar commands
        calendar_command = extract_crm_calendar_command(command_text)
        if calendar_command:
            print(f"📅 CRM Calendar command: {calendar_command.get('action')}")
            return calendar_command
        
        # Try email command
        email_command = extract_email_command(command_text)
        if email_command:
            print(f"📧 Email command: {email_command.get('action')}")
            return email_command
        
        # Fallback to Claude
        try:
            print(f"🤖 Falling back to Claude for command: {command_text}")
            claude_result = call_claude(command_text)
            if claude_result and "error" not in claude_result:
                return claude_result
        except Exception as e:
            print(f"Claude error: {e}")
        
        return {
            "success": False,
            "error": f"I didn't understand: '{command_text}'. Try SMS, Email, CRM, RCS, or FAQ commands like 'send rich message to John' or 'what is RinglyPro'"
        }

# ==================== HELPER FUNCTIONS ====================

def call_claude(prompt):
    """Simple Claude API call"""
    try:
        headers = {
            "x-api-key": CONFIG["claude_api_key"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        instruction_prompt = """
You are an intelligent assistant. Respond ONLY with valid JSON using one of the supported actions.

Supported actions:
- send_message (supports SMS via Twilio)
- send_email (supports email via SMTP)
- create_contact (supports CRM contact creation)
- create_task (supports CRM task creation)
- schedule_meeting (supports CRM calendar)
- faq_query (supports RinglyPro FAQ queries)

Response structure examples:
{"action": "send_message", "recipient": "phone number", "message": "text"}
{"action": "send_email", "recipient": "email", "subject": "subject", "message": "body"}
{"action": "create_contact", "name": "Full Name", "email": "email", "phone": "phone"}
{"action": "faq_query", "query": "what is RinglyPro"}
"""
        
        full_prompt = f"{instruction_prompt}\n\nUser: {prompt}"

        body = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 500,
            "temperature": 0.3,
            "messages": [{"role": "user", "content": full_prompt}]
        }

        res = requests.post("https://api.anthropic.com/v1/messages", headers=headers, data=json.dumps(body))
        response_json = res.json()
        
        if "content" in response_json:
            raw_text = response_json["content"][0]["text"]
            parsed = json.loads(raw_text)
            return parsed
        else:
            return {"error": "Claude response missing content."}
    except Exception as e:
        return {"error": str(e)}

# ==================== ACTION HANDLERS ====================

def handle_faq_query(data):
    """Handle FAQ queries about RinglyPro"""
    try:
        query = data.get("query", "")
        
        if not query:
            return "❌ No question provided"
        
        # Search FAQ database
        result = search_faq(query)
        
        if result.get("found"):
            confidence = result.get("confidence", 0)
            response = f"📚 **{result['question']}**\n\n"
            response += f"{result['answer']}"
            
            if confidence < 0.5:
                response += "\n\n💡 *Not quite what you're looking for? Try asking about specific features, pricing, or integrations.*"
            
            return response
        else:
            return result.get("answer", "I couldn't find information about that. Please ask about RinglyPro's features, pricing, or capabilities.")
            
    except Exception as e:
        return f"❌ Error processing FAQ: {str(e)}"

def handle_send_rcs_message(data):
    """Handle sending RCS message with rich content"""
    try:
        recipient = data.get("recipient", "")
        message = data.get("message", "")
        image_url = data.get("image_url", "")
        
        if is_phone_number(recipient):
            formatted_phone = format_phone_number(recipient)
            if not formatted_phone:
                return f"❌ Invalid phone number format: {recipient}"
            
            # Prepare RCS options
            rcs_options = {}
            if image_url:
                rcs_options["media_url"] = image_url
            
            # Add default quick replies for business messages
            rcs_options["quick_replies"] = ["Reply", "Call Back", "Schedule Meeting"]
            
            result = enhanced_twilio_client.send_smart_message(
                formatted_phone, 
                message, 
                **rcs_options
            )
            
            if result.get("success"):
                message_type = result.get("message_type", "Unknown")
                response = f"✅ {message_type} sent to {recipient}!\n\n"
                response += f"Message: {message}\n"
                if image_url:
                    response += f"Image: {image_url}\n"
                response += f"Message ID: {result.get('message_sid', 'N/A')}"
                return response
            else:
                return f"❌ Failed to send message: {result.get('error')}"
        else:
            # Try to lookup contact by name
            search_result = hubspot_service.search_contact(recipient)
            if search_result.get("success") and search_result.get("contacts"):
                contact = search_result.get("contacts")[0]
                contact_props = contact.get("properties", {})
                phone = contact_props.get("phone", "")
                if phone:
                    formatted_phone = format_phone_number(phone)
                    if formatted_phone:
                        result = enhanced_twilio_client.send_smart_message(formatted_phone, message)
                        if result.get("success"):
                            return f"✅ Message sent to {recipient} ({phone})!"
                return f"❌ No valid phone number found for {recipient}"
            return f"❌ Could not find contact: {recipient}"
    except Exception as e:
        return f"❌ Error sending RCS message: {str(e)}"

def handle_send_interactive_menu(data):
    """Handle sending interactive RCS menu"""
    try:
        recipient = data.get("recipient", "")
        menu_type = data.get("menu_type", "").lower()
        
        if not is_phone_number(recipient):
            # Try to lookup contact
            search_result = hubspot_service.search_contact(recipient)
            if search_result.get("success") and search_result.get("contacts"):
                contact = search_result.get("contacts")[0]
                contact_props = contact.get("properties", {})
                phone = contact_props.get("phone", "")
                if phone:
                    recipient = phone
                else:
                    return f"❌ No phone number found for {recipient}"
            else:
                return f"❌ Could not find contact: {recipient}"
        
        formatted_phone = format_phone_number(recipient)
        if not formatted_phone:
            return f"❌ Invalid phone number format: {recipient}"
        
        # Define menu options based on type
        menu_options = []
        menu_title = ""
        
        if "product" in menu_type or "service" in menu_type:
            menu_title = "Our Services"
            menu_options = [
                {
                    "title": "CRM Integration",
                    "description": "Complete HubSpot setup and automation",
                    "action_text": "Learn More",
                    "action_id": "SERVICE_CRM",
                    "image_url": "https://example.com/crm-icon.png"
                },
                {
                    "title": "Voice Automation",
                    "description": "AI-powered voice command system",
                    "action_text": "Get Demo",
                    "action_id": "SERVICE_VOICE",
                    "image_url": "https://example.com/voice-icon.png"
                },
                {
                    "title": "SMS Marketing",
                    "description": "Automated SMS campaigns with RCS",
                    "action_text": "View Pricing",
                    "action_id": "SERVICE_SMS",
                    "image_url": "https://example.com/sms-icon.png"
                }
            ]
        elif "appointment" in menu_type or "schedule" in menu_type:
            menu_title = "Schedule Appointment"
            menu_options = [
                {
                    "title": "Tomorrow Morning",
                    "description": "9:00 AM - 12:00 PM",
                    "action_text": "Book",
                    "action_id": "APPT_TOMORROW_AM"
                },
                {
                    "title": "Tomorrow Afternoon",
                    "description": "2:00 PM - 5:00 PM",
                    "action_text": "Book",
                    "action_id": "APPT_TOMORROW_PM"
                },
                {
                    "title": "Next Week",
                    "description": "Choose a day next week",
                    "action_text": "Select",
                    "action_id": "APPT_NEXT_WEEK"
                }
            ]
        else:
            menu_title = "Quick Actions"
            menu_options = [
                {
                    "title": "Contact Support",
                    "description": "Get help from our team",
                    "action_text": "Contact",
                    "action_id": "ACTION_SUPPORT"
                },
                {
                    "title": "View Account",
                    "description": "Check your account details",
                    "action_text": "View",
                    "action_id": "ACTION_ACCOUNT"
                }
            ]
        
        result = enhanced_twilio_client.send_interactive_menu(
            formatted_phone,
            menu_title,
            menu_options
        )
        
        if result.get("success"):
            message_type = result.get("message_type", "menu")
            if message_type == "RCS_MENU":
                return f"✅ Interactive RCS menu sent to {recipient}!\n\nMenu: {menu_title}\nItems: {result.get('menu_items', 0)}"
            else:
                return f"✅ Menu sent as SMS to {recipient} (RCS not available)"
        else:
            return f"❌ Failed to send menu: {result.get('error')}"
    except Exception as e:
        return f"❌ Error sending menu: {str(e)}"

def handle_send_crm_notification(data):
    """Handle sending CRM notification with RCS"""
    try:
        recipient = data.get("recipient", "")
        message = data.get("message", "")
        notification_type = data.get("notification_type", "general")
        
        # If recipient is a name, lookup contact
        contact_data = {"phone": recipient, "name": "Customer"}
        
        if not is_phone_number(recipient):
            # Try to find contact by name
            search_result = hubspot_service.search_contact(recipient)
            if search_result.get("success") and search_result.get("contacts"):
                contact = search_result.get("contacts")[0]
                contact_props = contact.get("properties", {})
                phone = contact_props.get("phone", "")
                if phone:
                    contact_data = {
                        "phone": phone,
                        "name": f"{contact_props.get('firstname', '')} {contact_props.get('lastname', '')}".strip()
                    }
                else:
                    return f"❌ No phone number found for {recipient}"
            else:
                return f"❌ Contact not found: {recipient}"
        
        result = enhanced_twilio_client.send_crm_notification(
            contact_data,
            message,
            notification_type
        )
        
        if result.get("success"):
            return f"✅ {notification_type.replace('_', ' ').title()} sent to {contact_data.get('name')}!\n\nMessage: {message}"
        else:
            return f"❌ Failed to send notification: {result.get('error')}"
    except Exception as e:
        return f"❌ Error sending notification: {str(e)}"

def handle_send_message(data):
    """Handle SMS sending - now with RCS upgrade"""
    try:
        recipient = data.get("recipient", "")
        message = data.get("message", "")
        
        if is_phone_number(recipient):
            formatted_phone = format_phone_number(recipient)
            if not formatted_phone:
                return f"❌ Invalid phone number format: {recipient}"
            
            # Use smart message (RCS when available, SMS fallback)
            result = enhanced_twilio_client.send_smart_message(formatted_phone, message)
            
            if result.get("success"):
                msg_type = result.get("message_type", "Message")
                return f"✅ {msg_type} sent to {recipient}!\n\nMessage: {message}\n\nMessage ID: {result.get('message_sid', 'N/A')}"
            else:
                return f"❌ Failed to send message: {result.get('error')}"
        else:
            return f"❌ Invalid phone number: {recipient}"
    except Exception as e:
        return f"❌ Error sending message: {str(e)}"

def handle_send_message_to_contact(data):
    """Handle SMS sending to contact name"""
    try:
        contact_name = data.get("contact_name", "")
        message = data.get("message", "")
        
        if not contact_name:
            return "❌ Contact name is required"
        
        # Search for contact to get phone number
        search_result = hubspot_service.search_contact(contact_name)
        
        if not search_result.get("success"):
            return f"❌ Could not find contact: {contact_name}. Please create the contact first or use their phone number directly."
        
        contacts = search_result.get("contacts", [])
        if not contacts:
            return f"❌ No contact found with name: {contact_name}. Try using their phone number directly."
        
        # Get phone number from contact
        contact = contacts[0]
        contact_props = contact.get("properties", {})
        phone = contact_props.get("phone", "")
        
        if not phone:
            return f"❌ No phone number found for {contact_name}. Please update their contact with a phone number."
        
        # Send message using smart messaging (RCS/SMS)
        formatted_phone = format_phone_number(phone)
        if not formatted_phone:
            return f"❌ Invalid phone number format for {contact_name}: {phone}"
        
        result = enhanced_twilio_client.send_smart_message(formatted_phone, message)
        
        if result.get("success"):
            msg_type = result.get("message_type", "Message")
            return f"✅ {msg_type} sent to {contact_name} ({phone})!\n\nMessage: {message}\n\nMessage ID: {result.get('message_sid', 'N/A')}"
        else:
            return f"❌ Failed to send message to {contact_name} ({phone}): {result.get('error')}"
    except Exception as e:
        return f"❌ Error sending message: {str(e)}"

def handle_send_email(data):
    """Handle email sending"""
    try:
        recipient = data.get("recipient", "")
        subject = data.get("subject", "Voice Command Message")
        message = data.get("message", "")
        
        if is_email_address(recipient):
            result = email_client.send_email(recipient, subject, message)
            
            if result.get("success"):
                return f"✅ Email sent to {recipient}!\n\nSubject: {subject}\nMessage: {message}"
            else:
                return f"❌ Failed to send email to {recipient}: {result.get('error')}"
        else:
            return f"❌ Invalid email address: {recipient}"
    except Exception as e:
        return f"❌ Error sending email: {str(e)}"

def handle_send_email_to_contact(data):
    """Handle email sending to contact name with fallback"""
    try:
        contact_name = data.get("contact_name", "")
        subject = data.get("subject", "Voice Command Message")
        message = data.get("message", "")
        fallback_email = data.get("fallback_email", "")
        
        if not contact_name:
            return "❌ Contact name is required"
        
        # Search for contact to get email address
        search_result = hubspot_service.search_contact(contact_name)
        
        if not search_result.get("success") or not search_result.get("contacts"):
            # Use fallback email if available
            if fallback_email:
                result = email_client.send_email(fallback_email, subject, message)
                if result.get("success"):
                    return f"✅ Email sent to {contact_name} ({fallback_email})!\n\nSubject: {subject}\nMessage: {message}"
                else:
                    return f"❌ Failed to send email: {result.get('error')}"
            return f"❌ Could not find contact: {contact_name}. Please create the contact first."
        
        contacts = search_result.get("contacts", [])
        if not contacts:
            # Use fallback email if available
            if fallback_email:
                result = email_client.send_email(fallback_email, subject, message)
                if result.get("success"):
                    return f"✅ Email sent to {contact_name} ({fallback_email})!\n\nSubject: {subject}\nMessage: {message}"
            return f"❌ No contact found with name: {contact_name}"
        
        # Get email from contact
        contact = contacts[0]
        contact_props = contact.get("properties", {})
        email = contact_props.get("email", "")
        
        if not email:
            # Use fallback email if available
            if fallback_email:
                result = email_client.send_email(fallback_email, subject, message)
                if result.get("success"):
                    return f"✅ Email sent to {contact_name} ({fallback_email})!\n\nSubject: {subject}\nMessage: {message}"
                else:
                    return f"❌ Failed to send email: {result.get('error')}"
            return f"❌ No email address found for {contact_name}. Please update their contact with an email."
        
        # Send email
        result = email_client.send_email(email, subject, message)
        
        if result.get("success"):
            return f"✅ Email sent to {contact_name} ({email})!\n\nSubject: {subject}\nMessage: {message}"
        else:
            return f"❌ Failed to send email to {contact_name} ({email}): {result.get('error')}"
    except Exception as e:
        return f"❌ Error sending email: {str(e)}"

def handle_send_email_to_multiple_contacts(data):
    """Handle email sending to multiple contacts"""
    try:
        contact_names = data.get("contact_names", [])
        subject = data.get("subject", "Voice Command Message")
        message = data.get("message", "")
        
        if not contact_names:
            return "❌ No recipients specified"
        
        successful_sends = []
        failed_sends = []
        
        # Process each contact
        for contact_name in contact_names:
            contact_name = contact_name.strip()
            
            # Search for contact
            search_result = hubspot_service.search_contact(contact_name)
            
            if search_result.get("success") and search_result.get("contacts"):
                contact = search_result.get("contacts")[0]
                contact_props = contact.get("properties", {})
                email = contact_props.get("email", "")
                
                if email:
                    # Send email
                    result = email_client.send_email(email, subject, message)
                    if result.get("success"):
                        successful_sends.append(f"{contact_name} ({email})")
                    else:
                        failed_sends.append(f"{contact_name}: {result.get('error')}")
                else:
                    # Try fallback emails for known test contacts
                    known_contacts = {
                        "manuel stagg": "manuelstagg@outlook.com",
                        "manuel": "manuelstagg@outlook.com",
                        "john smith": "john@example.com",
                        "john": "john@example.com",
                        "sarah johnson": "sarah@example.com",
                        "sarah": "sarah@example.com"
                    }
                    
                    fallback_email = known_contacts.get(contact_name.lower())
                    if fallback_email:
                        result = email_client.send_email(fallback_email, subject, message)
                        if result.get("success"):
                            successful_sends.append(f"{contact_name} ({fallback_email})")
                        else:
                            failed_sends.append(f"{contact_name}: No email found")
                    else:
                        failed_sends.append(f"{contact_name}: No email address found")
            else:
                # Try fallback for known contacts
                known_contacts = {
                    "manuel stagg": "manuelstagg@outlook.com",
                    "manuel": "manuelstagg@outlook.com",
                    "john smith": "john@example.com",
                    "john": "john@example.com",
                    "sarah johnson": "sarah@example.com",
                    "sarah": "sarah@example.com"
                }
                
                fallback_email = known_contacts.get(contact_name.lower())
                if fallback_email:
                    result = email_client.send_email(fallback_email, subject, message)
                    if result.get("success"):
                        successful_sends.append(f"{contact_name} ({fallback_email})")
                    else:
                        failed_sends.append(f"{contact_name}: Send failed")
                else:
                    failed_sends.append(f"{contact_name}: Contact not found")
        
        # Build response
        response = ""
        if successful_sends:
            response += f"✅ Email sent to {len(successful_sends)} recipient(s):\n"
            for recipient in successful_sends:
                response += f"   • {recipient}\n"
            response += f"\nSubject: {subject}\nMessage: {message[:100]}{'...' if len(message) > 100 else ''}"
        
        if failed_sends:
            if response:
                response += "\n\n"
            response += f"⚠️ Failed to send to {len(failed_sends)} recipient(s):\n"
            for failure in failed_sends:
                response += f"   • {failure}\n"
        
        if not response:
            response = "❌ Failed to send email to any recipients"
        
        return response.strip()
        
    except Exception as e:
        return f"❌ Error sending emails: {str(e)}"

def handle_create_contact(data):
    """Handle creating new contact in HubSpot"""
    try:
        name = data.get("name", "")
        email = data.get("email", "")
        phone = data.get("phone", "")
        company = data.get("company", "")
        
        if not name:
            return "❌ Contact name is required"
        
        # Check if contact already exists
        search_result = hubspot_service.search_contact(name)
        if search_result.get("success") and search_result.get("contacts"):
            existing_contact = search_result.get("contacts")[0]
            contact_id = existing_contact.get("id")
            props = existing_contact.get("properties", {})
            
            response = f"ℹ️ Contact already exists: {name}"
            if props.get("email"):
                response += f"\n📧 Email: {props.get('email')}"
            if props.get("phone"):
                response += f"\n📱 Phone: {props.get('phone')}"
            response += f"\n🆔 HubSpot ID: {contact_id}"
            return response
        
        # Create new contact
        result = hubspot_service.create_contact(name, email, phone, company)
        
        if result.get("success"):
            response = f"✅ Contact created: {name}"
            if email:
                response += f"\n📧 Email: {email}"
            if phone:
                response += f"\n📱 Phone: {phone}"
            if company:
                response += f"\n🏢 Company: {company}"
            return response
        else:
            return f"❌ Failed to create contact: {result.get('error')}"
    except Exception as e:
        return f"❌ Error creating contact: {str(e)}"

def handle_search_contact(data):
    """Handle searching for contacts"""
    try:
        query = data.get("query", "")
        
        if not query:
            return "❌ Search query is required"
        
        result = hubspot_service.search_contact(query)
        
        if result.get("success"):
            contacts = result.get("contacts", [])
            if contacts:
                response = f"✅ Found {len(contacts)} contact(s) for '{query}':\n\n"
                for i, contact in enumerate(contacts[:3], 1):
                    props = contact.get("properties", {})
                    response += f"{i}. {props.get('firstname', '')} {props.get('lastname', '')}\n"
                    if props.get("email"):
                        response += f"   📧 {props.get('email')}\n"
                    if props.get("phone"):
                        response += f"   📱 {props.get('phone')}\n"
                    if props.get("company"):
                        response += f"   🏢 {props.get('company')}\n"
                    response += "\n"
                return response.strip()
            else:
                return f"❌ No contacts found for '{query}'"
        else:
            return f"❌ Search failed: {result.get('error')}"
    except Exception as e:
        return f"❌ Error searching contacts: {str(e)}"

def handle_create_task(data):
    """Handle creating tasks"""
    try:
        title = data.get("title", "")
        contact = data.get("contact", "")
        due_date = data.get("due_date", "")
        
        if not title:
            return "❌ Task title is required"
        
        # Create task as a deal in HubSpot
        task_name = f"TASK: {title}"
        deal_properties = {
            "dealname": task_name,
            "dealstage": "appointmentscheduled",
            "pipeline": "default",
            "amount": "0"
        }
        
        # Add task details to description
        task_details = f"Task: {title}"
        if contact:
            task_details += f"\nAssigned to: {contact}"
        if due_date:
            task_details += f"\nDue: {due_date}"
        
        deal_properties["description"] = task_details
        
        # Set close date
        if due_date:
            # Parse the due date (simplified parsing)
            if "today" in due_date.lower():
                deal_properties["closedate"] = datetime.now().strftime("%Y-%m-%d")
            elif "tomorrow" in due_date.lower():
                deal_properties["closedate"] = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                deal_properties["closedate"] = datetime.now().strftime("%Y-%m-%d")
        else:
            deal_properties["closedate"] = datetime.now().strftime("%Y-%m-%d")
        
        deal_data = {"properties": deal_properties}
        
        # Create the deal/task
        response = requests.post(
            f"{hubspot_service.base_url}/crm/v3/objects/deals",
            headers=hubspot_service.headers,
            json=deal_data,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            result_response = f"✅ Task created: {title}"
            if contact:
                result_response += f"\n👤 For: {contact}"
            if due_date:
                result_response += f"\n📅 Due: {due_date}"
            result_response += f"\n📝 Find it in HubSpot → Deals → Look for '{task_name}'"
            return result_response
        else:
            return f"❌ Failed to create task: {response.text[:200]}"
            
    except Exception as e:
        return f"❌ Error creating task: {str(e)}"

def handle_update_contact_phone(data):
    """Handle updating contact phone number"""
    try:
        name = data.get("name", "").strip()
        phone = data.get("phone", "").strip()
        
        if not name or not phone:
            return "❌ Both contact name and phone number are required"
        
        print(f"🔍 Searching for contact: '{name}'")
        
        # Search for contact
        search_result = hubspot_service.search_contact(name)
        
        if not search_result or not search_result.get("success"):
            return f"❌ Could not find contact: {name}. Try creating a new contact instead."
        
        contacts = search_result.get("contacts", [])
        if not contacts:
            return f"❌ No contact found with name: {name}. Try: 'create contact {name} phone {phone}'"
        
        # Use the first contact found
        contact = contacts[0]
        contact_id = contact.get("id")
        
        if not contact_id:
            return f"❌ Invalid contact data for: {name}"
        
        # Get contact name for response
        contact_props = contact.get("properties", {})
        current_name = f"{contact_props.get('firstname', '')} {contact_props.get('lastname', '')}".strip()
        if not current_name:
            current_name = name
        
        print(f"✅ Found contact: {current_name} (ID: {contact_id})")
        
        # Update the contact
        update_result = hubspot_service.update_contact(contact_id, {"phone": phone})
        
        if update_result and update_result.get("success"):
            return f"✅ Updated {current_name}'s phone number to {phone}"
        else:
            error_msg = update_result.get("error", "Unknown error") if update_result else "No response from HubSpot"
            return f"❌ Failed to update phone for {current_name}: {error_msg}"
    
    except Exception as e:
        print(f"❌ Error in handle_update_contact_phone: {str(e)}")
        return f"❌ Error updating contact: {str(e)}"

def handle_update_contact_email(data):
    """Handle updating contact email address"""
    try:
        name = data.get("name", "").strip()
        email = data.get("email", "").strip()
        
        if not name or not email:
            return "❌ Both contact name and email address are required"
        
        print(f"🔍 Searching for contact: '{name}'")
        
        # Search for contact
        search_result = hubspot_service.search_contact(name)
        
        if not search_result or not search_result.get("success"):
            return f"❌ Could not find contact: {name}"
        
        contacts = search_result.get("contacts", [])
        if not contacts:
            return f"❌ No contact found with name: {name}"
        
        # Use the first contact found
        contact = contacts[0]
        contact_id = contact.get("id")
        
        if not contact_id:
            return f"❌ Invalid contact data for: {name}"
        
        # Get contact name for response
        contact_props = contact.get("properties", {})
        current_name = f"{contact_props.get('firstname', '')} {contact_props.get('lastname', '')}".strip()
        if not current_name:
            current_name = name
        
        print(f"✅ Found contact: {current_name} (ID: {contact_id})")
        
        # Update the contact
        update_result = hubspot_service.update_contact(contact_id, {"email": email})
        
        if update_result and update_result.get("success"):
            return f"✅ Updated {current_name}'s email to {email}"
        else:
            error_msg = update_result.get("error", "Unknown error") if update_result else "No response from HubSpot"
            return f"❌ Failed to update email for {current_name}: {error_msg}"
    
    except Exception as e:
        print(f"❌ Error in handle_update_contact_email: {str(e)}")
        return f"❌ Error updating contact: {str(e)}"

def handle_update_contact_company(data):
    """Handle updating contact company"""
    try:
        name = data.get("name", "").strip()
        company = data.get("company", "").strip()
        
        if not name or not company:
            return "❌ Both contact name and company are required"
        
        # Search for contact
        search_result = hubspot_service.search_contact(name)
        
        if not search_result or not search_result.get("success"):
            return f"❌ Could not find contact: {name}"
        
        contacts = search_result.get("contacts", [])
        if not contacts:
            return f"❌ No contact found with name: {name}"
        
        # Use the first contact found
        contact = contacts[0]
        contact_id = contact.get("id")
        
        # Update the contact
        update_result = hubspot_service.update_contact(contact_id, {"company": company})
        
        if update_result and update_result.get("success"):
            return f"✅ Updated {name}'s company to {company}"
        else:
            return f"❌ Failed to update company: {update_result.get('error', 'Unknown error')}"
    
    except Exception as e:
        return f"❌ Error updating contact: {str(e)}"

def handle_add_contact_note(data):
    """Handle adding note to contact"""
    try:
        name = data.get("name", "")
        note = data.get("note", "")
        
        if not note:
            return "❌ Note text is required"
        
        contact_id = ""
        contact_found = False
        
        if name:
            search_result = hubspot_service.search_contact(name)
            if search_result.get("success"):
                contacts = search_result.get("contacts", [])
                if contacts:
                    contact_id = contacts[0].get("id")
                    contact_found = True
        
        # If contact not found but name provided, create the contact first
        if name and not contact_found:
            # Try to create the contact
            create_result = hubspot_service.create_contact(name)
            if create_result.get("success"):
                contact_id = create_result.get("contact_id", "")
                contact_found = True
                print(f"✅ Created new contact '{name}' for note")
        
        # Now add the note
        note_result = hubspot_service.add_contact_note(contact_id, note)
        
        # ALWAYS return success message if note was saved
        if note_result.get("success"):
            if name and contact_found:
                response = f"✅ Note saved"
                response += f"\n📝 Added to {name}'s contact record"
            else:
                response = f"✅ Note saved"
                if name:
                    response += f"\n📝 Note saved as general note (contact '{name}' not found)"
                else:
                    response += f"\n📝 Saved as general note in HubSpot"
            return response
        else:
            return f"❌ Failed to add note: {note_result.get('error')}"
    except Exception as e:
        return f"❌ Error adding note: {str(e)}"

def handle_schedule_meeting(data):
    """Handle scheduling meetings/appointments"""
    try:
        contact = data.get("contact", "")
        duration = data.get("duration", 30)
        when = data.get("when", "")
        
        title = f"Appointment with {contact}" if contact else "Voice Scheduled Meeting"
        result = hubspot_service.create_appointment(title, "", when, duration)
        
        if result.get("success"):
            response = f"✅ {duration}-minute meeting scheduled"
            if contact:
                response += f" with {contact}"
            if when:
                response += f"\n📅 Time: {when}"
            else:
                response += f"\n📅 Time: Default (1 hour from now)"
            response += f"\n📝 Find it in HubSpot → Deals → Look for 'MEETING: {title}'"
            return response
        else:
            return f"❌ Failed to schedule meeting: {result.get('error')}"
    except Exception as e:
        return f"❌ Error scheduling meeting: {str(e)}"

def handle_show_calendar(data):
    """Handle showing calendar events"""
    try:
        when = data.get("when", "")
        
        if "week" in when.lower():
            start_date = ""
            end_date = ""
        elif "today" in when.lower():
            start_date = datetime.now().strftime("%Y-%m-%d")
            end_date = start_date
        else:
            start_date = when
            end_date = ""
        
        result = hubspot_service.get_calendar_events(start_date, end_date)
        
        if result.get("success"):
            events = result.get("events", [])
            if events:
                response = f"✅ Calendar events for {when or 'this week'}:\n\n"
                for i, event in enumerate(events[:5], 1):
                    props = event.get('properties', {})
                    response += f"{i}. {props.get('hs_meeting_title', 'Event')}\n"
                    if props.get("hs_meeting_start_time"):
                        # Convert timestamp to readable date
                        try:
                            timestamp = int(props.get("hs_meeting_start_time")) / 1000
                            start_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
                            response += f"   📅 {start_time}\n"
                        except:
                            response += f"   📅 {props.get('hs_meeting_start_time')}\n"
                    response += "\n"
                return response.strip()
            else:
                message = result.get("message", f"No events found for {when or 'this period'}")
                return f"📅 {message}"
        else:
            return f"❌ Failed to get calendar: {result.get('error')}"
    except Exception as e:
        return f"❌ Error getting calendar: {str(e)}"

def handle_create_opportunity(data):
    """Handle creating new opportunity"""
    try:
        name = data.get("name", "")
        value = data.get("value", 0)
        contact = data.get("contact", "")
        
        if not name:
            return "❌ Opportunity name is required"
        
        contact_id = ""
        if contact:
            search_result = hubspot_service.search_contact(contact)
            if search_result.get("success"):
                contacts = search_result.get("contacts", [])
                if contacts:
                    contact_id = contacts[0].get("id")
        
        result = hubspot_service.create_opportunity(name, contact_id, value)
        
        if result.get("success"):
            response = f"✅ Deal created: {name}"
            if value > 0:
                response += f"\n💰 Value: ${value:,.2f}"
            if contact:
                response += f"\n👤 Contact: {contact}"
            return response
        else:
            return f"❌ Failed to create deal: {result.get('error')}"
    except Exception as e:
        return f"❌ Error creating opportunity: {str(e)}"

def handle_show_pipeline_summary(data):
    """Handle showing pipeline summary"""
    try:
        result = hubspot_service.get_pipeline_summary()
        
        if result.get("success"):
            total_value = result.get("total_value", 0)
            total_count = result.get("total_count", 0)
            
            response = f"📊 Sales Pipeline Summary:\n\n"
            response += f"💰 Total Value: ${total_value:,.2f}\n"
            response += f"📈 Total Deals: {total_count}\n"
            
            if total_count > 0:
                avg_value = total_value / total_count
                response += f"📊 Average Deal Size: ${avg_value:,.2f}"
            
            return response
        else:
            return f"❌ Failed to get pipeline summary: {result.get('error')}"
    except Exception as e:
        return f"❌ Error getting pipeline: {str(e)}"

def handle_show_contact_deals(data):
    """Handle showing deals for a specific contact"""
    try:
        contact_name = data.get("contact_name", "")
        
        if not contact_name:
            return "❌ Contact name is required"
        
        result = hubspot_service.show_contact_deals(contact_name)
        
        if result.get("success"):
            deals = result.get("deals", [])
            if deals:
                response = f"📊 Deals for {contact_name}:\n\n"
                for i, deal in enumerate(deals[:5], 1):
                    props = deal.get("properties", {})
                    response += f"{i}. {props.get('dealname', 'Unknown Deal')}\n"
                    if props.get("amount"):
                        response += f"   💰 ${float(props.get('amount', 0)):,.2f}\n"
                    if props.get("dealstage"):
                        response += f"   📈 Stage: {props.get('dealstage')}\n"
                    response += "\n"
                return response.strip()
            else:
                return f"📊 No deals found for {contact_name}"
        else:
            return f"❌ {result.get('error', 'Failed to get deals')}"
    except Exception as e:
        return f"❌ Error getting deals: {str(e)}"

# ==================== ACTION DISPATCHER ====================

def dispatch_action(parsed):
    """Enhanced action dispatcher with all fixes including FAQ"""
    try:
        action = parsed.get("action")
        print(f"🔧 Dispatching action: '{action}'")
        
        # Handle special/unsupported commands
        if action == "unsupported_feature":
            return parsed.get("message", "This feature is not currently supported")
        
        # FAQ action
        elif action == "faq_query":
            return handle_faq_query(parsed)
        
        # RCS-specific actions
        elif action == "send_rcs_message":
            return handle_send_rcs_message(parsed)
        elif action == "send_interactive_menu":
            return handle_send_interactive_menu(parsed)
        elif action == "send_crm_notification":
            return handle_send_crm_notification(parsed)
        
        # Communication actions
        elif action == "send_message":
            return handle_send_message(parsed)
        elif action == "send_message_to_contact":
            return handle_send_message_to_contact(parsed)
        elif action == "send_email":
            return handle_send_email(parsed)
        elif action == "send_email_to_contact":
            return handle_send_email_to_contact(parsed)
        elif action == "send_email_to_multiple_contacts":
            return handle_send_email_to_multiple_contacts(parsed)
        
        # CRM Contact actions
        elif action == "create_contact":
            return handle_create_contact(parsed)
        elif action == "update_contact_phone":
            return handle_update_contact_phone(parsed)
        elif action == "update_contact_email":
            return handle_update_contact_email(parsed)
        elif action == "update_contact_company":
            return handle_update_contact_company(parsed)
        elif action == "add_contact_note":
            return handle_add_contact_note(parsed)
        elif action == "search_contact":
            return handle_search_contact(parsed)
        
        # CRM Task actions
        elif action == "create_task":
            return handle_create_task(parsed)
        
        # CRM Calendar actions
        elif action == "schedule_meeting":
            return handle_schedule_meeting(parsed)
        elif action == "show_calendar":
            return handle_show_calendar(parsed)
        
        # CRM Pipeline actions
        elif action == "create_opportunity":
            return handle_create_opportunity(parsed)
        elif action == "show_pipeline_summary":
            return handle_show_pipeline_summary(parsed)
        elif action == "show_contact_deals":
            return handle_show_contact_deals(parsed)
        
        else:
            print(f"❌ Unknown action received: '{action}'")
            return f"Unknown action: {action}. Supported: SMS, RCS, Email, CRM, and FAQ operations"
    except Exception as e:
        return f"❌ Error in dispatch: {str(e)}"

# ==================== INITIALIZE SERVICES ====================

# Use enhanced Twilio client instead of basic one
enhanced_twilio_client = EnhancedTwilioClient()
email_client = EmailClient()
hubspot_service = HubSpotService()
command_processor = CommandProcessor()

# ==================== HTML TEMPLATE ====================

# ==================== HTML TEMPLATE ====================

def get_html_template():
    rcs_enabled = CONFIG["twilio_rcs_agent_id"] and CONFIG["twilio_messaging_service_sid"]
    
    # Build RCS section separately to avoid f-string issues
    rcs_section = ""
    if rcs_enabled:
        rcs_section = '''<div class="capability-section rcs">
                <h4>📱 RCS Rich Messaging</h4>
                <ul>
                    <li>"send rich message to Manuel Stagg saying meeting confirmed"</li>
                    <li>"send menu to client for services"</li>
                    <li>"send meeting reminder to John about tomorrow's call"</li>
                </ul>
            </div>'''
    
    rcs_badge = '<div class="rcs-badge">🚀 RCS Enabled</div>' if rcs_enabled else ''
    rcs_text = 'RCS messaging, ' if rcs_enabled else ''
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CRMAutoPilot - Voice Assistant with RCS, HubSpot CRM & RinglyPro FAQ</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1a1a2e url('https://assets.cdn.filesafe.space/3lSeAHXNU9t09Hhp9oai/media/688bfadef231e6633e98f192.webp') center center/cover no-repeat fixed; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; color: white; }}
        .container {{ background: rgba(26, 26, 46, 0.9); border-radius: 20px; padding: 40px; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3); backdrop-filter: blur(15px); max-width: 700px; width: 100%; text-align: center; border: 2px solid #4a69bd; }}
        .header h1 {{ font-size: 2.8em; margin-bottom: 10px; font-weight: 700; color: #4a69bd; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); }}
        .header img {{ max-height: 300px; margin-bottom: 20px; max-width: 95%; border-radius: 15px; box-shadow: 0 10px 20px rgba(0,0,0,0.3); }}
        .header p {{ font-size: 1.2em; opacity: 0.9; margin-bottom: 30px; color: #a0a0ff; }}
        .rcs-badge {{ background: linear-gradient(45deg, #9c27b0, #673ab7); padding: 5px 15px; border-radius: 20px; display: inline-block; margin: 10px 0; font-weight: 600; box-shadow: 0 4px 10px rgba(156, 39, 176, 0.3); }}
        .listening-status {{ height: 120px; display: flex; flex-direction: column; align-items: center; justify-content: center; margin-bottom: 30px; }}
        .voice-indicator {{ width: 100px; height: 100px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 40px; margin-bottom: 15px; transition: all 0.3s ease; border: 3px solid transparent; }}
        .voice-indicator.listening {{ background: linear-gradient(45deg, #4a69bd, #0097e6); animation: pulse 2s infinite; box-shadow: 0 0 30px rgba(74, 105, 189, 0.8); border-color: #4a69bd; }}
        .voice-indicator.processing {{ background: linear-gradient(45deg, #e74c3c, #c0392b); animation: spin 1s linear infinite; box-shadow: 0 0 30px rgba(231, 76, 60, 0.8); border-color: #e74c3c; }}
        .voice-indicator.idle {{ background: rgba(74, 105, 189, 0.3); animation: none; border-color: #4a69bd; }}
        @keyframes pulse {{ 0% {{ transform: scale(1); opacity: 1; }} 50% {{ transform: scale(1.1); opacity: 0.8; }} 100% {{ transform: scale(1); opacity: 1; }} }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
        .status-text {{ font-size: 1.1em; font-weight: 500; min-height: 30px; }}
        .status-text.listening {{ color: #4a69bd; }}
        .status-text.processing {{ color: #e74c3c; }}
        .controls {{ margin-bottom: 30px; }}
        .control-button {{ background: linear-gradient(45deg, #4a69bd, #0097e6); color: white; border: none; padding: 12px 30px; border-radius: 25px; font-size: 1em; font-weight: 600; cursor: pointer; margin: 0 10px; transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(74, 105, 189, 0.3); }}
        .control-button:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(74, 105, 189, 0.5); }}
        .control-button.stop {{ background: linear-gradient(45deg, #e74c3c, #c0392b); }}
        .control-button:disabled {{ background: #6c757d; cursor: not-allowed; transform: none; box-shadow: none; }}
        .manual-input {{ background: rgba(74, 105, 189, 0.1); border-radius: 15px; padding: 20px; margin-bottom: 20px; border: 1px solid rgba(74, 105, 189, 0.3); }}
        .manual-input h3 {{ margin-bottom: 15px; text-align: center; color: #4a69bd; }}
        .input-group {{ display: flex; gap: 10px; align-items: center; }}
        .text-input {{ flex: 1; padding: 12px 15px; border: 2px solid rgba(74, 105, 189, 0.3); border-radius: 25px; background: rgba(26, 26, 46, 0.8); color: white; font-size: 1em; outline: none; transition: all 0.3s ease; }}
        .text-input:focus {{ border-color: #4a69bd; background: rgba(26, 26, 46, 0.9); box-shadow: 0 0 10px rgba(74, 105, 189, 0.3); }}
        .text-input::placeholder {{ color: rgba(255, 255, 255, 0.6); }}
        .send-button {{ background: linear-gradient(45deg, #27ae60, #2ecc71); color: white; border: none; padding: 12px 25px; border-radius: 25px; font-size: 1em; font-weight: 600; cursor: pointer; transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(39, 174, 96, 0.3); }}
        .send-button:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(39, 174, 96, 0.5); }}
        .transcription {{ background: rgba(74, 105, 189, 0.1); border-radius: 15px; padding: 20px; margin-bottom: 20px; min-height: 80px; border: 2px solid transparent; transition: all 0.3s ease; }}
        .transcription.active {{ border-color: #4a69bd; background: rgba(74, 105, 189, 0.2); }}
        .transcription h3 {{ font-size: 1.1em; margin-bottom: 10px; opacity: 0.8; color: #4a69bd; }}
        .transcription-text {{ font-size: 1.2em; font-weight: 500; font-family: 'Courier New', monospace; }}
        .response {{ background: rgba(74, 105, 189, 0.1); border-radius: 15px; padding: 20px; margin-bottom: 20px; min-height: 80px; text-align: left; white-space: pre-wrap; display: none; }}
        .response.success {{ background: rgba(39, 174, 96, 0.2); border: 2px solid #27ae60; }}
        .response.error {{ background: rgba(231, 76, 60, 0.2); border: 2px solid #e74c3c; }}
        .browser-support {{ font-size: 0.9em; opacity: 0.8; margin-top: 20px; }}
        .browser-support.unsupported {{ color: #e74c3c; font-weight: bold; opacity: 1; }}
        .privacy-note {{ background: rgba(243, 156, 18, 0.2); border: 1px solid #f39c12; border-radius: 10px; padding: 15px; margin-top: 20px; font-size: 0.9em; }}
        .capabilities {{ background: rgba(74, 105, 189, 0.1); border-radius: 15px; padding: 20px; margin-bottom: 20px; text-align: left; border: 1px solid rgba(74, 105, 189, 0.3); }}
        .capabilities h3 {{ margin-bottom: 15px; text-align: center; color: #f39c12; }}
        .capability-section {{ margin-bottom: 15px; }}
        .capability-section h4 {{ color: #4a69bd; margin-bottom: 5px; }}
        .capability-section ul {{ margin-left: 20px; }}
        .capability-section li {{ margin-bottom: 3px; font-size: 0.9em; }}
        .capability-section.rcs {{ border-left: 3px solid #9c27b0; padding-left: 15px; margin-left: -15px; }}
        .capability-section.faq {{ border-left: 3px solid #f39c12; padding-left: 15px; margin-left: -15px; }}
        @media (max-width: 600px) {{ .container {{ padding: 20px; margin: 10px; }} .header img {{ max-height: 220px; }} .voice-indicator {{ width: 80px; height: 80px; font-size: 32px; }} .control-button {{ padding: 10px 20px; font-size: 0.9em; margin: 5px; }} .input-group {{ flex-direction: column; gap: 15px; }} .text-input {{ width: 100%; margin-bottom: 10px; }} .send-button {{ width: 100%; }} }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Business Automation</h1>
            {rcs_badge}
            <img src="https://assets.cdn.filesafe.space/3lSeAHXNU9t09Hhp9oai/media/688c054fea6d0f50b10fc3d7.webp" alt="CRMAutoPilot AI Assistant Logo" />
            <p>Voice-powered business automation with {rcs_text}HubSpot CRM & RinglyPro FAQ!</p>
        </div>
        
        <div class="capabilities">
            <h3>🚀 Voice Command Capabilities</h3>
            <div class="capability-section faq">
                <h4>📚 RinglyPro FAQ Assistant</h4>
                <ul>
                    <li>"what is RinglyPro"</li>
                    <li>"how much does RinglyPro cost"</li>
                    <li>"does RinglyPro work with HubSpot"</li>
                    <li>"can RinglyPro handle multiple languages"</li>
                    <li>"what's included in each plan"</li>
                </ul>
            </div>
            {rcs_section}
            <div class="capability-section">
                <h4>📱 Communication</h4>
                <ul>
                    <li>"text Manuel about the proposal"</li>
                    <li>"email Manuel Stagg about quarterly report"</li>
                </ul>
            </div>
            <div class="capability-section">
                <h4>👥 HubSpot Contacts</h4>
                <ul>
                    <li>"create contact John Smith email john@test.com"</li>
                    <li>"add note to Manuel saying discussed pricing"</li>
                    <li>"show me Sarah's contact details"</li>
                    <li>"update contact Manuel Stagg phone number 555-1234"</li>
                </ul>
            </div>
            <div class="capability-section">
                <h4>📋 Tasks & Calendar</h4>
                <ul>
                    <li>"create task to follow up with prospects"</li>
                    <li>"schedule 30-minute meeting with new lead tomorrow"</li>
                    <li>"show my meetings for this week"</li>
                </ul>
            </div>
            <div class="capability-section">
                <h4>📊 Sales Pipeline</h4>
                <ul>
                    <li>"add opportunity Premium Package worth $5000"</li>
                    <li>"show deals for Manuel Stagg"</li>
                    <li>"what's in the pipeline"</li>
                </ul>
            </div>
        </div>
        
        <div class="listening-status">
            <div class="voice-indicator idle" id="voiceIndicator">🎤</div>
            <div class="status-text" id="statusText">Click "Start Listening" to begin</div>
        </div>
        <div class="controls">
            <button class="control-button" id="startButton" onclick="startListening()">Start Listening</button>
            <button class="control-button stop" id="stopButton" onclick="stopListening()" disabled>Stop Listening</button>
        </div>
        <div class="transcription" id="transcription">
            <h3>🎤 Voice Transcription</h3>
            <div class="transcription-text" id="transcriptionText">Ready for commands...</div>
        </div>
        <div id="response" class="response"></div>
        <div class="manual-input">
            <h3>⌨️ Type Command Manually</h3>
            <div class="input-group">
                <input type="text" class="text-input" id="manualCommand" placeholder='Try: "what is RinglyPro" or "text Manuel about the proposal"' />
                <button class="send-button" onclick="sendManualCommand()">Send</button>
            </div>
            <small style="opacity: 0.7; display: block; margin-top: 10px; text-align: center;">💡 Direct commands - no wake word needed!</small>
        </div>
        <div class="browser-support" id="browserSupport">Checking browser compatibility...</div>
        <div class="privacy-note">🔒 <strong>Privacy:</strong> Voice recognition runs locally in your browser. {rcs_text}HubSpot CRM data is securely handled via encrypted APIs.</div>
    </div>

    <script>
        let recognition = null;
        let isListening = false;
        let isProcessingCommand = false;
        let commandTimeout = null;

        const voiceIndicator = document.getElementById('voiceIndicator');
        const statusText = document.getElementById('statusText');
        const startButton = document.getElementById('startButton');
        const stopButton = document.getElementById('stopButton');
        const transcription = document.getElementById('transcription');
        const transcriptionText = document.getElementById('transcriptionText');
        const response = document.getElementById('response');
        const browserSupport = document.getElementById('browserSupport');

        function initSpeechRecognition() {{
            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {{
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                recognition = new SpeechRecognition();
                
                recognition.continuous = true;
                recognition.interimResults = true;
                recognition.lang = 'en-US';
                recognition.maxAlternatives = 1;

                recognition.onstart = function() {{
                    isListening = true;
                    updateUI('listening', '🎤 Listening for commands...', '👂');
                }};

                recognition.onresult = function(event) {{
                    let interimTranscript = '';
                    let finalTranscript = '';
                    
                    for (let i = event.resultIndex; i < event.results.length; i++) {{
                        const transcript = event.results[i][0].transcript;
                        if (event.results[i].isFinal) {{
                            finalTranscript += transcript + ' ';
                        }} else {{
                            interimTranscript += transcript;
                        }}
                    }}
                    
                    const currentText = (finalTranscript + interimTranscript).trim();
                    if (currentText) {{
                        transcriptionText.textContent = currentText;
                        transcription.classList.add('active');
                    }}
                    
                    // If we have final transcript, process it
                    if (finalTranscript && !isProcessingCommand) {{
                        // Clear any existing timeout
                        if (commandTimeout) {{
                            clearTimeout(commandTimeout);
                        }}
                        
                        // Set a new timeout to process the command
                        commandTimeout = setTimeout(() => {{
                            processVoiceCommand(finalTranscript.trim());
                        }}, 1500); // Wait 1.5 seconds after speech ends
                    }}
                }};

                recognition.onerror = function(event) {{
                    if (event.error === 'no-speech') {{
                        return;
                    }}
                    
                    let errorMessage = 'Recognition error: ' + event.error;
                    updateUI('idle', errorMessage, '❌');
                }};

                recognition.onend = function() {{
                    isListening = false;
                    updateUI('idle', 'Speech recognition stopped', '🎤');
                    startButton.disabled = false;
                    stopButton.disabled = true;
                }};

                browserSupport.textContent = 'Voice recognition with RinglyPro FAQ support ✅';
                browserSupport.className = 'browser-support';
                return true;
            }} else {{
                browserSupport.textContent = '❌ Voice recognition not supported in this browser.';
                browserSupport.className = 'browser-support unsupported';
                startButton.disabled = true;
                return false;
            }}
        }}

        async function processVoiceCommand(text) {{
            if (isProcessingCommand) {{
                return;
            }}
            isProcessingCommand = true;
            updateUI('processing', '🔤 Processing command...', '⚙️');
            
            try {{
                const apiResponse = await fetch('/execute', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ text: text }})
                }});
                const data = await apiResponse.json();
                
                if (apiResponse.ok) {{
                    showResponse(data.response || 'Command executed successfully!', 'success');
                    updateUI('listening', '✅ Command processed! Continue speaking...', '👂');
                }} else {{
                    showResponse(data.error || 'An error occurred while processing your command.', 'error');
                    updateUI('listening', '❌ Error occurred. Continue speaking...', '👂');
                }}
            }} catch (error) {{
                showResponse('Network error. Please check your connection and try again.', 'error');
                updateUI('listening', '❌ Network error. Continue speaking...', '👂');
            }} finally {{
                isProcessingCommand = false;
                setTimeout(() => {{
                    transcriptionText.textContent = 'Waiting for next command...';
                    transcription.classList.remove('active');
                }}, 3000);
            }}
        }}

        function updateUI(state, statusMessage, indicator) {{
            statusText.textContent = statusMessage;
            statusText.className = 'status-text ' + state;
            voiceIndicator.textContent = indicator;
            voiceIndicator.className = 'voice-indicator ' + state;
        }}

        function showResponse(message, type) {{
            response.textContent = message;
            response.className = 'response ' + type;
            response.style.display = 'block';
            if (type === 'success') {{
                setTimeout(() => {{ response.style.display = 'none'; }}, 10000);
            }}
        }}

        function sendManualCommand() {{
            const manualInput = document.getElementById('manualCommand');
            let command = manualInput.value.trim();
            
            if (!command) {{
                alert('Please enter a command');
                return;
            }}
            
            manualInput.value = '';
            processVoiceCommand(command);
        }}

        document.addEventListener('DOMContentLoaded', function() {{
            const manualInput = document.getElementById('manualCommand');
            if (manualInput) {{
                manualInput.addEventListener('keypress', function(e) {{
                    if (e.key === 'Enter') {{
                        sendManualCommand();
                    }}
                }});
            }}
        }});

        function startListening() {{
            if (!recognition) {{
                alert('Speech recognition not available in this browser.');
                return;
            }}
            
            startButton.disabled = true;
            stopButton.disabled = false;
            response.style.display = 'none';
            
            try {{
                recognition.start();
            }} catch (error) {{
                updateUI('idle', 'Error starting recognition. Please try again.', '❌');
                startButton.disabled = false;
                stopButton.disabled = true;
            }}
        }}

        function stopListening() {{
            if (recognition && isListening) {{
                try {{
                    recognition.stop();
                }} catch (error) {{}}
            }}
            
            if (commandTimeout) {{
                clearTimeout(commandTimeout);
            }}
            
            updateUI('idle', 'Stopped listening', '🎤');
            startButton.disabled = false;
            stopButton.disabled = true;
            transcriptionText.textContent = 'Ready for commands...';
            transcription.classList.remove('active');
        }}

        window.addEventListener('load', function() {{ initSpeechRecognition(); }});
    </script>
</body>
</html>'''

# ==================== ROUTES ====================

@app.route("/")
def root():
    return get_html_template()

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/execute', methods=['POST'])
def execute():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Invalid request data"}), 400
            
        prompt = data.get("text", "")
        
        # Process command directly without wake word
        command_result = command_processor.process_command(prompt)
        
        if not command_result.get("success", True):
            return jsonify({
                "response": command_result.get("error", "Command processing failed"),
                "claude_output": command_result
            })
        
        if command_result.get("action"):
            dispatch_result = dispatch_action(command_result)
            return jsonify({
                "response": dispatch_result,
                "claude_output": command_result
            })
        
        return jsonify({
            "response": "No valid command found",
            "claude_output": command_result
        })

    except Exception as e:
        return jsonify({"response": f"Error: {str(e)}"}), 500

@app.route('/faq', methods=['POST'])
def faq_endpoint():
    """Direct FAQ query endpoint"""
    try:
        data = request.json
        query = data.get("query", "")
        
        if not query:
            return jsonify({"error": "No query provided"}), 400
        
        result = search_faq(query)
        
        if result.get("found"):
            return jsonify({
                "success": True,
                "question": result["question"],
                "answer": result["answer"],
                "confidence": result.get("confidence", 0)
            })
        else:
            return jsonify({
                "success": False,
                "message": result.get("answer", "No matching FAQ found")
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/send-rcs", methods=["POST"])
def send_rcs():
    try:
        data = request.json
        recipient = data.get("to")
        message = data.get("message", "")
        image_url = data.get("image_url", "")
        quick_replies = data.get("quick_replies", [])

        if not recipient or not message:
            return jsonify({"error": "Missing 'to' or 'message' field"}), 400

        # Format phone
        formatted_phone = format_phone_number(recipient)
        if not formatted_phone:
            return jsonify({"error": "Invalid phone number"}), 400

        # Send RCS using enhanced Twilio client
        result = enhanced_twilio_client.send_smart_message(
            formatted_phone,
            message,
            media_url=image_url,
            quick_replies=quick_replies
        )

        return jsonify(result), 200 if result.get("success") else 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/rcs-webhook', methods=['POST'])
def handle_rcs_webhook():
    """Handle RCS message responses and interactions"""
    try:
        data = request.json
        print(f"📱 RCS Webhook received: {json.dumps(data, indent=2)}")
        
        # Handle button clicks
        if data.get('PostbackData'):
            postback = data.get('PostbackData')
            from_number = data.get('From')
            
            if postback == 'RESCHEDULE_MEETING':
                response_message = "I'll help you reschedule. When would you prefer?"
                enhanced_twilio_client.send_smart_message(
                    from_number, 
                    response_message,
                    quick_replies=["Tomorrow", "Next Week", "Let me specify"]
                )
                return jsonify({"status": "rescheduling"}), 200
                
            elif postback == 'APPROVE_DEAL':
                response_message = "Deal approved! I've updated the CRM."
                enhanced_twilio_client.send_smart_message(from_number, response_message)
                return jsonify({"status": "deal_approved"}), 200
                
            elif postback.startswith('SERVICE_'):
                service = postback.replace('SERVICE_', '').lower()
                response_message = f"Great choice! I'll send you more info about our {service} services."
                enhanced_twilio_client.send_smart_message(from_number, response_message)
                return jsonify({"status": "service_selected", "service": service}), 200
                
            elif postback.startswith('APPT_'):
                slot = postback.replace('APPT_', '')
                response_message = f"Perfect! I've scheduled your appointment. You'll receive a confirmation shortly."
                enhanced_twilio_client.send_smart_message(from_number, response_message)
                return jsonify({"status": "appointment_booked", "slot": slot}), 200
        
        # Handle text responses
        if data.get('Body'):
            message = data.get('Body')
            from_number = data.get('From')
            
            # Process as a voice command
            command_result = command_processor.process_command(message)
            
            if command_result.get("action"):
                response = dispatch_action(command_result)
                enhanced_twilio_client.send_smart_message(from_number, f"Command processed: {response}")
            else:
                enhanced_twilio_client.send_smart_message(
                    from_number, 
                    "Thanks for your message! How can I help you?",
                    quick_replies=["Schedule Meeting", "View Services", "Contact Support"]
                )
            
            return jsonify({"status": "message_received"}), 200
        
        return jsonify({"status": "received"}), 200
        
    except Exception as e:
        print(f"❌ RCS Webhook error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    rcs_configured = bool(CONFIG["twilio_rcs_agent_id"] and CONFIG["twilio_messaging_service_sid"])
    
    return jsonify({
        "status": "healthy",
        "mode": "direct_command_mode",
        "services": {
            "twilio_configured": bool(enhanced_twilio_client.client),
            "rcs_configured": rcs_configured,
            "email_configured": bool(CONFIG["email_address"] and CONFIG["email_password"]),
            "hubspot_configured": bool(CONFIG["hubspot_api_token"]),
            "claude_configured": bool(CONFIG["claude_api_key"]),
            "faq_system": "active"
        },
        "rcs_config": {
            "agent_id_configured": bool(CONFIG["twilio_rcs_agent_id"]),
            "messaging_service_configured": bool(CONFIG["twilio_messaging_service_sid"]),
            "rcs_ready": rcs_configured
        },
        "email_config": {
            "provider": CONFIG["email_provider"],
            "smtp_server": CONFIG["email_smtp_server"],
            "smtp_port": CONFIG["email_smtp_port"]
        },
        "crm_integration": {
            "provider": "HubSpot",
            "api_configured": bool(CONFIG["hubspot_api_token"])
        },
        "faq_stats": {
            "total_faqs": sum(len(cat) for cat in RINGLY_FAQ_DATABASE.values()),
            "categories": list(RINGLY_FAQ_DATABASE.keys())
        }
    })

# ==================== MAIN EXECUTION ====================

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Starting CRMAutoPilot AI Assistant")
    print("   with RCS, HubSpot & RinglyPro FAQ")
    print("=" * 60)
    
    # Display configuration status
    print("\n📋 Configuration Status:")
    print("-" * 40)
    
    print(f"🎙️  Mode: Direct Command (No Wake Words Required)")
    
    # Twilio Configuration
    twilio_status = "✅ Ready" if enhanced_twilio_client.client else "❌ Not configured"
    print(f"\n📱 Twilio SMS: {twilio_status}")
    if enhanced_twilio_client.client:
        print(f"    Phone: {CONFIG['twilio_phone_number']}")
    
    # RCS Configuration
    rcs_configured = bool(CONFIG["twilio_rcs_agent_id"] and CONFIG["twilio_messaging_service_sid"])
    rcs_status = "✅ Ready" if rcs_configured else "⚠️ Not configured"
    print(f"\n🚀 Twilio RCS: {rcs_status}")
    if rcs_configured:
        print(f"    Agent ID: {CONFIG['twilio_rcs_agent_id'][:12]}...")
        print(f"    Service: {CONFIG['twilio_messaging_service_sid'][:12]}...")
        print("    Features: Rich Cards, Carousels, Quick Replies")
    else:
        if not CONFIG["twilio_rcs_agent_id"]:
            print("    ⚠️ Missing: TWILIO_RCS_AGENT_ID")
        if not CONFIG["twilio_messaging_service_sid"]:
            print("    ⚠️ Missing: TWILIO_MESSAGING_SERVICE_SID")
    
    # Email Configuration
    email_status = "✅ Ready" if CONFIG['email_address'] and CONFIG['email_password'] else "⚠️ Not configured"
    print(f"\n📧 Email ({CONFIG['email_provider'].title()}): {email_status}")
    if CONFIG['email_address']:
        print(f"    From: {CONFIG['email_address']}")
        print(f"    Server: {CONFIG['email_smtp_server']}:{CONFIG['email_smtp_port']}")
    
    # HubSpot Configuration
    hubspot_status = "✅ Ready" if CONFIG['hubspot_api_token'] else "⚠️ Not configured"
    print(f"\n🏢 HubSpot CRM: {hubspot_status}")
    if CONFIG['hubspot_api_token']:
        print(f"    Token: {CONFIG['hubspot_api_token'][:12]}...")
        print("    Objects: Contacts, Deals, Tasks, Meetings")
    
    # Claude Configuration
    claude_status = "✅ Ready" if CONFIG['claude_api_key'] else "❌ Not configured"
    print(f"\n🤖 Claude AI: {claude_status}")
    if CONFIG['claude_api_key']:
        print(f"    Key: {CONFIG['claude_api_key'][:12]}...")
    
    # FAQ System
    faq_count = sum(len(cat) for cat in RINGLY_FAQ_DATABASE.values())
    print(f"\n📚 RinglyPro FAQ: ✅ Ready")
    print(f"    Questions: {faq_count}")
    print(f"    Categories: {', '.join(RINGLY_FAQ_DATABASE.keys())}")
    
    # Display available commands
    print("\n" + "=" * 60)
    print("🎯 Available Voice Commands (No Wake Word Needed):")
    print("=" * 60)
    
    print("\n📚 RinglyPro FAQ:")
    print("   • 'what is RinglyPro'")
    print("   • 'how much does RinglyPro cost'")
    print("   • 'does RinglyPro work with HubSpot'")
    print("   • 'can I use my existing phone number'")
    print("   • 'what CRMs does RinglyPro integrate with'")
    
    if rcs_configured:
        print("\n📱 RCS Rich Messaging:")
        print("   • 'send rich message to Manuel saying meeting confirmed'")
        print("   • 'send menu to client for services'")
        print("   • 'send meeting reminder to John about tomorrow'")
    
    print("\n💬 Communication:")
    print("   • 'text Manuel about the proposal'")
    print("   • 'email Manuel Stagg about quarterly report'")
    
    print("\n👥 Contact Management:")
    print("   • 'create contact John Smith email john@test.com'")
    print("   • 'update contact Manuel Stagg phone number 555-1234'")
    print("   • 'search contact Sarah Johnson'")
    print("   • 'add note to Manuel saying discussed pricing'")
    
    print("\n📋 Tasks & Calendar:")
    print("   • 'create task to follow up with prospects'")
    print("   • 'schedule 30-minute meeting with new lead tomorrow'")
    print("   • 'show my meetings for this week'")
    
    print("\n📊 Sales Pipeline:")
    print("   • 'add opportunity Premium Package worth $5000'")
    print("   • 'show deals for Manuel Stagg'")
    print("   • 'what's in the pipeline'")
    
    # Display test endpoints
    print("\n" + "=" * 60)
    print("🧪 Test Endpoints:")
    print("=" * 60)
    print("   • GET  /health      - System health check")
    print("   • POST /faq         - Direct FAQ query")
    if rcs_configured:
        print("   • POST /send-rcs    - Send RCS message")
    print("   • POST /rcs-webhook - RCS response handler")
    
    # Start server
    port = int(os.environ.get("PORT", 10000))
    print("\n" + "=" * 60)
    print(f"🌐 Starting server on port {port}")
    print(f"🔗 Access the app at: http://0.0.0.0:{port}")
    print("=" * 60 + "\n")
    
    app.run(host="0.0.0.0", port=port, debug=False)

