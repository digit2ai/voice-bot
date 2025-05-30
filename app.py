from flask import Flask, request, send_file
from flask_cors import CORS
import openai
import os
import tempfile
import difflib
from dotenv import load_dotenv

# Load environment
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__, static_folder='static')
CORS(app)

# FAQ brain
FAQ_BRAIN = {
    "what is tampalawnpro": "TampaLawnPro is an AI-powered lawn care platform that helps homeowners get instant quotes and lets lawn care pros automate quoting, booking, and payments.",
    "how does the instant quote work": "Just enter your address, and our AI uses satellite imagery to measure your lawn and generate an instant, personalized quote—no site visit needed.",
    "can i book and pay online": "Yes, you can securely book your service and handle all payments online—right from your phone or computer.",
    "do you support lawn pros": "Absolutely. We offer a full-featured Lawn Pro Dashboard where you can manage leads, jobs, payments, and customer communications.",
    "what is geopricing": "GeoPricing™ lets lawn pros set different pricing for different ZIP codes or areas. It’s perfect for local customization.",
    "do you offer crm or marketing tools": "Yes, TampaLawnPro integrates with tools like GoHighLevel to automate follow-ups, appointment reminders, and client engagement.",
    "where are you based": "We’re proudly based in Wesley Chapel, FL, and focused on serving the Tampa Bay area with real local support.",
    "who is tampalawnpro for": "We’re built for both homeowners who want fast, reliable lawn care—and for pros who want to grow their business efficiently.",
    "is this affordable for small businesses": "Yes, our platform is designed to scale with you—whether you're a solo operator or managing multiple crews.",
    "how can i get started": "Just visit TampaLawnPro.com to get your instant quote or request a live demo if you're a service provider."
}

def find_faq_answer(transcript: str):
    transcript_lower = transcript.lower()
    questions = list(FAQ_BRAIN.keys())
    best_match = difflib.get_close_matches(transcript_lower, questions, n=1, cutoff=0.7)
    if best_match:
        matched_key = best_match[0]
        print(f"🤖 Matched FAQ: {matched_key}")
        return FAQ_BRAIN[matched_key]
    return None

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
            ).text
        print(f"📝 [Step 2] Transcript: {transcript}")
    except Exception as e:
        print("❌ [Transcription Failed]:", e)
        return send_file("static/test.mp3", mimetype="audio/mpeg")

    try:
        faq_answer = find_faq_answer(transcript)
        if faq_answer:
            response = faq_answer
            print("💡 Responding with matched FAQ")
        else:
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
