from flask import Flask, request, send_file
from flask_cors import CORS
import openai
import os
import tempfile
from dotenv import load_dotenv
from difflib import get_close_matches

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__, static_folder='static')
CORS(app)

# Simple FAQ dictionary
FAQ_BRAIN = {
    "what is tampalawnpro": "TampaLawnPro is an AI-powered lawn care platform...",
    "que es tampalawnpro": "TampaLawnPro es una plataforma de cuidado del césped impulsada por IA..."
    # Keep rest as before or load from JSON
}

@app.route('/')
def serve_index():
    return app.send_static_file("index.html")

@app.route('/process-audio', methods=['POST'])
def process_audio():
    print("📥 Audio request received")

    audio_file = request.files.get("file")
    if not audio_file:
        print("❌ No audio file found in request")
        return "Missing audio", 400

    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
        audio_file.save(temp_audio.name)
        print(f"✅ Saved uploaded audio: {temp_audio.name}")

    try:
        with open(temp_audio.name, "rb") as f:
            transcript = openai.audio.transcriptions.create(
                model="whisper-1",
                file=f
            ).text.lower()
        print(f"📝 Transcript: {transcript}")
    except Exception as e:
        print("❌ Error in transcription:", e)
        return send_file("static/test.mp3", mimetype="audio/mpeg")

    matched = get_close_matches(transcript, FAQ_BRAIN.keys(), n=1, cutoff=0.7)
    if matched:
        response = FAQ_BRAIN[matched[0]]
        print(f"🤖 Matched response: {matched[0]}")
    else:
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are Lina, a friendly assistant for lawn care."},
                    {"role": "user", "content": transcript}
                ]
            ).choices[0].message.content
            print(f"💬 GPT response: {response}")
        except Exception as e:
            print("❌ GPT fallback failed:", e)
            return send_file("static/test.mp3", mimetype="audio/mpeg")

    try:
        speech = openai.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=response
        )
        print("🔊 TTS completed")
    except Exception as e:
        print("❌ TTS failed:", e)
        return send_file("static/test.mp3", mimetype="audio/mpeg")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as out_audio:
            out_audio.write(speech.content)
            out_audio.flush()
            os.fsync(out_audio.fileno())

            file_size = os.path.getsize(out_audio.name)
            print(f"📁 MP3 file size: {file_size} bytes")

            if file_size < 1000:
                print("⚠️ MP3 too small, fallback triggered")
                return send_file("static/test.mp3", mimetype="audio/mpeg")

            return send_file(out_audio.name, mimetype="audio/mpeg", download_name="response.mp3")

    except Exception as e:
        print("❌ File serving failed:", e)
        return send_file("static/test.mp3", mimetype="audio/mpeg")

if __name__ == "__main__":
    app.run(debug=True)
