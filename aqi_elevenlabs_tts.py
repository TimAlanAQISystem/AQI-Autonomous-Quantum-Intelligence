import requests
import os

class ElevenLabsTTS:
    def __init__(self, api_key, voice_id=None):
        self.api_key = api_key
        self.voice_id = voice_id or "EXAVITQu4vr4xnSDxMaL"  # Default Adam voice
        self.base_url = "https://api.elevenlabs.io/v1/text-to-speech/"

    def synthesize(self, text, output_path="output.wav"):
        url = f"{self.base_url}{self.voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "voice_settings": {"stability": 0.3, "similarity_boost": 0.9}
        }
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"[ElevenLabs] Audio saved to {output_path}")
            return output_path
        else:
            print(f"[ElevenLabs] Error: {response.status_code} {response.text}")
            return None

# Example usage:
if __name__ == "__main__":
    api_key = os.getenv("ELEVENLABS_API_KEY")  # Set your API key in environment or replace here
    tts = ElevenLabsTTS(api_key, voice_id="EXAVITQu4vr4xnSDxMaL")
    tts.synthesize("Alan is now quantum-powered and ready to close your next deal.", "alan_elevenlabs.wav")
