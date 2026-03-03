"""
Direct Twilio Voice Call Script
Makes outbound calls using Twilio Python SDK directly
"""

import os
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect, ConversationRelay
import time

def make_voice_call(to_number, from_number=None, message=None):
    """
    Make a direct voice call using Twilio Python SDK

    Args:
        to_number: Phone number to call (E.164 format)
        from_number: Twilio phone number to call from
        message: Custom message to speak
    """

    # Get credentials from environment
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')

    if not account_sid or not auth_token:
        print("❌ Missing Twilio credentials. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN")
        return None

    # Default numbers if not provided
    if not from_number:
        from_number = os.environ.get('TWILIO_PHONE_NUMBER', '+18883277213')

    if not message:
        message = "Hi! This is Alan from Agent X. I wanted to connect personally and hear how things are unfolding on your side today. I'm eager to explore what's next together."

    try:
        # Initialize Twilio client
        client = Client(account_sid, auth_token)

        # Create TwiML response for the call using ConversationRelay
        response = VoiceResponse()
        connect = Connect()

        # Configure ConversationRelay for Agent X AI conversation
        # Using the public ngrok URL for the WebSocket connection
        conversation_relay = ConversationRelay(
            url="wss://hierodulic-unfaded-gemma.ngrok-free.dev/conversation-relay",  # Public WebSocket URL
            welcome_greeting="Hi! This is Alan from Agent X. I wanted to connect personally and hear how things are unfolding on your side today. I'm eager to explore what's next together.",
            welcome_greeting_interruptible="any",
            language="en-US",
            tts_provider="ElevenLabs",
            voice="PIGsltMj3gFMR34aFDI3",  # ElevenLabs voice (User Selected)
            transcription_provider="Deepgram",
            speech_model="nova-3-general",
            interruptible="any",
            interrupt_sensitivity="high",
            hints="Agent X, Alan, artificial intelligence, AI assistant, conversation, help"
        )

        # Add custom parameters for Agent X
        conversation_relay.parameter(name="agent_type", value="Agent X AI")
        conversation_relay.parameter(name="personality", value="helpful_assistant")
        conversation_relay.parameter(name="call_purpose", value="personal_connection")

        connect.append(conversation_relay)
        response.append(connect)

        # Make the call with ConversationRelay TwiML
        call = client.calls.create(
            twiml=str(response),
            to=to_number,
            from_=from_number
        )

        print(f"✅ Call initiated successfully!")
        print(f"📞 Call SID: {call.sid}")
        print(f"📱 To: {to_number}")
        print(f"📞 From: {from_number}")
        print(f"📊 Status: {call.status}")

        return call

    except Exception as e:
        print(f"❌ Call failed: {str(e)}")
        return None

def check_call_status(call_sid):
    """
    Check the status of a call

    Args:
        call_sid: The call SID to check
    """
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')

    if not account_sid or not auth_token:
        print("❌ Missing Twilio credentials")
        return None

    try:
        client = Client(account_sid, auth_token)
        call = client.calls(call_sid).fetch()

        print(f"📞 Call Status: {call.status}")
        print(f"⏱️  Duration: {call.duration} seconds")
        print(f"📅 Start Time: {call.start_time}")
        print(f"📅 End Time: {call.end_time}")

        return call

    except Exception as e:
        print(f"❌ Status check failed: {str(e)}")
        return None

if __name__ == "__main__":
    print("🎯 Direct Twilio Voice Call")
    print("=" * 50)

    # Target phone number
    target_number = "+14062102346"  # The number you want to call

    # Custom message for Alan
    alan_message = """
    Hi! This is Alan from Agent X. I wanted to connect personally and hear how things are unfolding on your side today.
    I'm eager to explore what's next together. Please call me back at 888-327-7213 when you have a moment.
    """

    print(f"📱 Calling: {target_number}")
    print(f"💬 Message: {alan_message.strip()}")

    # Make the call
    call = make_voice_call(target_number, message=alan_message)

    if call:
        print("\n⏳ Waiting 10 seconds then checking status...")
        time.sleep(10)

        # Check call status
        check_call_status(call.sid)

    print("\n🎯 Call attempt complete!")