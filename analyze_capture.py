import wave
import numpy as np
import sys

path = 'stability_capture_vad_debug.wav'
if len(sys.argv) > 1:
    path = sys.argv[1]

try:
    with wave.open(path, 'rb') as wf:
        nch = wf.getnchannels()
        sr = wf.getframerate()
        nframes = wf.getnframes()
        data = wf.readframes(nframes)
        arr = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32767.0
        if nch > 1:
            arr = arr.reshape(-1, nch).mean(axis=1)

    duration = nframes / sr
    peak = float(np.max(np.abs(arr)))
    rms = float(np.sqrt(np.mean(arr**2)))
    median = float(np.median(np.abs(arr)))
    silence_thresh = 0.01
    silent_frames = np.sum(np.abs(arr) < silence_thresh)
    silence_ratio = float(silent_frames) / len(arr)

    print(f"File: {path}")
    print(f"Duration: {duration:.2f}s, Sample rate: {sr}, Frames: {nframes}, Channels: {nch}")
    print(f"Peak: {peak:.6f}, RMS: {rms:.6f}, Median abs: {median:.6f}")
    print(f"Silence threshold: {silence_thresh}, Silent samples: {silent_frames}, Silence ratio: {silence_ratio:.3f}")

except FileNotFoundError:
    print(f"File not found: {path}")
    sys.exit(1)
except Exception as e:
    print(f"Error reading file: {e}")
    sys.exit(2)
