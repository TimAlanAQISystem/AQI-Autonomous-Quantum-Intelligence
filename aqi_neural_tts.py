from TTS.api import TTS
import os

class AQINeuralTTS:
    def __init__(self, model_name="tts_models/en/ljspeech/tacotron2-DDC", vocoder_name="tts_models/en/ljspeech/hifigan"):
        self.tts = TTS(model_name=model_name, vocoder_name=vocoder_name)

    def speak(self, text):
        self.tts.tts_to_file(text=text, file_path="aqi_tts_output.wav")
        os.system("start aqi_tts_output.wav")  # Windows: play the file

    def save_to_file(self, text, filename):
        self.tts.tts_to_file(text=text, file_path=filename)

# Example usage:
if __name__ == "__main__":
    tts = AQINeuralTTS()
    tts.speak("Alan is now quantum-powered and speaks with a high quality human voice.")
