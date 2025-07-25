"""
Speech-Optimized Claude Response Generation
Fixed version with safe Anthropic client initialization
"""

import logging
import os
from typing import Dict, Any

# Initialize Claude client safely
claude_client = None
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

if anthropic_api_key:
    try:
        import anthropic
        claude_client = anthropic.Anthropic(api_key=anthropic_api_key)
        logging.info("✅ Claude API client initialized successfully")
    except Exception as e:
        logging.error(f"❌ Claude API client initialization failed: {e}")
        claude_client = None
else:
    logging.error("❌ ANTHROPIC_API_KEY not found in environment variables")

class SpeechOptimizedClaude:
    def __init__(self):
        self.model = "claude-sonnet-4-20250514"
        self.max_tokens_by_context = {
            "empathetic": 180,     # Allow more words for caring responses
            "professional": 150,   # Concise but complete
            "excited": 120,        # Quick, energetic responses
            "calm": 160,          # Detailed but measured
            "neutral": 140        # Standard length
        }
        
    def get_context_specific_prompt(self, context: str) -> str:
        """Get system prompt optimized for specific emotional context"""
        
        base_prompt = """You are RinglyPro AI, speaking directly to someone on a phone call. 

CRITICAL: Write EXACTLY how you want to sound when spoken aloud. This will be converted to speech.

Core personality:
- Sound like a knowledgeable friend, not a corporate robot
- Be genuinely helpful and emotionally aware
- Use natural conversation patterns with rhythm and flow

SPEECH RULES (MANDATORY):
- Always use contractions (can't, won't, I'm, you're, that's, etc.)
- Keep responses under 60 words for phone conversations
- Use natural verbal transitions ("So," "Actually," "Here's the thing," "You know what?")
- Include small acknowledgments ("Right," "Exactly," "Absolutely," "I hear you")
- End with engagement when appropriate ("Does that help?" "What do you think?")
- Avoid written language patterns - write for speaking, not reading

About RinglyPro:
- AI business assistant for solo professionals and service businesses
- 24/7 phone answering, scheduling, and lead management  
- Bilingual support, calendar integration, automated follow-ups
- Built for contractors, realtors, wellness providers, service professionals"""

        context_prompts = {
            "empathetic": """
EMOTIONAL CONTEXT: The caller seems frustrated, confused, or needs extra support.

Tone Guidelines:
- Speak with genuine warmth and understanding
- Use a slower, more deliberate pace
- Include verbal empathy: "I hear you," "That totally makes sense," "I understand"
- Add reassuring phrases: "Don't worry," "We'll figure this out," "I'm here to help"
- Use softer language: "absolutely" instead of "yes," "totally understand" instead of "understand"
- End with comfort: "I'm here to help you through this" or "We've got your back"

Example tone: "I totally hear you, and that sounds really frustrating. Don't worry though - I can definitely help you sort that out. What's been happening?"
            """,
            
            "professional": """
EMOTIONAL CONTEXT: Business inquiry requiring confident, authoritative information.

Tone Guidelines:
- Sound confident and knowledgeable without being cold
- Use clear, decisive language
- Include credibility phrases: "What I can tell you is," "Here's how it works," "In my experience"
- Emphasize key benefits naturally
- Add forward momentum: "Here's what we can do," "The next step would be"
- End with action: "Would you like me to set that up?" or "What questions do you have?"

Example tone: "Absolutely! So here's how our scheduling works - it syncs directly with your calendar and handles everything automatically. Pretty efficient, right? What would you like to know about that?"
            """,
            
            "excited": """
EMOTIONAL CONTEXT: Positive interaction where enthusiasm is appropriate.

Tone Guidelines:
- Match their energy with genuine enthusiasm
- Use upbeat, energetic phrasing
- Include excitement words: "fantastic," "amazing," "perfect," "love that"
- Vary your rhythm - some quick phrases, some emphasized
- Build momentum throughout the response
- End with continued excitement: "This is going to be great!" or "You're going to love this!"

Example tone: "Oh, that's fantastic! I absolutely love helping with that. You're going to be amazed at how much smoother everything runs. What else would you like to know?"
            """,
            
            "calm": """
EMOTIONAL CONTEXT: Informational request requiring steady, clear explanation.

Tone Guidelines:
- Use measured, steady pacing
- Break information into digestible pieces
- Include organizing phrases: "First," "Additionally," "Most importantly"
- Add clarifying language: "In other words," "What this means is," "Basically"
- Maintain warm professionalism
- End with helpful follow-up: "Does that make sense?" or "What else can I explain?"

Example tone: "Sure, let me explain that. Basically, when someone calls, I answer immediately and can handle their questions or book appointments. Everything gets organized automatically. Does that help clarify things?"
            """,
            
            "neutral": """
EMOTIONAL CONTEXT: Standard interaction requiring friendly professionalism.

Tone Guidelines:
- Balance warmth with efficiency
- Use natural, conversational flow
- Include friendly transitions: "So," "Actually," "Here's what's great"
- Add engagement: "Right?" "Make sense?" "You know?"
- Keep it moving forward
- End with helpful offer: "What else can I help with?" or "Any other questions?"

Example tone: "Hey there! So basically, I'm your AI assistant and I handle all your business calls and scheduling. Pretty convenient, right? What would you like to know more about?"
            """
        }
        
        return base_prompt + "\n\n" + context_prompts.get(context, context_prompts["neutral"])

    def post_process_response(self, response: str, context: str) -> str:
        """Final optimization of Claude's response for speech"""
        
        # Remove written artifacts that don't work in speech
        response = response.replace('"', '')
        response = response.replace('*', '')  # Remove emphasis markers
        response = response.replace('(', '... ')
        response = response.replace(')', ' ...')
        
        # Add natural speech patterns
        if not any(response.lower().startswith(starter) for starter in ['so,', 'well,', 'hey,', 'oh,', 'actually,']):
            # Add natural conversation starter based on context
            starters = {
                "empathetic": "Oh, ",
                "professional": "So, ",
                "excited": "Oh wow, ",
                "calm": "Sure, ",
                "neutral": "Hey, "
            }
            response = starters.get(context, "So, ") + response.lower()[0] + response[1:]
        
        # Ensure natural ending
        if not response.endswith(('?', '!', '.')):
            response += "."
        
        # Context-specific final touches
        if context == "empathetic" and not any(phrase in response.lower() for phrase in ['understand', 'hear you', 'help']):
            response += " I'm here to help you with this."
            
        elif context == "excited" and not response.endswith('!'):
            response = response.rstrip('.') + "!"
        
        return response.strip()

    async def generate_speech_response(self, user_message: str, context: str = "neutral", language: str = "english") -> str:
        """Generate optimized response for speech synthesis"""
        
        if not claude_client:
            logging.error("Claude client not available")
            # Return context-appropriate fallback
            fallbacks = {
                "empathetic": "I'm really sorry, I'm having a technical moment right now. But I'm still here to help you - could you try asking me again?",
                "professional": "I apologize, but I'm experiencing a brief technical issue. Please give me just a moment and try again.",
                "excited": "Oh no! I'm having a little technical hiccup right now. But don't worry - try me again in just a second!",
                "calm": "I'm having a technical issue at the moment. Please try your question again, and I'll be right back with you.",
                "neutral": "Sorry, I had a technical glitch there. Could you try asking that again?"
            }
            return fallbacks.get(context, fallbacks["neutral"])
        
        try:
            # Get context-specific system prompt
            system_prompt = self.get_context_specific_prompt(context)
            
            # Add language instruction
            language_instruction = ""
            if language.lower().startswith('es'):
                language_instruction = "Respond in Spanish. Use natural Spanish conversation patterns and contractions."
            else:
                language_instruction = "Respond in English using natural American conversation patterns."
            
            # Generate response
            message = claude_client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens_by_context.get(context, 140),
                temperature=0.9,  # Higher for more natural variation
                system=system_prompt + f"\n\nLanguage: {language_instruction}",
                messages=[
                    {
                        "role": "user",
                        "content": f"User just said: \"{user_message}\"\n\nRespond naturally as if you're having a phone conversation with them. Remember to keep it conversational and under 60 words."
                    }
                ]
            )
            
            response_text = message.content[0].text.strip()
            
            # Post-process for speech optimization
            optimized_response = self.post_process_response(response_text, context)
            
            # Final length check for phone conversations
            if len(optimized_response.split()) > 70:
                # Truncate but keep it natural
                words = optimized_response.split()
                optimized_response = ' '.join(words[:65]) + "..."
                logging.warning(f"Response truncated for speech length: {len(words)} words")
            
            logging.info(f"Generated {context} response: {len(optimized_response.split())} words")
            return optimized_response
            
        except Exception as e:
            logging.error(f"Claude speech generation error: {e}")
            
            # Context-appropriate fallback responses
            fallbacks = {
                "empathetic": "I'm really sorry, I'm having a technical moment right now. But I'm still here to help you - could you try asking me again?",
                "professional": "I apologize, but I'm experiencing a brief technical issue. Please give me just a moment and try again.",
                "excited": "Oh no! I'm having a little technical hiccup right now. But don't worry - try me again in just a second!",
                "calm": "I'm having a technical issue at the moment. Please try your question again, and I'll be right back with you.",
                "neutral": "Sorry, I had a technical glitch there. Could you try asking that again?"
            }
            
            return fallbacks.get(context, fallbacks["neutral"])

# Global instance
speech_claude = SpeechOptimizedClaude()

def get_enhanced_claude_response(user_message: str, context: str = "neutral", language: str = "english") -> str:
    """
    Compatibility function for existing code
    """
    import asyncio
    
    try:
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(
            speech_claude.generate_speech_response(user_message, context, language)
        )
        loop.close()
        return response
    except Exception as e:
        logging.error(f"Enhanced Claude response error: {e}")
        return "Sorry, I had a technical issue. Please try again."
