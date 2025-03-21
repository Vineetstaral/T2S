from fastcore.parallel import threaded
from fasthtml.common import *
import uuid, os, uvicorn, requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv("HUGGINGFACE_API_KEY")  
API_URL = "https://router.huggingface.co/hf-inference/models/openai-community/gpt2"  
headers = {"Authorization": f"Bearer {API_KEY}"}

# Function to query the Hugging Face API
def query(payload):
    """
    Send a request to the Hugging Face API and return the response.
    """
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"API error: {e}"}

# Database for storing chat history
tables = database('data/chat.db').t
chats = tables.chats
if not chats in tables:
    chats.create(user_input=str, bot_response=str, id=int, pk='id')
Chat = chats.dataclass()

# Flexbox CSS (http://flexboxgrid.com/)
gridlink = Link(rel="stylesheet", href="https://cdnjs.cloudflare.com/ajax/libs/flexboxgrid/6.3.1/flexboxgrid.min.css", type="text/css")

# Our FastHTML app
app = FastHTML(hdrs=(picolink, gridlink))

# Main page
@app.get("/")
def home():
    # Input form for user messages
    inp = Input(id="user-input", name="user_input", placeholder="Type your message...")
    send = Form(Group(inp, Button("Send")), hx_post="/send", target_id='chat-history', hx_swap="beforeend")

    # Display chat history
    chat_history = Div(id='chat-history', cls="row")
    for chat in chats(limit=10):  # Show the last 10 messages
        chat_history.append(chat_message(chat))

    return Title('Chatbot Demo'), Main(
        H1('Chat with AI 🤖'),
        send,
        chat_history,
        cls='container'
    )

# Format a chat message
def chat_message(chat):
    """
    Format a chat message for display.
    """
    user_msg = Div(P(B("You: "), chat.user_input), cls="user-message")
    bot_msg = Div(P(B("AI: "), chat.bot_response), cls="bot-message")
    return Div(user_msg, bot_msg, cls="chat-message")

# Route to handle user messages
@app.post("/send")
def send_message(user_input: str):
    # Query the Hugging Face API for a response
    bot_response = query({"inputs": user_input})
    if "error" in bot_response:
        bot_response = "Sorry, I couldn't process your request. Please try again."

    # Save the chat to the database
    chat = chats.insert(Chat(user_input=user_input, bot_response=bot_response))

    # Clear the input field
    clear_input = Input(id="user-input", name="user_input", placeholder="Type your message...", hx_swap_oob='true')

    # Return the new chat message and clear the input field
    return chat_message(chat), clear_input

# Run the app
if __name__ == '__main__':
    uvicorn.run("main:app", host='0.0.0.0', port=int(os.getenv("PORT", default=8000)))
