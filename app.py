
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
    audio_file = request.files["file"]
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
        audio_file.save(temp_audio.name)

        transcript = openai.audio.transcribe("whisper-1", file=open(temp_audio.name, "rb"))["text"]

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are Lina, a helpful lawn care assistant from TampaLawnPro."},
                {"role": "user", "content": transcript}
            ]
        ).choices[0].message.content

        speech = openai.audio.speech.create(
            model="tts-1-hd",
            voice="nova",
            input=response
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as out_audio:
            out_audio.write(speech.content)
            return send_file(out_audio.name, mimetype="audio/mpeg")

if __name__ == '__main__':
    app.run(debug=True)
