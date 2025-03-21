from fastcore.parallel import threaded
from fasthtml.common import *
import uuid, os, uvicorn, requests, glob
from pydub import AudioSegment
import io
from dotenv import load_dotenv

# Load environment variables from .env file
# Example TTS model
headers = {"Authorization": f"Bearer {API_KEY}"}


from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import soundfile as sf
import io
from fastapi.responses import StreamingResponse

app = FastAPI()
load_dotenv()
API_KEY = os.getenv("HUGGINGFACE_API_KEY")
API_URL = "https://api-inference.huggingface.co/models/facebook/fastspeech2-en-ljspeech"  
headers = {"Authorization": f"Bearer {API_TOKEN}"}

class TextToSpeechRequest(BaseModel):
    text: str

def query_huggingface_api(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.content

@app.post("/text-to-speech/")
async def text_to_speech(request: TextToSpeechRequest):
    try:
        # Send text to Hugging Face API
        payload = {"inputs": request.text}
        audio_data = query_huggingface_api(payload)
        
        # Convert the audio data to a WAV file in memory
        wav_io = io.BytesIO(audio_data)
        wav_io.seek(0)
        
        # Return the WAV file as a streaming response
        return StreamingResponse(wav_io, media_type="audio/wav")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
