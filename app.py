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

    # 🚧 TEMP TEST MODE: return a known good mp3
    try:
        print("🔁 Returning static test.mp3 instead of TTS output.")
        return send_file("static/test.mp3", mimetype="audio/mpeg")
    except Exception as e:
        print("❌ Test MP3 file error:", e)
        return "Test MP3 failed", 500

if __name__ == '__main__':
    app.run(debug=True)
