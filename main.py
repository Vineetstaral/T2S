from fastcore.parallel import threaded
from fasthtml.common import *
import uuid, os, uvicorn, requests, glob
from pydub import AudioSegment
import io
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv("HUGGINGFACE_API_KEY")
API_URL = "https://api-inference.huggingface.co/models/facebook/fastspeech2-en-ljspeech"  # Example TTS model
headers = {"Authorization": f"Bearer {API_KEY}"}

# Function to query the Hugging Face API
def query(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.content

# Database setup
tables = database('data/tts.db').t
tts_entries = tables.tts_entries
if not tts_entries in tables:
    tts_entries.create(prompt=str, id=int, folder=str, pk='id')
TTSEntry = tts_entries.dataclass()

# Flexbox CSS (http://flexboxgrid.com/)
gridlink = Link(rel="stylesheet", href="https://cdnjs.cloudflare.com/ajax/libs/flexboxgrid/6.3.1/flexboxgrid.min.css", type="text/css")

# Our FastHTML app
app = FastHTML(hdrs=(picolink, gridlink))

# Main page
@app.get("/")
def home():
    inp = Input(id="new-prompt", name="prompt", placeholder="Enter text to convert to speech")
    add = Form(Group(inp, Button("Generate Speech")), hx_post="/", target_id='tts-list', hx_swap="afterbegin")
    tts_containers = [tts_preview(t) for t in tts_entries(limit=10)]  # Start with last 10
    tts_list = Div(*reversed(tts_containers), id='tts-list', cls="row")  # flexbox container: class = row

    # Display the number of audio files
    audio_count_div = Div(id='audio-count', hx_get="/audio_count", hx_trigger="load", hx_swap="innerHTML")

    return Title('Text-to-Speech Demo'), Main(
        H1('Magic Text-to-Speech Generation'),
        add,
        audio_count_div,  # Add the audio count display
        tts_list,
        cls='container'
    )

# Show the audio player (if available) and prompt for a TTS entry
def tts_preview(t):
    grid_cls = "box col-xs-12 col-sm-6 col-md-4 col-lg-3"
    audio_path = f"{t.folder}/{t.id}.wav"
    delete_button = Button("Delete", hx_delete=f"/tts/{t.id}", hx_confirm="Are you sure you want to delete this audio?", hx_target=f'#tts-{t.id}', hx_swap="outerHTML", hx_trigger="click")
    if os.path.exists(audio_path):
        return Div(Card(
                       Audio(src=audio_path, controls=True, cls="card-audio"),
                       Div(P(B("Text: "), t.prompt, cls="card-text"), cls="card-body"),
                       delete_button
                   ), id=f'tts-{t.id}', cls=grid_cls)
    return Div(f"Generating audio for text: {t.prompt}",
            id=f'tts-{t.id}', hx_get=f"/tts/{t.id}",
            hx_trigger="every 2s", hx_swap="outerHTML", cls=grid_cls)

# A pending preview keeps polling this route until we return the audio preview
@app.get("/tts/{id}")
def preview(id:int):
    return tts_preview(tts_entries.get(id))

# For static files like CSS, etc.
@app.get("/{fname:path}.{ext:static}")
def static(fname:str, ext:str):
    return FileResponse(f'{fname}.{ext}')

# TTS generation route
@app.post("/")
def post(prompt:str):
    if count_free_audios() >= 2:
        return "Free limit reached! <a href='https://example.com/upgrade'>Upgrade Now</a>"

    folder = f"data/tts/{str(uuid.uuid4())}"
    os.makedirs(folder, exist_ok=True)
    t = tts_entries.insert(TTSEntry(prompt=prompt, folder=folder))
    generate_and_save(t.prompt, t.id, t.folder)
    clear_input = Input(id="new-prompt", name="prompt", placeholder="Enter text to convert to speech", hx_swap_oob='true')
    return tts_preview(t), clear_input

# Delete route
@app.delete("/tts/{id}")
def delete_tts(id:int):
    tts_entry = tts_entries.get(id)
    if tts_entry:
        audio_path = f"{tts_entry.folder}/{tts_entry.id}.wav"
        if os.path.exists(audio_path):
            os.remove(audio_path)
        tts_entries.delete(id)
    return "Hit Refresh!"

# Generate an audio file and save it to the folder (in a separate thread)
@threaded
def generate_and_save(prompt, id, folder):
    audio_bytes = query({"inputs": prompt})
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="wav")
    audio.export(f"{folder}/{id}.wav", format="wav")
    return True

# Count WAV audio files
@app.get("/audio_count")
def audio_count():
    count = count_free_audios()
    if count >= 2:
        return "Free limit reached! <a href='https://example.com/upgrade'>Upgrade Now</a>"
    return f"Number of audio files generated: {count}/2"

def count_free_audios():
    wav_files = glob.glob("data/tts/**/*.wav", recursive=True)
    return len(wav_files)

if __name__ == '__main__':
    uvicorn.run("main:app", host='0.0.0.0', port=int(os.getenv("PORT", default=8000)))
