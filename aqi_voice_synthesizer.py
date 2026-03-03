#!/usr/bin/env python3
"""
AQI Voice Synthesis Module
Handles autonomous voice generation for documentary chapters
"""

import os
import json
import pyttsx3
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger('VoiceSynthesizer')

class VoiceSynthesizer:
    """Autonomous voice synthesis for AQI documentary production"""

    def __init__(self, media_root: Path):
        self.media_root = media_root
        self.output_root = media_root / "output" / "documentary"
        self.engine = None
        self.voice_profile = None

        self._initialize_engine()

    def _initialize_engine(self):
        """Initialize TTS engine with AQI voice profile"""
        try:
            self.engine = pyttsx3.init()

            # Configure AQI voice profile
            voices = self.engine.getProperty('voices')
            # Use a clear, professional voice
            if voices:
                # Try to find a good English voice
                for voice in voices:
                    if 'english' in voice.name.lower() or 'us' in voice.name.lower():
                        self.engine.setProperty('voice', voice.id)
                        break

            # Set speech rate and volume for professional delivery
            self.engine.setProperty('rate', 180)  # Slightly slower for clarity
            self.engine.setProperty('volume', 0.9)

            logger.info("✅ Voice synthesis engine initialized")

        except Exception as e:
            logger.error(f"❌ Failed to initialize voice engine: {e}")
            raise

    def synthesize_chapter_voice(self, chapter_num: int, script: str) -> str:
        """
        Synthesize voice track for a chapter
        Returns path to generated audio file
        """
        logger.info(f"🎤 Synthesizing voice for Chapter {chapter_num}")

        # Create output directory
        chapter_dir = self.output_root / f"chapter_{chapter_num}"
        chapter_dir.mkdir(parents=True, exist_ok=True)

        output_file = chapter_dir / f"chapter{chapter_num}_voice.wav"

        try:
            # Generate speech
            self.engine.save_to_file(script, str(output_file))
            self.engine.runAndWait()

            # Verify file was created
            if not output_file.exists():
                raise RuntimeError(f"Voice file not created: {output_file}")

            logger.info(f"✅ Chapter {chapter_num} voice synthesis complete: {output_file}")
            return str(output_file)

        except Exception as e:
            logger.error(f"❌ Voice synthesis failed for Chapter {chapter_num}: {e}")
            raise

    def ready(self) -> bool:
        """Check if voice synthesizer is ready"""
        return self.engine is not None