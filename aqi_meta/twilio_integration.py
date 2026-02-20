"""
Twilio Integration for AQI Meta-Layer
Handles voice calls, SMS, and conversation relay for merchant outreach.
"""

import os
from typing import Dict, List, Any, Optional
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import requests

class TwilioIntegration:
    """
    Manages Twilio operations for AQI voice communications.
    """
    
    def __init__(self):
        self.account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        self.auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        self.phone_number = os.environ.get('TWILIO_PHONE_NUMBER')

        if not all([self.account_sid, self.auth_token, self.phone_number]):
            print("Warning: Twilio environment not configured (missing SID/token/phone). Twilio disabled.")
            self.client = None
            self.twilio_available = False
            return

        try:
            self.client = Client(self.account_sid, self.auth_token)
            self.twilio_available = True
        except Exception as e:
            print(f"Warning: Twilio client initialization failed: {e}")
            self.twilio_available = False
    
    def initiate_call(self, to_number: str, webhook_url: str, 
                     context: Dict[str, Any] = None) -> Optional[str]:
        """
        Initiate an outbound call.
        
        Args:
            to_number: Target phone number
            webhook_url: URL for call handling
            context: Additional context for the call
            
        Returns:
            Call SID if successful, None otherwise
        """
        if not self.twilio_available:
            print("Twilio not available")
            return None
        
        try:
            call = self.client.calls.create(
                to=to_number,
                from_=self.phone_number,
                url=webhook_url,
                method='POST'
            )
            return call.sid
        except Exception as e:
            print(f"Call initiation failed: {e}")
            return None
    
    def send_sms(self, to_number: str, message: str) -> bool:
        """
        Send an SMS message.
        
        Args:
            to_number: Target phone number
            message: SMS content
            
        Returns:
            True if successful
        """
        if not self.twilio_available:
            print("Twilio not available")
            return False
        
        try:
            message = self.client.messages.create(
                body=message,
                from_=self.phone_number,
                to=to_number
            )
            return True
        except Exception as e:
            print(f"SMS failed: {e}")
            return False
    
    def generate_twiml_response(self, response_text: str, 
                              voice_url: Optional[str] = None) -> str:
        """
        Generate TwiML for voice response.
        
        Args:
            response_text: Text to speak
            voice_url: URL to audio file (if using pre-recorded)
            
        Returns:
            TwiML XML string
        """
        response = VoiceResponse()
        
        if voice_url:
            response.play(voice_url)
        else:
            # Use ElevenLabs or fallback TTS
            audio_url = self._generate_audio(response_text)
            if audio_url:
                response.play(audio_url)
            else:
                response.say(response_text, voice='alice')
        
        # Add gather for user input
        response.gather(
            input='speech',
            action='/twilio/voice',
            method='POST',
            timeout=5,
            speech_timeout='auto'
        )
        
        return str(response)
    
    def _generate_audio(self, text: str) -> Optional[str]:
        """
        Generate audio using ElevenLabs or fallback.
        
        Args:
            text: Text to convert to speech
            
        Returns:
            URL to audio file or None
        """
        # Try ElevenLabs first
        elevenlabs_key = os.environ.get('ELEVENLABS_API_KEY')
        if elevenlabs_key:
            try:
                url = "https://api.elevenlabs.io/v1/text-to-speech/pNInz6obpgDQGcFmaJgB"  # Tim Jones voice
                headers = {
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": elevenlabs_key
                }
                data = {
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.5
                    }
                }
                
                response = requests.post(url, json=data, headers=headers)
                if response.status_code == 200:
                    # In a real implementation, you'd upload this to a accessible URL
                    # For now, return a placeholder
                    return f"data:audio/mpeg;base64,{response.content.hex()}"
                    
            except Exception as e:
                print(f"ElevenLabs failed: {e}")
        
        # Fallback to Twilio TTS
        return None
    
    def get_call_status(self, call_sid: str) -> Optional[Dict]:
        """
        Get status of a call.
        
        Args:
            call_sid: Twilio call SID
            
        Returns:
            Call status information
        """
        if not self.twilio_available:
            return None
        
        try:
            call = self.client.calls(call_sid).fetch()
            return {
                'sid': call.sid,
                'status': call.status,
                'duration': call.duration,
                'direction': call.direction,
                'to': call.to,
                'from': call.from_,
                'start_time': str(call.start_time),
                'end_time': str(call.end_time)
            }
        except Exception as e:
            print(f"Call status fetch failed: {e}")
            return None
    
    def handle_incoming_call(self, call_data: Dict) -> str:
        """
        Handle incoming webhook for voice calls.
        
        Args:
            call_data: Twilio webhook data
            
        Returns:
            TwiML response
        """
        # Extract speech input if any
        speech_result = call_data.get('SpeechResult', '')
        
        if speech_result:
            # Process the speech input through AQI meta-layer
            response_text = self._process_speech_input(speech_result)
        else:
            # Initial greeting
            response_text = "Hello! This is Alan from Signature Card Services. How can I help you today?"
        
        return self.generate_twiml_response(response_text)
    
    def _process_speech_input(self, speech: str) -> str:
        """
        Process speech input through AQI system.
        
        Args:
            speech: Transcribed speech
            
        Returns:
            Response text
        """
        # This would integrate with the meta-layer
        # For now, simple response
        if 'yes' in speech.lower():
            return "Great! Let me tell you about our Supreme Edge program that can save you up to $30,000 per year on processing fees."
        elif 'no' in speech.lower():
            return "I understand. Would you like me to follow up with some information via email instead?"
        else:
            return "Thank you for your interest. Our representative will be in touch soon to discuss how we can help your business."