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

        # Transcribe audio to text
        try:
            with open(temp_audio.name, "rb") as audio:
                transcript = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio
                ).text
            print(f"📝 Transcript: {transcript}")
        except Exception as e:
            print("❌ Transcription error:", e)
            return "Transcription failed", 500

        # Generate chat response
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
            print("❌ GPT error:", e)
            return "GPT failed", 500

        # Convert to speech
        try:
            speech = openai.audio.speech.create(
                model="tts-1-hd",
                voice="nova",
                input=response
            )
            print("🔊 Speech created.")
        except Exception as e:
            print("❌ TTS error:", e)
            return "Text-to-speech failed", 500

        # Save and return MP3
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as out_audio:
                out_audio.write(speech.content)
                out_audio.flush()
                os.fsync(out_audio.fileno())
                print(f"✅ Returning audio file: {out_audio.name}")
                print("🎧 MP3 file size:", os.path.getsize(out_audio.name), "bytes")
                return send_file(out_audio.name, mimetype="audio/mpeg")
        except Exception as e:
            print("❌ File write or send error:", e)
            return "Audio response failed", 500

if __name__ == '__main__':
    app.run(debug=True)
