from flask import Flask, request, send_file
from flask_cors import CORS
import openai
import os
import tempfile
import logging
from dotenv import load_dotenv
from difflib import get_close_matches

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Setup Flask
app = Flask(__name__, static_folder='static')
CORS(app)

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# FAQ dictionary (shortened for example)
FAQ_BRAIN = {
    "what is tampalawnpro": (
        "TampaLawnPro is an AI-powered lawn care platform based in Wesley Chapel, Florida, designed to help homeowners get instant lawn quotes and "
        "enable lawn care professionals to grow their businesses using automation. Homeowners can receive satellite-based quotes, book services online, "
        "and connect with trusted local pros. Lawn pros get tools to manage jobs, automate client communication, and run marketing campaigns."
    ),
    "que es tampalawnpro": (
        "TampaLawnPro es una plataforma de cuidado del césped impulsada por inteligencia artificial, con sede en Wesley Chapel, Florida. "
        "Ayuda a los propietarios a obtener cotizaciones instantáneas usando imágenes satelitales y a reservar servicios en línea. "
        "Los profesionales del césped pueden automatizar sus operaciones, gestionar clientes y hacer crecer su negocio."
    ),
    "how do instant quotes work": (
        "Just enter your address, and TampaLawnPro uses satellite imagery and AI to instantly measure your lawn and generate a personalized quote—"
        "no site visit needed."
    ),
    "can i book lawn care online": (
        "Yes. Homeowners can schedule lawn services quickly and securely online, from their phone or computer."
    ),
    "are the providers local": (
        "Yes. TampaLawnPro connects homeowners with vetted, trusted local lawn care professionals in the Tampa Bay area."
    ),
    "what tools do lawn pros get": (
        "Lawn care businesses get a complete suite of tools including online booking, a mobile app, automated reminders, CRM, invoicing, QuickBooks integration, "
        "local SEO, landing pages, and marketing automation features like email campaigns and lead follow-up."
    ),
    "how much does it cost for pros": (
        "Plans start at $97/month for scheduling tools, $297/month for business operations and marketing setup, and $497/month for full marketing automation including "
        "Google Ads, reputation management, and monthly analytics."
    ),
    "is there a free trial": (
        "Yes. TampaLawnPro offers a 30-day risk-free trial with a full money-back guarantee for lawn care professionals."
    ),
    "where is tampalawnpro based": (
        "TampaLawnPro is proudly based in Wesley Chapel, Florida, serving homeowners and lawn pros across the greater Tampa Bay area."
    )
}

@app.route('/')
def serve_index():
    return app.send_static_file("index.html")

@app.route('/process-audio', methods=['POST'])
def process_audio():
    logging.info("📥 Received audio request")

    audio_file = request.files.get("file")
    if not audio_file:
        logging.error("❌ No audio file found in request")
        return "Missing audio", 400

    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
        audio_file.save(temp_audio.name)
        logging.info(f"✅ Saved uploaded audio to: {temp_audio.name}")

    # Step 1: Transcription
    try:
        with open(temp_audio.name, "rb") as f:
            transcript = openai.audio.transcriptions.create(
                model="whisper-1",
                file=f
            ).text.lower()
        logging.info(f"📝 Transcript: {transcript}")
    except Exception as e:
        logging.error(f"❌ Transcription error: {e}")
        return send_file("static/test.mp3", mimetype="audio/mpeg")

    # Step 2: Match against FAQ
    matched = get_close_matches(transcript, FAQ_BRAIN.keys(), n=1, cutoff=0.7)
    if matched:
        response = FAQ_BRAIN[matched[0]]
        logging.info(f"🤖 Matched FAQ: {matched[0]}")
    else:
        # Fallback to GPT
        try:
            completion = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are Lina, a friendly assistant for lawn care."},
                    {"role": "user", "content": transcript}
                ]
            )
            response = completion.choices[0].message.content
            logging.info(f"💬 GPT Response: {response}")
        except Exception as e:
            logging.error(f"❌ GPT fallback error: {e}")
            return send_file("static/test.mp3", mimetype="audio/mpeg")

    # Step 3: Convert to Speech
    try:
        speech = openai.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=response
        )
        logging.info("🔊 TTS conversion successful")
    except Exception as e:
        logging.error(f"❌ TTS error: {e}")
        return send_file("static/test.mp3", mimetype="audio/mpeg")

    # Step 4: Serve MP3
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as out_audio:
            out_audio.write(speech.content)
            out_audio.flush()
            os.fsync(out_audio.fileno())
            file_size = os.path.getsize(out_audio.name)
            logging.info(f"📁 MP3 file size: {file_size} bytes")

            if file_size < 1000:
                logging.warning("⚠️ MP3 file too small — returning fallback")
                return send_file("static/test.mp3", mimetype="audio/mpeg")

            return send_file(out_audio.name, mimetype="audio/mpeg", download_name="response.mp3")

    except Exception as e:
        logging.error(f"❌ Error sending audio file: {e}")
        return send_file("static/test.mp3", mimetype="audio/mpeg")

if __name__ == "__main__":
    app.run(debug=True)
