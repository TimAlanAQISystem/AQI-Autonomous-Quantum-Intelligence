"""
Stability recorder for AudioManager

Usage:
    python run_am_stability.py [seconds]

This script records audio using `AudioManager` for the specified number of seconds (default 600 = 10 minutes),
then writes the captured audio to `stability_capture.wav` in the current folder and prints statistics.
It uses `AudioManager(test_mode=True)` to ensure raw chunks are captured for diagnostics.
"""
import sys
import time
import wave
import numpy as np
from audio_manager import AudioManager


def float32_to_int16(x: np.ndarray) -> np.ndarray:
    # Clip then convert
    clipped = np.clip(x, -1.0, 1.0)
    ints = (clipped * 32767.0).astype(np.int16)
    return ints


if __name__ == '__main__':
    duration = 600
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            print('Invalid duration, using 600 seconds')

    print(f"Recording stability test for {duration} seconds...")
    am = AudioManager(test_mode=True)

    # Start input
    default_input, default_output = am.get_default_devices()
    am.start_input(default_input)

    collected = []
    start = time.time()
    try:
        while time.time() - start < duration:
            chunk = am.get_input_audio(timeout=1.0)
            if chunk is not None:
                collected.append(chunk)
    except KeyboardInterrupt:
        print('\nInterrupted by user')
    finally:
        am.stop_input()

    total_chunks = len(collected)
    print(f"Collected {total_chunks} chunks")

    if total_chunks == 0:
        print('No audio collected; check device and settings')
        am.shutdown()
        sys.exit(1)

    audio_np = np.concatenate(collected).flatten()

    # Normalize and convert to int16
    maxv = float(np.abs(audio_np).max())
    if maxv > 0:
        audio_np = audio_np / maxv * 0.9

    int16 = float32_to_int16(audio_np)

    out_path = 'stability_capture.wav'
    with wave.open(out_path, 'wb') as wf:
        wf.setnchannels(am.channels)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(am.sample_rate)
        wf.writeframes(int16.tobytes())

    print(f"Wrote {out_path} ({len(int16)} samples, {am.sample_rate} Hz)")
    print('Statistics:', am.get_statistics())

    am.shutdown()
    print('Stability test complete')
