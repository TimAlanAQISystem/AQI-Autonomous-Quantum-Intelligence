import time
from audio_manager import AudioManager

if __name__ == '__main__':
    print('=== AudioManager Standalone Test ===')
    # Create AudioManager in test mode (disables VAD so we capture raw chunks reliably)
    am = AudioManager(test_mode=True)
    devices = am.get_devices()
    print(f"Found {len(devices['input'])} input devices, {len(devices['output'])} output devices")
    print('Input devices (first 8):')
    for d in devices['input'][:8]:
        print(f"  [{d.index}] {d.name} ({d.hostapi})")
    print('Output devices (first 8):')
    for d in devices['output'][:8]:
        print(f"  [{d.index}] {d.name} ({d.hostapi})")

    # Start input capture for 3 seconds
    default_input, default_output = am.get_default_devices()
    print(f"Default devices: input={default_input}, output={default_output}")

    print('Starting input capture for 3 seconds...')
    try:
        am.start_input(default_input)
    except Exception as e:
        print(f'Failed to start input: {e}')
        am.shutdown()
        raise

    chunks = []
    start = time.time()
    while time.time() - start < 3.0:
        chunk = am.get_input_audio(timeout=0.2)
        if chunk is not None:
            chunks.append(chunk)
    am.stop_input()

    stats = am.get_statistics()
    print(f'Recorded {len(chunks)} chunks')
    print('Statistics:', stats)

    # If we have recorded something, try to play it back
    if chunks:
        import numpy as np
        print('Playing back recorded audio...')
        audio_np = np.concatenate(chunks).flatten()
        # Normalize
        maxv = float(abs(audio_np).max())
        if maxv > 0:
            audio_np = audio_np / maxv * 0.5
        am.start_output(default_output)
        am.play_audio(audio_np.astype('float32'))
        # wait for playback to finish
        time.sleep(1.0)
        am.stop_output()

    am.shutdown()
    print('Test complete')
