"""
Minimal AudioManager shim

This simplified AudioManager is intentionally lightweight and defensive. It
provides the minimal methods the runner and control API expect so the service
can start reliably on systems where the full audio stack or dependencies
may be missing or broken. It is suitable for stabilization and smoke testing
and can be replaced later with the full-featured implementation.
"""

import queue
import threading
import logging
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class AudioDevice:
    index: int
    name: str
    channels: int
    sample_rate: float
    is_input: bool
    is_output: bool
    hostapi: str

logger = logging.getLogger(__name__)


class AudioManager:
    """Lightweight AudioManager stub used for startup and tests.

    Methods mirror the real manager's surface but perform non-blocking
    no-op behavior so the agent can stabilize without requiring OS audio.
    """

    def __init__(self, sample_rate: int = 16000, channels: int = 1, chunk_duration_ms: int = 32, debug: bool = False, test_mode: bool = False, forward_raw: bool = True, vad_threshold: float = 0.25, vad_context_chunks: int = 10):
        self.sample_rate = int(sample_rate)
        self.channels = int(channels)
        self.chunk_duration_ms = int(chunk_duration_ms)
        self.chunk_size = int(self.sample_rate * self.chunk_duration_ms / 1000)

        # Lightweight queues used by the rest of the system
        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()

        # State
        self.is_recording = False
        self.is_playing = False
        self.test_mode = bool(test_mode)

        # Threads (not used in stub but kept for compatibility)
        self._stop_event = threading.Event()

        logger.info(f"AudioManager (stub) initialized: {self.sample_rate}Hz, {self.channels}ch, test_mode={self.test_mode}")

    def get_devices(self) -> Dict[str, List[AudioDevice]]:
        return {'input': [], 'output': []}

    def get_default_devices(self) -> Tuple[Optional[int], Optional[int]]:
        return None, None

    def start_input(self, device_id: Optional[int] = None):
        logger.info("AudioManager.start_input() called (stub)")
        self.is_recording = True

    def stop_input(self):
        logger.info("AudioManager.stop_input() called (stub)")
        self.is_recording = False

    def start_output(self, device_id: Optional[int] = None):
        logger.info("AudioManager.start_output() called (stub)")
        self.is_playing = True

    def stop_output(self):
        logger.info("AudioManager.stop_output() called (stub)")
        self.is_playing = False

    def play_audio(self, audio_data):
        # Accept audio_data but do not actually play
        try:
            self.output_queue.put_nowait(audio_data)
        except Exception:
            pass

    def get_input_audio(self, timeout: float = 0.1):
        try:
            return self.input_queue.get(timeout=timeout)
        except Exception:
            return None

    def get_statistics(self):
        return {
            'input_chunks_processed': 0,
            'output_chunks_played': 0,
            'speech_chunks_detected': 0,
            'silence_chunks_detected': 0,
            'input_queue_size': self.input_queue.qsize(),
            'output_queue_size': self.output_queue.qsize(),
        }

    def shutdown(self):
        logger.info("AudioManager.shutdown() called (stub)")
        self.stop_input()
        self.stop_output()


# Test function
if __name__ == "__main__":
    print("=== Audio Manager Test ===\n")
    
    # Create audio manager
    audio_mgr = AudioManager()
    
    # List devices
    print("Available Audio Devices:")
    devices = audio_mgr.get_devices()
    
    print("\nInput Devices:")
    for device in devices['input']:
        print(f"  [{device.index}] {device.name} ({device.hostapi})")
    
    print("\nOutput Devices:")
    for device in devices['output']:
        print(f"  [{device.index}] {device.name} ({device.hostapi})")
    
    # Get defaults
    input_id, output_id = audio_mgr.get_default_devices()
    print(f"\nDefault devices: Input={input_id}, Output={output_id}")
    
    # Test recording for 3 seconds
    print("\n--- Testing Recording (3 seconds) ---")
    audio_mgr.start_input()
    
    recorded_chunks = []
    start_time = time.time()
    
    while time.time() - start_time < 3.0:
        chunk = audio_mgr.get_input_audio(timeout=0.1)
        if chunk is not None:
            recorded_chunks.append(chunk)
    
    audio_mgr.stop_input()
    
    print(f"Recorded {len(recorded_chunks)} chunks")
    print(f"Statistics: {audio_mgr.get_statistics()}")
    
    # Test playback
    if recorded_chunks:
        print("\n--- Testing Playback ---")
        audio_mgr.start_output()
        
        for chunk in recorded_chunks:
            audio_mgr.play_audio(chunk.flatten())
            time.sleep(0.05)  # Match chunk duration
        
        time.sleep(0.5)  # Let playback finish
        audio_mgr.stop_output()
    
    # Cleanup
    audio_mgr.shutdown()
    print("\nTest complete!")
