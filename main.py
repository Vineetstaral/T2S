from fastapi import FastAPI
import requests, os
from dotenv import load_dotenv
import sqlite3
import uvicorn

# Load environment variables
load_dotenv()
API_KEY = os.getenv("HUGGINGFACE_API_KEY")  
API_URL = "https://api-inference.huggingface.co/models/openai-community/gpt2"
headers = {"Authorization": f"Bearer {API_KEY}"}

app = FastAPI()

# SQLite Database Setup
conn = sqlite3.connect("data/chat.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY, user_input TEXT, bot_response TEXT)")
conn.commit()

# Function to call Hugging Face API
def query(payload):
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

# Route to send messages
@app.post("/send")
def send_message(user_input: str):
    bot_response = query({"inputs": user_input})
    
    if "error" in bot_response:
        bot_response_text = "Sorry, I couldn't process your request."
    else:
        bot_response_text = bot_response[0].get('generated_text', "No response")

    cursor.execute("INSERT INTO chats (user_input, bot_response) VALUES (?, ?)", (user_input, bot_response_text))
    conn.commit()
    
    return {"user": user_input, "bot": bot_response_text}

# Start the FastAPI server
if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
