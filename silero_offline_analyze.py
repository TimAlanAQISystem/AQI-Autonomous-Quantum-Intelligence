"""
Run Silero VAD offline on a WAV file and print timestamps + simple summary.

Usage:
    python silero_offline_analyze.py [path_to_wav] [threshold]

This script will:
- load the WAV (using torchaudio if available, otherwise wave+numpy)
- resample to 16000 Hz if needed (torchaudio preferred, otherwise a simple linear interp)
- load Silero VAD via torch.hub and call the provided `get_speech_timestamps` util
- print timestamps in samples and seconds and counts
"""
import sys
import os
import wave
import numpy as np
import torch

path = 'stability_capture_vad_debug.wav'
if len(sys.argv) > 1:
    path = sys.argv[1]
threshold = 0.25
if len(sys.argv) > 2:
    try:
        threshold = float(sys.argv[2])
    except Exception:
        pass

print(f"Analyzing: {path} (threshold={threshold})")
if not os.path.exists(path):
    print('File not found')
    sys.exit(2)

# Load audio
sr = None
audio = None
_has_torchaudio = False
try:
    import torchaudio
    _has_torchaudio = True
except Exception:
    _has_torchaudio = False

if _has_torchaudio:
    try:
        waveform, sr = torchaudio.load(path)
        # waveform: (channels, samples)
        if waveform.ndim > 1:
            audio = waveform.mean(dim=0).numpy()
        else:
            audio = waveform.numpy()
        sr = int(sr)
        print(f"Loaded with torchaudio: sr={sr}, samples={len(audio)}")
    except Exception as e:
        print('torchaudio load failed:', e)
        _has_torchaudio = False

if not _has_torchaudio:
    with wave.open(path, 'rb') as wf:
        nch = wf.getnchannels()
        sr = wf.getframerate()
        nframes = wf.getnframes()
        data = wf.readframes(nframes)
        arr = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32767.0
        if nch > 1:
            arr = arr.reshape(-1, nch).mean(axis=1)
        audio = arr
    print(f"Loaded with wave: sr={sr}, samples={len(audio)}")

# Resample to 16000 if needed
target_sr = 16000
if sr != target_sr:
    print(f"Resampling {sr} -> {target_sr}")
    if _has_torchaudio:
        try:
            resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=target_sr)
            tensor = torch.from_numpy(audio).unsqueeze(0)
            audio = resampler(tensor).squeeze(0).numpy()
            sr = target_sr
        except Exception as e:
            print('torchaudio resample failed:', e)
            # fallback to numpy interp
            duration = len(audio) / sr
            new_len = int(duration * target_sr)
            audio = np.interp(np.linspace(0, len(audio), new_len, endpoint=False), np.arange(len(audio)), audio).astype(np.float32)
            sr = target_sr
    else:
        duration = len(audio) / sr
        new_len = int(duration * target_sr)
        audio = np.interp(np.linspace(0, len(audio), new_len, endpoint=False), np.arange(len(audio)), audio).astype(np.float32)
        sr = target_sr

# Ensure float32 and 1D
audio = np.asarray(audio, dtype=np.float32).flatten()

# Load Silero VAD
print('Loading Silero VAD model via torch.hub...')
try:
    model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=False, onnx=False)
    get_speech_timestamps = utils[0]
    print('Silero utilities loaded')
except Exception as e:
    print('Failed to load Silero VAD:', e)
    sys.exit(3)

# Run get_speech_timestamps
try:
    audio_tensor = torch.from_numpy(audio)
    timestamps = get_speech_timestamps(audio_tensor, model, sampling_rate=target_sr, threshold=threshold)
    print('Timestamps:', timestamps)
    if timestamps:
        for seg in timestamps:
            start_s = seg['start'] / target_sr
            end_s = seg['end'] / target_sr
            print(f"Segment: {seg['start']}..{seg['end']} samples ({start_s:.3f}s - {end_s:.3f}s)")
    else:
        print('No speech timestamps detected')
    print(f"Total segments: {len(timestamps)}")
except Exception as e:
    print('get_speech_timestamps failed:', e)
    # As fallback, try the simple energy-based scan
    print('Falling back to energy scan...')
    window = int(0.032 * target_sr)
    hop = window
    segs = []
    for i in range(0, len(audio)-window+1, hop):
        w = audio[i:i+window]
        rms = float(np.sqrt(np.mean(w**2)))
        if rms > 0.02:
            segs.append((i, i+window, rms))
    print(f'Energy segments found: {len(segs)}')
    for s in segs[:10]:
        print(f"{s[0]}..{s[1]} rms={s[2]:.4f}")

print('Done')
