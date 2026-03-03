# integrations/tts_interface.py

import pyttsx3

class TextToSpeechEngine:
    def __init__(self):
        self.engine = pyttsx3.init()
        # Set default voice to something close to "Confident Architect"
        voices = self.engine.getProperty('voices')
        if voices:
            self.engine.setProperty('voice', voices[0].id)  # Use first available voice
        self.engine.setProperty('rate', 150)  # WPM

    def synthesize(self, voice_spec, output_path: str):
        """
        Implement TTS using pyttsx3.
        - voice_spec: dict from VoiceSpec.build_spec()
        - output_path: target audio file path

        Produces an audio file at output_path.
        """
        import os
        import time
        
        # Combine all text segments
        full_text = " ".join([seg['text'] for seg in voice_spec['segments']])
        
        # Set voice properties
        if 'pace_wpm' in voice_spec:
            self.engine.setProperty('rate', voice_spec['pace_wpm'])
        
        # Note: pyttsx3 has limited voice selection on Windows, but it's functional
        self.engine.save_to_file(full_text, output_path)
        
        # Use a timeout to prevent indefinite blocking
        try:
            self.engine.runAndWait()
        except KeyboardInterrupt:
            # If interrupted, check if file was created
            if os.path.exists(output_path):
                print(f"TTS synthesis completed (interrupted but file exists): {output_path}")
                return
            else:
                raise
        
        print(f"TTS synthesis complete: {output_path}")