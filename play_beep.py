"""
Utility function to play an attention beep
"""

import numpy as np
import sounddevice as sd

def play_attention_beep(frequency=1000, duration=0.3, volume=0.3):
    """
    Play a beep sound to get user's attention
    
    Args:
        frequency: Beep frequency in Hz (default: 1000Hz)
        duration: Beep duration in seconds (default: 0.3s)
        volume: Volume level 0.0-1.0 (default: 0.3)
    """
    try:
        sample_rate = 44100
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # Generate beep (sine wave with fade in/out to prevent clicks)
        beep = np.sin(2 * np.pi * frequency * t) * volume
        
        # Apply fade in/out
        fade_samples = int(sample_rate * 0.01)  # 10ms fade
        beep[:fade_samples] *= np.linspace(0, 1, fade_samples)
        beep[-fade_samples:] *= np.linspace(1, 0, fade_samples)
        
        # Play
        sd.play(beep, sample_rate)
        sd.wait()
        
    except Exception as e:
        print(f"Failed to play beep: {e}")

if __name__ == "__main__":
    print("Playing attention beep...")
    play_attention_beep()
    print("Done!")
