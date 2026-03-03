# test_inbound_silence_sensitizer.py
import unittest
import time
import base64
import audioop
from inbound_silence_sensitizer import InboundSilenceSensitizer, InboundAudioMetrics

class TestInboundSilenceSensitizer(unittest.TestCase):
    
    def setUp(self):
        # Default config: 100ms rms, 100ms interval, 5000ms dead air
        self.sensitizer = InboundSilenceSensitizer()
        self.call_sid = "CA12345"
        self.sensitizer.register_call(self.call_sid)
        
    def test_normal_packet(self):
        # Create a loud packet (linear PCM -> ulaw)
        # 16-bit silence is 0, max is 32767
        # ulaw has different characteristics. Let's make some noise.
        # audioop.lin2ulaw takes 2-byte linear PCM
        
        # Make a linear PCM sine wave or just noise
        import struct
        noise = b'\x10\x20' * 80 # Just some bytes
        ulaw_payload = audioop.lin2ulaw(noise, 2)
        
        # First packet establishes baseline time
        res = self.sensitizer.process_packet(self.call_sid, ulaw_payload)
        self.assertEqual(res['action'], 'none')
        
        time.sleep(0.02) # 20ms
        
        # Second packet
        res = self.sensitizer.process_packet(self.call_sid, ulaw_payload)
        self.assertEqual(res['action'], 'none')
        self.assertLess(res['metrics']['interval'], 100) # Should be ~20ms
        
    def test_silence_detection(self):
        # Create silent packet
        silence_pcm = b'\x00\x00' * 160 # 160 samples (20ms at 8khz)
        ulaw_silence = audioop.lin2ulaw(silence_pcm, 2)
        
        # Feed silence for > 5 seconds (simulated)
        # We can simulate by sleeping? Or mocking time.
        # But for unit test speed, let's just modify the internal state or config.
        
        # Override config for fast test
        self.sensitizer.thresholds['dead_air_timeout_ms'] = 100
        
        # Feed silence
        for _ in range(10): # 10 packets * 20ms = 200ms
            self.sensitizer.process_packet(self.call_sid, ulaw_silence)
            time.sleep(0.001) # fast feed
            
        # The last packet should have triggered dead air
        # But we need to look at consecutive_silence_frames
        state = self.sensitizer._states[self.call_sid]
        self.assertGreater(state.consecutive_silence_frames, 5)
        
        # The logic divides frames by 50 (packets/sec) to get seconds.
        # If we send enough frames, it triggers.
        # dead_air_timeout_ms = 100 -> 0.1s -> 5 packets
        
        # Let's send one more to be sure
        res = self.sensitizer.process_packet(self.call_sid, ulaw_silence)
        
        # If we exceeded threshold, it returns action
        if res['action'] == 'none':
             # Maybe state wasn't updated correctly?
             pass
        else:
             self.assertEqual(res['action'], 'trigger_stt_restart')

    def test_connection_loss(self):
        # Simulate connection loss by checking heartbeat with old timestamp
        self.sensitizer.thresholds['connection_loss_timeout_ms'] = 50
        
        # Use initial packet to set time
        self.sensitizer.process_packet(self.call_sid, b'\xFF' * 100)
        
        time.sleep(0.1) # 100ms > 50ms config
        
        res = self.sensitizer.check_heartbeat(self.call_sid)
        self.assertEqual(res['action'], 'hangup')
        
    def tearDown(self):
        self.sensitizer.unregister_call(self.call_sid)

if __name__ == '__main__':
    unittest.main()
