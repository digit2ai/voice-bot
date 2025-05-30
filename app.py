from flask import Flask, request, send_file
from flask_cors import CORS
import openai
import os
import tempfile
from dotenv import load_dotenv

# Load environment
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__, static_folder='static')
CORS(app)

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

    # Save uploaded audio
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
        audio_file.save(temp_audio.name)
        print(f"✅ Saved audio file to: {temp_audio.name}")

    # Transcribe speech
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

    # Generate GPT-4o reply
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

    # Convert reply to speech
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

    # Write and return audio
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
