from flask import Flask, request, send_file
from flask_cors import CORS
import openai
import os
import tempfile
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__, static_folder='static')
CORS(app)

@app.route('/')
def serve_index():
    return app.send_static_file("index.html")

@app.route('/process-audio', methods=['POST'])
def process_audio():
    print("🔊 Received audio POST request...")

    audio_file = request.files["file"]
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
        audio_file.save(temp_audio.name)
        print(f"✅ Saved audio file to: {temp_audio.name}")

    try:
        with open(temp_audio.name, "rb") as audio:
            transcript = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio
            ).text
        print(f"📝 Transcript: {transcript}")
    except Exception as e:
        print("❌ Transcription failed:", e)
        return send_file("static/test.mp3", mimetype="audio/mpeg")

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are Lina, a helpful lawn care assistant from TampaLawnPro."},
                {"role": "user", "content": transcript}
            ]
        ).choices[0].message.content
        print(f"💬 GPT Reply: {response}")
    except Exception as e:
        print("❌ GPT failed:", e)
        return send_file("static/test.mp3", mimetype="audio/mpeg")

    try:
        speech = openai.audio.speech.create(
            model="tts-1-hd",
            voice="nova",
            input=response
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as out_audio:
            out_audio.write(speech.content)
            out_audio.flush()
            os.fsync(out_audio.fileno())
            print(f"✅ TTS MP3 file saved: {out_audio.name}")
            print(f"🎧 MP3 size: {os.path.getsize(out_audio.name)} bytes")
            return send_file(out_audio.name, mimetype="audio/mpeg")
    except Exception as e:
        print("❌ TTS failed:", e)
        return send_file("static/test.mp3", mimetype="audio/mpeg")

if __name__ == '__main__':
    app.run(debug=True)
