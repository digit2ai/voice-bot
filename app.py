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
    # What is it?
    "¿Qué es TampaLawnPro?": (
        "TampaLawnPro es una plataforma inteligente basada en IA que ayuda a propietarios y empresas de jardinería en Tampa Bay a obtener cotizaciones instantáneas, programar servicios y automatizar la gestión de su negocio."
    ),
    "What is TampaLawnPro?": (
        "TampaLawnPro is an AI-powered platform that helps homeowners and lawn care businesses in Tampa Bay get instant quotes, schedule services, and automate operations."
    ),

    # How to get started
    "¿Cómo empiezo?": (
        "Puedes comenzar visitando el sitio web de TampaLawnPro. Selecciona el plan que más te convenga, haz clic en 'Empezar ahora' y sigue los pasos para registrarte. También puedes agendar una demostración si prefieres ver cómo funciona antes de inscribirte."
    ),
    "How do I get started?": (
        "You can get started by visiting the TampaLawnPro website. Choose the plan that fits your needs, click 'Get Started', and follow the steps to register. You can also schedule a demo if you'd like to see how it works first."
    ),

    # How to use it
    "¿Cómo puedo usar TampaLawnPro?": (
        "Si eres propietario, solo ingresa tu dirección en el sitio web para obtener una cotización instantánea y agendar servicios. "
        "Si eres profesional del césped, puedes suscribirte a uno de los planes mensuales para gestionar reservas, automatizar mensajes, y recibir soporte personalizado."
    ),
    "How do I use TampaLawnPro?": (
        "If you're a homeowner, just enter your address on the website to get an instant quote and book a service. "
        "If you're a lawn care pro, you can subscribe to one of the monthly plans to manage bookings, automate messages, and receive personalized support."
    ),

    # Demo
    "¿Cómo hago para una demostración?": (
        "Puedes solicitar una demostración directamente desde el sitio web seleccionando una fecha en el calendario. Un miembro del equipo te guiará en una videollamada para mostrarte cómo funciona la plataforma paso a paso."
    ),
    "How do I book a demo?": (
        "You can book a demo directly on the website by selecting a date from the calendar. A team member will guide you step-by-step through the platform in a video call."
    ),

    # Purchase
    "¿Cómo lo compro?": (
        "Puedes comprar un plan directamente desde el sitio web. Solo elige el plan que mejor se adapte a tu negocio, haz clic en 'Empezar' o 'Suscribirse', y sigue los pasos para registrarte y realizar el pago en línea de forma segura."
    ),
    "How do I buy it?": (
        "You can purchase a plan directly from the website. Just choose the plan that fits your needs, click 'Start' or 'Subscribe', and follow the secure checkout process."
    ),

    # Signup
    "¿Cómo me inscribo?": (
        "Para inscribirte, visita el sitio web de TampaLawnPro, selecciona un plan, haz clic en 'Empezar ahora' y completa el formulario con tus datos. El proceso es rápido y 100% en línea."
    ),
    "How do I sign up?": (
        "To sign up, visit the TampaLawnPro website, select a plan, click 'Get Started' and complete the form with your information. The process is quick and fully online."
    ),

    # Purpose
    "¿Cuál es el objetivo de TampaLawnPro?": (
        "TampaLawnPro es una plataforma todo-en-uno diseñada para automatizar cotizaciones, reservas y la gestión de servicios de jardinería."
    ),
    "What is the purpose of TampaLawnPro?": (
        "TampaLawnPro is an all-in-one platform built to automate quoting, scheduling, and business management for lawn care services."
    ),

    # Target audience
    "¿Quiénes pueden usar TampaLawnPro?": (
        "Está diseñada tanto para propietarios de viviendas como para empresas de cuidado de césped en el área de Tampa Bay."
    ),
    "Who can use TampaLawnPro?": (
        "It’s built for both homeowners and lawn care professionals in the Tampa Bay area."
    ),

    # Plans
    "¿Qué planes ofrece TampaLawnPro y cuánto cuestan?": (
        "Ofrece planes mensuales desde $97 hasta $497, según el nivel de automatización y herramientas incluidas."
    ),
    "What plans does TampaLawnPro offer and how much do they cost?": (
        "TampaLawnPro offers monthly plans ranging from $97 to $497 depending on the level of automation and included features."
    ),

    # Price
    "¿Cuánto cuesta?": (
        "TampaLawnPro tiene planes mensuales que van desde $97 hasta $497, dependiendo de las funciones que necesites para tu negocio."
    ),
    "How much does it cost?": (
        "TampaLawnPro’s plans range from $97 to $497 per month, depending on the features you need for your business."
    ),

    # Technology
    "¿Qué tecnología utiliza TampaLawnPro?": (
        "Utiliza inteligencia artificial avanzada, soporte local y un chatbot llamado Lina que responde a consultas automáticamente."
    ),
    "What technology does TampaLawnPro use?": (
        "It uses advanced AI, local support, and a smart voice assistant named Lina to respond to inquiries automatically."
    ),

    # Privacy
    "¿Cómo maneja TampaLawnPro la privacidad?": (
        "Los datos están cifrados y se recopila información como nombre, correo electrónico, número de teléfono y geolocalización para brindar una mejor experiencia."
    ),
    "How does TampaLawnPro handle privacy?": (
        "Data is encrypted, and the system collects name, email, phone number, and location info to improve user experience."
    ),

    # Location
    "¿Dónde está ubicada TampaLawnPro?": (
        "La empresa tiene su sede en Wesley Chapel, en la región de Tampa, Florida, y se enfoca en brindar soporte local."
    ),
    "Where is TampaLawnPro located?": (
        "The company is based in Wesley Chapel, in the Tampa, Florida region, and focuses on providing local support."
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
