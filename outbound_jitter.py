"""
outbound_jitter.py — Outbound Jitter Smoothing Organ
=====================================================
AQI Classification: Experimental (governed)
Author: Tim (Founder) + Copilot (Instrument)
Created: February 19, 2026

PURPOSE:
    Smooth inter-frame delivery timing on outbound audio to reduce
    perceived lag and artifacts from upstream timing jitter.
    
    NOT a buffer — a SHAPE CORRECTOR.
    
    Current behavior: Frames sent as-fast-as-synthesized → clumping when
    TTS or Python event loop jitters.
    
    Target: Maintain a 40-80ms rolling micro-buffer. Smooth inter-frame
    intervals to ~20ms. Drop or compress only if buffer exceeds ceiling
    to prevent runaway lag.

INTEGRATION POINT:
    Sits between TTS output and WebSocket frame transmission in
    aqi_conversation_relay_server.py's audio streaming loop.

ARCHITECTURE:
    ┌─────────────┐    ┌─────────────────┐    ┌──────────────────┐
    │ TTS Output   │───▶│  JitterSmoother  │───▶│  WebSocket Send  │
    │ (bursty)     │    │  (shape correct) │    │  (steady 20ms)   │
    └─────────────┘    └─────────────────┘    └──────────────────┘
"""

import asyncio
import time
import logging
import collections
from dataclasses import dataclass
from typing import Optional, Deque, List

logger = logging.getLogger("outbound_jitter")

# =============================================================================
# CONFIGURATION
# =============================================================================
JITTER_SMOOTHING_ENABLED = False  # OFF by default — governed experiment
TARGET_INTERVAL_MS = 20.0         # Target inter-frame interval (20ms = standard)
MIN_BUFFER_MS = 40.0              # Minimum buffer before starting to drain
MAX_BUFFER_MS = 80.0              # Maximum buffer — above this, start fast-draining
EMERGENCY_CEILING_MS = 200.0      # Above this, drop frames to prevent runaway lag
FRAME_SIZE_BYTES = 160            # Standard mulaw 8kHz frame size (20ms @ 8000 samples/s)


@dataclass
class JitterStats:
    """Per-call jitter smoothing statistics."""
    frames_in: int = 0
    frames_out: int = 0
    frames_dropped: int = 0
    max_buffer_depth_ms: float = 0.0
    avg_input_interval_ms: float = 0.0
    avg_output_interval_ms: float = 0.0
    emergency_drains: int = 0
    smoothing_engaged_pct: float = 0.0


class JitterSmoother:
    """Outbound audio frame jitter smoother.
    
    Accepts audio frames as they arrive (bursty) and emits them
    at steady ~20ms intervals. Uses a small rolling buffer to
    absorb timing jitter without adding perceptible latency.
    
    Design principles:
    - Never add more than MAX_BUFFER_MS of latency
    - If buffer runs dry, pass through immediately (no stalling)
    - If buffer exceeds emergency ceiling, drop oldest frames
    - Measure everything for post-hoc analysis
    
    Usage:
        smoother = JitterSmoother()
        smoother.start()
        
        # In TTS output callback:
        smoother.enqueue(frame_bytes)
        
        # In send loop:
        async for frame in smoother.drain():
            await websocket.send(frame)
        
        # At call end:
        stats = smoother.finalize()
    """

    def __init__(self, enabled: bool = JITTER_SMOOTHING_ENABLED,
                 target_interval_ms: float = TARGET_INTERVAL_MS,
                 min_buffer_ms: float = MIN_BUFFER_MS,
                 max_buffer_ms: float = MAX_BUFFER_MS):
        self._enabled = enabled
        self._target_interval_ms = target_interval_ms
        self._min_buffer_ms = min_buffer_ms
        self._max_buffer_ms = max_buffer_ms
        self._buffer: Deque[bytes] = collections.deque()
        self._running = False
        self._drain_task: Optional[asyncio.Task] = None

        # Metrics
        self._frames_in = 0
        self._frames_out = 0
        self._frames_dropped = 0
        self._emergency_drains = 0
        self._input_times: Deque[float] = collections.deque(maxlen=100)
        self._output_times: Deque[float] = collections.deque(maxlen=100)
        self._max_buffer_depth = 0

        # Output queue for async consumers
        self._output_queue: asyncio.Queue = asyncio.Queue()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def buffer_depth_frames(self) -> int:
        return len(self._buffer)

    @property
    def buffer_depth_ms(self) -> float:
        return len(self._buffer) * (TARGET_INTERVAL_MS)

    def enqueue(self, frame: bytes):
        """Add a frame to the smoothing buffer.
        
        If smoothing is disabled, frame passes through immediately.
        If buffer exceeds emergency ceiling, oldest frames are dropped.
        """
        if not self._enabled:
            # Pass-through mode — no smoothing
            self._output_queue.put_nowait(frame)
            return

        self._frames_in += 1
        self._input_times.append(time.monotonic())

        # Emergency ceiling check
        buffer_ms = self.buffer_depth_ms
        if buffer_ms > EMERGENCY_CEILING_MS:
            # Drop oldest frames to get below max
            drop_count = max(1, int((buffer_ms - self._max_buffer_ms) / TARGET_INTERVAL_MS))
            for _ in range(min(drop_count, len(self._buffer))):
                self._buffer.popleft()
                self._frames_dropped += 1
            self._emergency_drains += 1
            logger.warning(
                f"[JITTER] Emergency drain: dropped {drop_count} frames, "
                f"buffer was {buffer_ms:.0f}ms"
            )

        self._buffer.append(frame)

        # Track max buffer depth
        current_depth = self.buffer_depth_ms
        if current_depth > self._max_buffer_depth:
            self._max_buffer_depth = current_depth

    def start(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        """Start the drain loop. Call once per call session."""
        if not self._enabled:
            return
        self._running = True
        if loop:
            self._drain_task = loop.create_task(self._drain_loop())
        else:
            try:
                loop = asyncio.get_running_loop()
                self._drain_task = loop.create_task(self._drain_loop())
            except RuntimeError:
                logger.warning("[JITTER] No running event loop — drain loop not started")

    async def _drain_loop(self):
        """Background loop that drains buffer at steady intervals."""
        logger.info("[JITTER] Drain loop started")
        while self._running:
            if self._buffer:
                # Fast drain if above max buffer
                if self.buffer_depth_ms > self._max_buffer_ms:
                    interval = self._target_interval_ms * 0.5  # Drain faster
                else:
                    interval = self._target_interval_ms

                frame = self._buffer.popleft()
                self._output_queue.put_nowait(frame)
                self._frames_out += 1
                self._output_times.append(time.monotonic())

                await asyncio.sleep(interval / 1000.0)
            else:
                # Buffer empty — short sleep and check again
                await asyncio.sleep(0.005)  # 5ms poll

    async def get_frame(self, timeout: float = 0.1) -> Optional[bytes]:
        """Get the next smoothed frame. Returns None on timeout."""
        try:
            return await asyncio.wait_for(self._output_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    def stop(self):
        """Stop the drain loop."""
        self._running = False
        if self._drain_task and not self._drain_task.done():
            self._drain_task.cancel()

    def finalize(self) -> JitterStats:
        """Stop and return statistics."""
        self.stop()

        # Compute average intervals
        avg_in = 0.0
        if len(self._input_times) >= 2:
            intervals = [
                (self._input_times[i] - self._input_times[i-1]) * 1000
                for i in range(1, len(self._input_times))
            ]
            avg_in = sum(intervals) / len(intervals) if intervals else 0.0

        avg_out = 0.0
        if len(self._output_times) >= 2:
            intervals = [
                (self._output_times[i] - self._output_times[i-1]) * 1000
                for i in range(1, len(self._output_times))
            ]
            avg_out = sum(intervals) / len(intervals) if intervals else 0.0

        # Smoothing engagement: % of time buffer was actively smoothing (>1 frame)
        total = self._frames_in
        engaged = max(0, self._frames_in - self._frames_out) if total > 0 else 0
        engagement_pct = (engaged / total * 100) if total > 0 else 0.0

        stats = JitterStats(
            frames_in=self._frames_in,
            frames_out=self._frames_out,
            frames_dropped=self._frames_dropped,
            max_buffer_depth_ms=self._max_buffer_depth,
            avg_input_interval_ms=avg_in,
            avg_output_interval_ms=avg_out,
            emergency_drains=self._emergency_drains,
            smoothing_engaged_pct=min(100.0, engagement_pct),
        )

        logger.info(
            f"[JITTER] Finalized: in={stats.frames_in}, out={stats.frames_out}, "
            f"dropped={stats.frames_dropped}, max_buffer={stats.max_buffer_depth_ms:.0f}ms, "
            f"avg_in_interval={stats.avg_input_interval_ms:.1f}ms, "
            f"avg_out_interval={stats.avg_output_interval_ms:.1f}ms"
        )
        return stats

    def reset(self):
        """Full reset for new call."""
        self.stop()
        self._buffer.clear()
        self._frames_in = 0
        self._frames_out = 0
        self._frames_dropped = 0
        self._emergency_drains = 0
        self._input_times.clear()
        self._output_times.clear()
        self._max_buffer_depth = 0
        while not self._output_queue.empty():
            try:
                self._output_queue.get_nowait()
            except asyncio.QueueEmpty:
                break


# =============================================================================
# PASSTHROUGH ADAPTER — Drop-in for when smoothing is disabled
# =============================================================================
class PassthroughJitter:
    """No-op adapter that matches JitterSmoother interface.
    Used when JITTER_SMOOTHING_ENABLED=False to avoid if/else branches
    in the relay server.
    """

    @property
    def enabled(self) -> bool:
        return False

    @property
    def buffer_depth_ms(self) -> float:
        return 0.0

    def enqueue(self, frame: bytes):
        pass  # Caller sends directly

    def start(self, loop=None):
        pass

    def stop(self):
        pass

    def finalize(self) -> JitterStats:
        return JitterStats()

    def reset(self):
        pass


def create_jitter_smoother(enabled: bool = JITTER_SMOOTHING_ENABLED) -> 'JitterSmoother':
    """Factory function. Returns active smoother or passthrough based on config."""
    if enabled:
        return JitterSmoother(enabled=True)
    return PassthroughJitter()


# =============================================================================
# MODULE SELF-TEST
# =============================================================================
if __name__ == "__main__":
    import struct

    logging.basicConfig(level=logging.DEBUG)
    print("=== Outbound Jitter Smoother Self-Test ===\n")

    async def _test():
        # Test 1: Bursty input → smooth output
        print("1. Testing jitter smoothing (bursty → steady)...")
        smoother = JitterSmoother(enabled=True, target_interval_ms=20,
                                  min_buffer_ms=40, max_buffer_ms=80)

        loop = asyncio.get_running_loop()
        smoother.start(loop)

        # Simulate bursty TTS output: 5 frames arrive in quick succession
        for i in range(5):
            frame = bytes([128] * FRAME_SIZE_BYTES)
            smoother.enqueue(frame)
            await asyncio.sleep(0.002)  # 2ms between frames (bursty)

        # Collect output frames and measure intervals
        output_times = []
        for _ in range(5):
            frame = await smoother.get_frame(timeout=0.5)
            if frame:
                output_times.append(time.monotonic())

        if len(output_times) >= 2:
            intervals = [(output_times[i] - output_times[i-1]) * 1000
                        for i in range(1, len(output_times))]
            avg = sum(intervals) / len(intervals)
            print(f"   Input: 5 frames in ~10ms (bursty)")
            print(f"   Output: 5 frames, avg interval = {avg:.1f}ms (target: 20ms)")

        stats = smoother.finalize()
        print(f"   Stats: in={stats.frames_in}, out={stats.frames_out}, "
              f"dropped={stats.frames_dropped}\n")

        # Test 2: Emergency drain
        print("2. Testing emergency ceiling...")
        smoother2 = JitterSmoother(enabled=True)
        # Fill buffer way past ceiling
        for i in range(15):  # 15 * 20ms = 300ms >> emergency ceiling
            smoother2.enqueue(bytes([128] * FRAME_SIZE_BYTES))
        print(f"   Buffer after 15 frames: {smoother2.buffer_depth_ms:.0f}ms")
        print(f"   Frames dropped: {smoother2._frames_dropped}")
        print(f"   Emergency drains: {smoother2._emergency_drains}")

        # Test 3: Passthrough mode
        print("\n3. Testing passthrough (disabled)...")
        pt = create_jitter_smoother(enabled=False)
        print(f"   Enabled: {pt.enabled}")
        pt.enqueue(bytes([128] * 160))
        stats = pt.finalize()
        print(f"   Stats: in={stats.frames_in}, out={stats.frames_out}")

        print("\n=== Self-Test Complete ===")

    asyncio.run(_test())
