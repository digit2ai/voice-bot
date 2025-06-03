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
    # English
    "what is tampalawnpro": (
        "TampaLawnPro is an AI-powered lawn care platform based in Wesley Chapel, Florida. It helps homeowners get instant lawn quotes using satellite imagery, "
        "and supports lawn pros with tools for automation, client management, and marketing."
    ),
    "how do instant quotes work": (
        "Just enter your address, and TampaLawnPro uses satellite imagery and AI to instantly measure your lawn and generate a personalized quote—no site visit needed."
    ),
    "can i book lawn care online": (
        "Yes. You can book your lawn services online quickly and securely from your phone or computer."
    ),
    "are the providers local": (
        "Yes. TampaLawnPro connects you with vetted, local lawn care professionals in the Tampa Bay area."
    ),
    "what tools do lawn pros get": (
        "Lawn pros get a dashboard with online booking, CRM, mobile app, invoicing, QuickBooks integration, marketing automation, landing pages, and more."
    ),
    "how much does it cost for pros": (
        "Plans start at $97/month for scheduling, $297/month for business tools and SEO, and $497/month for full marketing automation including Google Ads and analytics."
    ),
    "is there a free trial": (
        "Yes, there's a 30-day risk-free trial with a money-back guarantee for lawn pros."
    ),
    "where is tampalawnpro based": (
        "TampaLawnPro is based in Wesley Chapel, Florida and serves the greater Tampa Bay area."
    ),

    # Spanish
    "que es tampalawnpro": (
        "TampaLawnPro es una plataforma de jardinería impulsada por inteligencia artificial con sede en Wesley Chapel, Florida. "
        "Ayuda a propietarios a obtener cotizaciones instantáneas con imágenes satelitales y permite a los profesionales del césped automatizar sus servicios y atraer más clientes."
    ),
    "como funciona la cotización instantanea": (
        "Solo ingresa tu dirección y TampaLawnPro usa imágenes satelitales e inteligencia artificial para medir tu jardín y darte una cotización personalizada al instante."
    ),
    "puedo reservar servicios en linea": (
        "Sí. Puedes reservar servicios de jardinería en línea de forma rápida y segura desde tu celular o computadora."
    ),
    "los proveedores son locales": (
        "Sí. TampaLawnPro te conecta con profesionales verificados y confiables en el área de Tampa Bay."
    ),
    "que herramientas tienen los profesionales": (
        "Los profesionales tienen acceso a un panel con funciones como programación, CRM, app móvil, facturación, integración con QuickBooks, páginas de aterrizaje y automatización de marketing."
    ),
    "cuanto cuesta para los profesionales": (
        "Desde $97/mes para programación, $297/mes con herramientas de negocio y SEO, y $497/mes para marketing completo con anuncios y reportes."
    ),
    "ofrecen prueba gratuita": (
        "Sí, hay una prueba gratuita de 30 días con garantía de devolución de dinero para profesionales del césped."
    ),
    "donde estan ubicados": (
        "TampaLawnPro está ubicado en Wesley Chapel, Florida, y atiende toda el área de Tampa Bay."
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
