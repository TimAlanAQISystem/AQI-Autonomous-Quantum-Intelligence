"""
Offline Silero VAD analyzer

Usage:
    python run_silero_offline.py <wav_path> [threshold]

Loads the Silero VAD model+utils and runs get_speech_timestamps on the provided WAV file.
Prints detected speech segments in samples and seconds.
"""
import sys
import wave
import numpy as np
import torch


def load_wav(path):
    with wave.open(path, 'rb') as wf:
        sr = wf.getframerate()
        nch = wf.getnchannels()
        nframes = wf.getnframes()
        data = wf.readframes(nframes)
        arr = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32767.0
        if nch > 1:
            arr = arr.reshape(-1, nch).mean(axis=1)
    return arr, sr


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python run_silero_offline.py <wav_path> [threshold]')
        sys.exit(1)

    path = sys.argv[1]
    threshold = 0.25
    if len(sys.argv) > 2:
        try:
            threshold = float(sys.argv[2])
        except Exception:
            pass

    print(f'Loading WAV: {path}')
    audio, sr = load_wav(path)
    print(f'Sample rate: {sr}, samples: {len(audio)}')

    print('Loading Silero VAD model via torch.hub...')
    try:
        model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad')
        get_speech_timestamps = utils[0]
        print('Silero loaded')
    except Exception as e:
        print('Failed to load Silero VAD:', e)
        sys.exit(2)

    try:
        audio_tensor = torch.from_numpy(audio.astype(np.float32))
        print(f'Running get_speech_timestamps (threshold={threshold})...')
        timestamps = get_speech_timestamps(audio_tensor, model, sampling_rate=sr, threshold=threshold)
        print('Timestamps (samples):', timestamps)
        if timestamps:
            print('\nDetected segments (seconds):')
            for seg in timestamps:
                s = seg['start'] / float(sr)
                e = seg['end'] / float(sr)
                print(f" - {s:.3f}s -> {e:.3f}s (samples {seg['start']} - {seg['end']})")
        else:
            print('No speech segments detected by Silero with current threshold.')
    except Exception as e:
        print('Error running get_speech_timestamps:', e)
        sys.exit(3)
