import os
import logging
from flask import Flask, request, url_for
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from pyngrok import ngrok
import threading
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Twilio Credentials (must be supplied via environment)
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
TARGET_PHONE_NUMBER = '+14062102346'

# Agent Brain (Simplified for Legacy Mode)
class AgentXBrain:
    def __init__(self):
        self.personality = {
            "name": "Alan",
            "company": "Agent X Solutions"
        }

    def generate_response(self, user_input):
        user_input = user_input.lower()
        if any(w in user_input for w in ['hello', 'hi']):
            return f"Hello! This is {self.personality['name']} from {self.personality['company']}. How are you doing today?"
        elif 'interested' in user_input:
            return "That's great! We help businesses grow. What are your main challenges?"
        elif 'bye' in user_input:
            return "Goodbye! Have a great day."
        else:
            return "I understand. Tell me more about that."

brain = AgentXBrain()

@app.route("/voice", methods=['POST'])
def voice():
    """Handle incoming call or loop."""
    resp = VoiceResponse()
    
    # If speech result is present, process it
    if 'SpeechResult' in request.values:
        user_input = request.values['SpeechResult']
        logger.info(f"User said: {user_input}")
        ai_response = brain.generate_response(user_input)
        resp.say(ai_response, voice='Polly.Matthew')
    else:
        # Initial greeting
        resp.say("Hello! This is Alan from Agent X Solutions. How can I help you?", voice='Polly.Matthew')

    # Gather more input
    gather = Gather(input='speech', action='/voice', method='POST', speechTimeout='auto')
    resp.append(gather)
    
    # If no input, loop
    resp.redirect('/voice')
    
    return str(resp)

def start_ngrok():
    url = ngrok.connect(5000).public_url
    logger.info(f" * ngrok tunnel \"{url}\" -> \"http://127.0.0.1:5000\"")
    return url

def make_call(public_url):
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        logger.error("Twilio credentials missing; set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER.")
        return
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    call = client.calls.create(
        to=TARGET_PHONE_NUMBER,
        from_=TWILIO_PHONE_NUMBER,
        url=f"{public_url}/voice"
    )
    logger.info(f"Call initiated: {call.sid}")

if __name__ == "__main__":
    # Start ngrok
    public_url = start_ngrok()
    
    # Give ngrok a moment
    time.sleep(2)
    
    # Initiate call
    threading.Thread(target=make_call, args=(public_url,)).start()
    
    # Run Flask
    app.run(port=5000)
