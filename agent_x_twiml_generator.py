import os
from twilio.twiml.voice_response import VoiceResponse, Connect, ConversationRelay

def generate_conversation_relay_twiml(websocket_url="ws://localhost:8765", welcome_message="Hello! I'm Alan from Agent X. How can I help you today?"):
    """
    Generate TwiML for ConversationRelay - AI-powered voice interactions.
    This connects the call to a WebSocket server for real-time AI conversation.
    """
    response = VoiceResponse()

    # Create Connect verb
    connect = Connect()

    # Add ConversationRelay with AI settings - MALE VOICE CONFIGURATION
    conversation_relay = ConversationRelay(
        url=websocket_url,
        welcome_greeting=welcome_message,
        welcome_greeting_interruptible="any",
        language="en-US",
        tts_provider="ElevenLabs",
        voice="PIGsltMj3gFMR34aFDI3",  # MALE VOICE: User Selected (PIGsltMj3gFMR34aFDI3)
        transcription_provider="Deepgram",
        speech_model="nova-3-general",
        interruptible="any",
        interrupt_sensitivity="high",
        dtmf_detection="true",
        hints="Agent X, Alan, artificial intelligence, AI assistant, business, sales, support, account setup, professional, male voice, human-like conversation"
    )

    # Add language configurations for multi-language support - MALE VOICES
    conversation_relay.language(
        code="en-US",
        tts_provider="ElevenLabs",
        voice="PIGsltMj3gFMR34aFDI3",  # User Selected Voice
        transcription_provider="Deepgram",
        speech_model="nova-3-general"
    )

    conversation_relay.language(
        code="es-ES",
        tts_provider="ElevenLabs",
        voice="pNInz6obpgDQGcFmaJgB",  # Spanish male voice
        transcription_provider="Deepgram",
        speech_model="nova-2-general"
    )

    # Add custom parameters for Agent X context
    conversation_relay.parameter(name="agent_type", value="Agent X AI")
    conversation_relay.parameter(name="personality", value="helpful_assistant")
    conversation_relay.parameter(name="capabilities", value="voice_interaction,payments,support")

    connect.append(conversation_relay)
    response.append(connect)

    return str(response)

def generate_simple_greeting_twiml(message="Hello! This is Alan from Agent X calling."):
    """
    Generate simple TwiML for basic voice greeting.
    This can be used once voice calling is enabled.
    """
    response = VoiceResponse()
    response.say(message, voice="alice")
    response.pause(length=1)
    response.say("How can I assist you today?", voice="alice")

    return str(response)

def generate_payment_enabled_twiml(websocket_url):
    """
    Generate TwiML that combines ConversationRelay with payment capabilities.
    Note: Payments require active call context and proper setup.
    """
    response = VoiceResponse()

    # First, greet the caller
    response.say("Hello! I'm Alan from Agent X. I can help you with payments and support.", voice="alice")

    # Connect to ConversationRelay for AI interaction
    connect = Connect()
    conversation_relay = ConversationRelay(
        url=websocket_url,
        language="en-US",
        tts_provider="ElevenLabs",
        transcription_provider="Deepgram"
    )

    # Add payment-related hints
    conversation_relay.hints("payment,credit card,billing,charge,refund,support")

    connect.append(conversation_relay)
    response.append(connect)

    return str(response)

def demonstrate_twiml_generation():
    """
    Demonstrate different TwiML generation scenarios for Agent X.
    """
    print("=== Agent X TwiML Generation Examples ===\n")

    # Example 1: Basic greeting (works with current SDK)
    print("1. Basic Voice Greeting TwiML:")
    basic_twiml = generate_simple_greeting_twiml()
    print(basic_twiml)
    print()

    # Example 2: ConversationRelay (requires WebSocket server)
    websocket_url = "ws://localhost:8765"  # Local ConversationRelay server
    print("2. AI-Powered ConversationRelay TwiML:")
    ai_twiml = generate_conversation_relay_twiml(websocket_url)
    print(ai_twiml)
    print()

    # Example 3: Payment-enabled conversation
    print("3. Payment-Enabled Conversation TwiML:")
    payment_twiml = generate_payment_enabled_twiml(websocket_url)
    print(payment_twiml)
    print()

    print("=== Usage Notes ===")
    print("- Basic greeting works immediately once voice calling is enabled")
    print("- ConversationRelay requires a WebSocket server for AI interactions")
    print("- Payment features require active call context and proper PCI compliance")
    print("- All features require upgrading from trial account to enable voice calling")

if __name__ == "__main__":
    demonstrate_twiml_generation()