from fastapi import FastAPI, HTTPException, Form
import requests
import io
import os
import soundfile as sf
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from fasthtml.common import *
import uuid

# Load environment variables
load_dotenv()
API_KEY = os.getenv("HUGGINGFACE_API_KEY")
API_URL = "https://api-inference.huggingface.co/models/facebook/fastspeech2-en-ljspeech"  
headers = {"Authorization": f"Bearer {API_KEY}"}

# Validate API Key
if not API_KEY:
    raise RuntimeError("Hugging Face API key is missing. Set 'HUGGINGFACE_API_KEY' in the .env file.")

app = FastHTML()

# CSS for styling the UI
custom_css = Style("""
    body {
        background: linear-gradient(to right, #00c6ff, #0072ff);
        font-family: 'Arial', sans-serif;
        color: white;
        text-align: center;
        padding: 50px;
    }
    .container {
        max-width: 600px;
        margin: auto;
        background: rgba(255, 255, 255, 0.2);
        padding: 20px;
        border-radius: 10px;
    }
    textarea {
        width: 100%;
        padding: 10px;
        border-radius: 5px;
        border: none;
        resize: none;
        font-size: 16px;
    }
    button {
        background: #ff6b6b;
        color: white;
        border: none;
        padding: 10px 20px;
        font-size: 18px;
        cursor: pointer;
        border-radius: 5px;
        margin-top: 10px;
    }
    button:hover {
        background: #ff4757;
    }
    audio {
        margin-top: 20px;
        width: 100%;
    }
""")

# Function to query Hugging Face API
def query_huggingface_api(payload):
    response = requests.post(API_URL, headers=headers, json=payload)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"Hugging Face API error: {response.text}")

    return response.content

# Save the WAV file temporarily for playback
def save_audio_file(audio_data):
    filename = f"static/{uuid.uuid4().hex}.wav"
    os.makedirs("static", exist_ok=True)  # Ensure directory exists
    with open(filename, "wb") as f:
        f.write(audio_data)
    return filename

# FastHTML Home Page
@app.get("/")
def home():
    return Title("Text-to-Speech Converter"), custom_css, Main(
        Div(
            H1("Text-to-Speech Converter 🎙️"),
            P("Enter text below and click 'Convert to Speech' to generate an audio file."),
            Form(
                Group(
                    Textarea(id="text-input", placeholder="Type your text here...", rows=5, name="text"),
                    Button("🎤 Convert to Speech", 
                           hx_post="/text-to-speech/", 
                           hx_target="#audio-container", 
                           hx_swap="innerHTML",
                           hx_headers='{"Content-Type": "application/x-www-form-urlencoded"}')
                )
            ),
            Div(id="audio-container"),  # Placeholder for audio output
            cls="container"
        )
    )

# Fix API to Accept Form Data
@app.post("/text-to-speech/")
def text_to_speech(text: str = Form(...)):  # Accept form data
    try:
        if len(text) > 500:
            raise HTTPException(status_code=400, detail="Text too long. Limit is 500 characters.")

        payload = {"inputs": text}
        audio_data = query_huggingface_api(payload)

        if not audio_data or len(audio_data) < 100:
            raise HTTPException(status_code=500, detail="Invalid response: No audio data received.")

        # Convert to WAV and save to file
        audio_path = save_audio_file(audio_data)

        # Return an HTML audio player element with the file URL
        return Audio(audio_path, controls=True)

    except Exception as e:
        return Div(f"Error: {str(e)}", cls="error-message")

# Run the API server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")
