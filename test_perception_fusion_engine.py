import unittest
from perception_fusion_engine import (
    PerceptionFusionEngine,
    PerceptionMode,
    PerceptionHealth,
)


BASE_CFG = {
    "stt_confidence_degraded_threshold": 0.75,
    "tts_drift_mild_threshold": 0.25,
    "tts_drift_severe_threshold": 0.60,
    "dead_air_warn_timeout_ms": 3000,
    "dead_air_timeout_ms": 5000,
    "connection_loss_warn_timeout_ms": 1500,
    "connection_loss_timeout_ms": 3000,
    "ivr_hard_threshold": 0.80,
    "voicemail_hard_threshold": 0.80,
}


class TestPerceptionFusionEngine(unittest.TestCase):
    def setUp(self):
        self.eng = PerceptionFusionEngine(BASE_CFG)

    def test_normal_ok(self):
        snap = self.eng.fuse(
            stt_confidence=0.95,
            tts_drift_score=0.1,
            inbound_silence_ms=500,
            packet_gap_ms=100,
            ivr_score=0.1,
            voicemail_score=0.1,
        )
        self.assertEqual(snap.mode, PerceptionMode.NORMAL)
        self.assertEqual(snap.health, PerceptionHealth.OK)

    def test_dead_air_critical(self):
        snap = self.eng.fuse(
            stt_confidence=0.9,
            tts_drift_score=0.1,
            inbound_silence_ms=6000,
            packet_gap_ms=100,
            ivr_score=0.1,
            voicemail_score=0.1,
        )
        self.assertEqual(snap.mode, PerceptionMode.DEAD_AIR)
        self.assertEqual(snap.health, PerceptionHealth.CRITICAL)

    def test_connection_loss_critical(self):
        snap = self.eng.fuse(
            stt_confidence=0.9,
            tts_drift_score=0.1,
            inbound_silence_ms=1000,
            packet_gap_ms=4000,
            ivr_score=0.1,
            voicemail_score=0.1,
        )
        self.assertEqual(snap.mode, PerceptionMode.CONNECTION_LOSS)
        self.assertEqual(snap.health, PerceptionHealth.CRITICAL)

    def test_audio_drift_critical(self):
        snap = self.eng.fuse(
            stt_confidence=0.9,
            tts_drift_score=0.7,
            inbound_silence_ms=1000,
            packet_gap_ms=100,
            ivr_score=0.1,
            voicemail_score=0.1,
        )
        self.assertEqual(snap.mode, PerceptionMode.AUDIO_DRIFT)
        self.assertEqual(snap.health, PerceptionHealth.CRITICAL)

    def test_ivr_detection(self):
        snap = self.eng.fuse(
            stt_confidence=0.9,
            tts_drift_score=0.1,
            inbound_silence_ms=500,
            packet_gap_ms=100,
            ivr_score=0.9,
            voicemail_score=0.1,
        )
        self.assertEqual(snap.mode, PerceptionMode.IVR)

    def test_degraded_stt(self):
        snap = self.eng.fuse(
            stt_confidence=0.6,
            tts_drift_score=0.1,
            inbound_silence_ms=500,
            packet_gap_ms=100,
            ivr_score=0.1,
            voicemail_score=0.1,
        )
        self.assertEqual(snap.health, PerceptionHealth.DEGRADED)


if __name__ == "__main__":
    unittest.main()
