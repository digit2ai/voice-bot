from flask import Flask, request, send_file
from flask_cors import CORS
import openai
import os
import tempfile
from dotenv import load_dotenv
from difflib import get_close_matches

# Load environment
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__, static_folder='static')
CORS(app)

FAQ_BRAIN = {
    # English
    "what is tampalawnpro": "TampaLawnPro is an AI-powered lawn care platform that helps homeowners get instant quotes and lets lawn care pros automate quoting, booking, and payments.",
    "how does the instant quote work": "Just enter your address, and our AI uses satellite imagery to measure your lawn and generate an instant, personalized quote—no site visit needed.",
    "can i book and pay online": "Yes, you can securely book your service and handle all payments online—right from your phone or computer.",
    "do you support lawn pros": "Absolutely. We offer a full-featured Lawn Pro Dashboard where you can manage leads, jobs, payments, and customer communications.",
    "what is geopricing": "GeoPricing™ lets lawn pros set different pricing for different ZIP codes or areas. It’s perfect for local customization.",
    "do you offer crm or marketing tools": "Yes, TampaLawnPro integrates with tools like GoHighLevel to automate follow-ups, appointment reminders, and client engagement.",
    "where are you based": "We’re proudly based in Wesley Chapel, and focused on serving the Tampa Bay area with real local support.",
    "who is tampalawnpro for": "We’re built for both homeowners who want fast, reliable lawn care—and for pros who want to grow their business efficiently.",
    "is this affordable for small businesses": "Yes, our platform is designed to scale with you—whether you're a solo operator or managing multiple crews.",
    "how can i get started": "Just visit TampaLawnPro.com to get your instant quote or request a live demo if you're a service provider.",
    "how much does the service cost": "Our pricing starts at $97 per month for smaller companies. You only pay for what you use, making it cost-effective for businesses of all sizes.",
    "how easy is it to set up the tool": "Setting up our tool is simple. We provide tutorials and dedicated support to walk you through the entire process.",
    "what imagery do you use for measurements": "We use county public records to obtain property dimensions, along with Google Maps Platform sources to ensure precise measurements.",
    "how fast is your ai for measurements": "Our AI generates residential property measurements in about 30 to 60 seconds — lightning fast and highly accurate.",
    "what can your software measure": "We can measure lawns, driveways, sidewalks, patios, and even building footprints — ideal for creating accurate property assessments.",
    "where is the service available": "We currently serve businesses across Tampa Bay, Wesley Chapel and Pineelas county, supporting a wide variety of lawn care providers.,
    "do you offer route optimization": "Yes, TampaLawnPro can help you save time and fuel by automatically optimizing your daily service routes for maximum efficiency.",
    "can i send automatic appointment reminders": "Yes. Our system sends automated email and text reminders to your customers, reducing no-shows and improving communication.",
    "is there a customer portal": "Yes. Customers can log in to a secure portal to view service history, pay invoices, and request new appointments at their convenience.",
    "how does scheduling work": "You can drag and drop jobs onto your calendar and assign them to specific team members. It’s quick, intuitive, and mobile-friendly.",
    "can i create and send invoices": "Absolutely. You can generate professional invoices, accept online payments, and track revenue—all from your dashboard.",
    "does tampalawnpro work on mobile": "Yes, the entire platform is mobile-optimized. Whether you're in the office or in the field, you can run your business on the go.",
    "can i collect customer reviews": "Yes. After a service is completed, you can automatically request reviews from your customers and showcase your reputation online.",
    "how can i manage my team": "You can assign jobs, track progress, and monitor team performance—all from one central dashboard.",
    "is my customer data safe": "Yes, we use industry-standard encryption and data protection practices to keep your customer and business information secure.",
    "can i customize service offerings": "Yes. You can tailor your service catalog, pricing, and availability to match your unique business model and target market.”,
    "can i track my income and expenses": "Yes, TampaLawnPro lets you record income and expenses to keep your business finances organized and ready for tax season.",
    "do you offer chemical tracking": "Yes. If you apply fertilizers or treatments, TampaLawnPro allows you to log chemical usage for compliance and reporting purposes.",
    "is there a client database": "Yes. You can manage all your customer information, service history, and notes in one place.",
    "can i schedule recurring jobs": "Absolutely. You can set up recurring services for weekly, bi-weekly, or custom intervals, and we’ll handle the reminders.",
    "can i take notes on properties": "Yes. You can add property-specific notes, like gate codes, pet warnings, or special instructions.",
    "can i generate reports": "Yes. TampaLawnPro provides reports on revenue, job status, customer history, and more so you can run your business smarter.",
    "does it support multiple users": "Yes. You can create accounts for your crew members, assign permissions, and track who does what.",
    "can i create custom service packages": "Yes, you can bundle multiple services into a custom package with your own pricing and frequency settings.",
    "how do i handle one-time jobs": "TampaLawnPro supports both recurring and one-time jobs. You can easily schedule, invoice, and complete them from your dashboard.",
    "can i accept tips from customers": "Yes. When customers pay online, they have the option to leave a tip, and it’s added to your payment report automatically.",
    "how does tampalawnpro work": "TampaLawnPro makes lawn care easy—just enter your address to get an instant quote, and we’ll match you with a trusted local lawn care pro for fast booking and secure payment online.",
    "do i have to be home during the service": "No, you don’t have to be home. Just ensure your lawn is accessible, gates are unlocked, and pets are secured.",
    "can i request a specific lawn pro": "Yes! Once you've had a service, you can request the same pro for future visits, depending on their availability.",
    "how are prices calculated": "We use satellite imagery to measure your lawn and apply our GeoPricing™ model to ensure fair, accurate quotes based on your location and service type.",
    "does tampalawnpro offer a satisfaction guarantee": "Absolutely! We offer a 100% satisfaction guarantee. If you’re not happy, we’ll make it right—no questions asked.",
    "can i skip or reschedule a service": "Yes, you can skip or reschedule anytime through your online dashboard. Just let us know at least 24 hours in advance.",
    "how do i pay for services": "All payments are handled securely online. You’ll only be charged after your lawn service is completed.",
    "does tampalawnpro serve my area": "We serve the entire Tampa Bay area—including Wesley Chapel, Brandon, Riverview, and nearby ZIP codes. Just enter your address to check availability."
    
    # Spanish
    "que es tampalawnpro": "TampaLawnPro es una plataforma de cuidado del césped impulsada por IA que ayuda a los propietarios a obtener cotizaciones instantáneas y permite a los profesionales automatizar presupuestos, reservas y pagos.",
    "como funciona la cotizacion instantanea": "Solo ingresa tu dirección y nuestra IA usará imágenes satelitales para medir tu césped y generar una cotización personalizada al instante—sin visita necesaria.",
    "puedo reservar y pagar en linea": "Sí, puedes reservar tu servicio y realizar todos los pagos en línea, desde tu celular o computadora.",
    "apoyan a los profesionales del cesped": "Claro que sí. Ofrecemos un panel completo para Lawn Pros donde pueden gestionar clientes potenciales, trabajos, pagos y comunicación.",
    "que es geopricing": "GeoPricing™ permite a los Lawn Pros establecer precios diferentes por código postal o zona. Es perfecto para personalizar localmente.",
    "ofrecen herramientas de crm o marketing": "Sí, TampaLawnPro se integra con plataformas como GoHighLevel para automatizar seguimientos, recordatorios de citas y comunicaciones.",
    "donde estan ubicados": "Estamos orgullosamente ubicados en Wesley Chapel, FL y servimos al área de Tampa Bay con soporte local real.",
    "para quien es tampalawnpro": "Está diseñado tanto para propietarios que quieren servicios confiables y rápidos, como para profesionales que quieren hacer crecer su negocio.",
    "es asequible para pequeños negocios": "Sí, nuestra plataforma está diseñada para escalar contigo, seas un operador independiente o manejes varios equipos.",
    "como empiezo": "Solo visita TampaLawnPro.com para obtener tu cotización instantánea o solicita una demo si eres proveedor."
}

@app.route('/')
def serve_index():
    return app.send_static_file("index.html")

@app.route('/process-audio', methods=['POST'])
def process_audio():
    print("🔊 [Step 1] Received audio POST request")

    audio_file = request.files.get("file")
    if not audio_file:
        print("❌ No file uploaded")
        return "No audio file received", 400

    print(f"📦 File received: {audio_file.filename}, type: {audio_file.content_type}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
        audio_file.save(temp_audio.name)
        print(f"✅ Saved audio file to: {temp_audio.name}")

    try:
        with open(temp_audio.name, "rb") as audio:
            transcript = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio
            ).text.lower()
        print(f"📝 [Step 2] Transcript: {transcript}")
    except Exception as e:
        print("❌ [Transcription Failed]:", e)
        return send_file("static/test.mp3", mimetype="audio/mpeg")

    matched = get_close_matches(transcript, FAQ_BRAIN.keys(), n=1, cutoff=0.7)
    if matched:
        response = FAQ_BRAIN[matched[0]]
        print(f"🤖 [Step 3] Matched FAQ: {matched[0]}")
    else:
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are Lina, a helpful lawn care assistant from TampaLawnPro."},
                    {"role": "user", "content": transcript}
                ]
            ).choices[0].message.content
            print(f"💬 [Step 3] GPT Reply: {response}")
        except Exception as e:
            print("❌ [GPT Failed]:", e)
            return send_file("static/test.mp3", mimetype="audio/mpeg")

    try:
        speech = openai.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=response
        )
        print("🔊 [Step 4] TTS completed")
    except Exception as e:
        print("❌ [TTS Failed]:", e)
        return send_file("static/test.mp3", mimetype="audio/mpeg")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as out_audio:
            out_audio.write(speech.content)
            out_audio.flush()
            os.fsync(out_audio.fileno())
            file_size = os.path.getsize(out_audio.name)
            print(f"✅ [Step 5] MP3 created: {file_size} bytes")

            if file_size < 1000:
                print("⚠️ MP3 file is too small. Returning test.mp3 fallback.")
                return send_file("static/test.mp3", mimetype="audio/mpeg")

            return send_file(
                out_audio.name,
                mimetype="audio/mpeg",
                as_attachment=False,
                download_name="response.mp3"
            )
    except Exception as e:
        print("❌ [File Return Failed]:", e)
        return send_file("static/test.mp3", mimetype="audio/mpeg")

if __name__ == '__main__':
    app.run(debug=True)
