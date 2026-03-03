#!/usr/bin/env python3
"""
AQI Quality Verifier Module
Verifies video and audio quality for documentary production
"""

import os
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger('QualityVerifier')

class QualityVerifier:
    """Quality verification for AQI documentary production"""

    def __init__(self, media_root: Path):
        self.media_root = media_root
        self.ffprobe_path = media_root / "ffmpeg" / "ffmpeg-8.0.1-essentials_build" / "bin" / "ffprobe.exe"

    def verify_chapter(self, video_path: str) -> bool:
        """
        Verify individual chapter video quality
        Returns True if chapter passes all checks
        """
        logger.info(f"🔍 Verifying chapter video: {video_path}")

        video_file = Path(video_path)

        if not video_file.exists():
            logger.error(f"❌ Chapter video file does not exist: {video_path}")
            return False

        try:
            # Get video info
            info = self._get_video_info(video_file)

            # Check basic requirements
            checks = [
                self._check_video_exists(video_file),
                self._check_minimum_duration(info, 10),  # At least 10 seconds
                self._check_resolution(info, 1920, 1080),  # 1080p
                self._check_has_audio(info),
                self._check_video_codec(info),
            ]

            passed = all(checks)
            if passed:
                logger.info(f"✅ Chapter verification passed: {video_path}")
            else:
                logger.warning(f"⚠️ Chapter verification failed: {video_path}")

            return passed

        except Exception as e:
            logger.error(f"❌ Chapter verification error: {e}")
            return False

    def verify_final_documentary(self, video_path: str) -> bool:
        """
        Verify final documentary quality
        Returns True if documentary passes all checks
        """
        logger.info(f"🔍 Verifying final documentary: {video_path}")

        video_file = Path(video_path)

        if not video_file.exists():
            logger.error(f"❌ Final documentary file does not exist: {video_path}")
            return False

        try:
            # Get video info
            info = self._get_video_info(video_file)

            # Check comprehensive requirements
            checks = [
                self._check_video_exists(video_file),
                self._check_minimum_duration(info, 600),  # At least 10 minutes
                self._check_resolution(info, 1920, 1080),  # 1080p
                self._check_has_audio(info),
                self._check_video_codec(info),
                self._check_audio_codec(info),
            ]

            passed = all(checks)
            if passed:
                logger.info(f"✅ Final documentary verification passed: {video_path}")
                logger.info(f"📊 Final documentary: {info.get('duration', 0):.1f}s, "
                           f"{info.get('width', 0)}x{info.get('height', 0)}, "
                           f"{info.get('video_codec', 'unknown')}, "
                           f"{info.get('audio_codec', 'unknown')}")
            else:
                logger.error(f"❌ Final documentary verification failed: {video_path}")

            return passed

        except Exception as e:
            logger.error(f"❌ Final documentary verification error: {e}")
            return False

    def _get_video_info(self, video_file: Path) -> Dict:
        """Get video information using ffprobe"""
        cmd = [
            str(self.ffprobe_path), '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            str(video_file)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")

        data = json.loads(result.stdout)

        # Extract relevant info
        info = {
            'duration': float(data['format']['duration']),
            'size': int(data['format']['size']),
            'bitrate': data['format'].get('bit_rate', 'unknown')
        }

        # Get video stream info
        for stream in data['streams']:
            if stream['codec_type'] == 'video':
                info.update({
                    'width': stream['width'],
                    'height': stream['height'],
                    'video_codec': stream['codec_name'],
                    'fps': eval(stream['r_frame_rate']),
                    'pixel_format': stream.get('pix_fmt', 'unknown')
                })
            elif stream['codec_type'] == 'audio':
                info.update({
                    'audio_codec': stream['codec_name'],
                    'sample_rate': int(stream['sample_rate']),
                    'channels': stream.get('channels', 0)
                })

        return info

    def _check_video_exists(self, video_file: Path) -> bool:
        """Check if video file exists"""
        exists = video_file.exists()
        if not exists:
            logger.error(f"Video file does not exist: {video_file}")
        return exists

    def _check_minimum_duration(self, info: Dict, min_seconds: int) -> bool:
        """Check minimum duration"""
        duration = info.get('duration', 0)
        passed = duration >= min_seconds
        if not passed:
            logger.warning(f"Duration too short: {duration:.1f}s < {min_seconds}s")
        return passed

    def _check_resolution(self, info: Dict, expected_width: int, expected_height: int) -> bool:
        """Check video resolution"""
        width = info.get('width', 0)
        height = info.get('height', 0)
        passed = width >= expected_width and height >= expected_height
        if not passed:
            logger.warning(f"Resolution too low: {width}x{height} < {expected_width}x{expected_height}")
        return passed

    def _check_has_audio(self, info: Dict) -> bool:
        """Check if video has audio track"""
        has_audio = 'audio_codec' in info
        if not has_audio:
            logger.warning("Video missing audio track")
        return has_audio

    def _check_video_codec(self, info: Dict) -> bool:
        """Check video codec is H.264"""
        codec = info.get('video_codec', '')
        passed = codec == 'h264'
        if not passed:
            logger.warning(f"Unexpected video codec: {codec} (expected h264)")
        return passed

    def _check_audio_codec(self, info: Dict) -> bool:
        """Check audio codec is AAC"""
        codec = info.get('audio_codec', '')
        passed = codec == 'aac'
        if not passed:
            logger.warning(f"Unexpected audio codec: {codec} (expected aac)")
        return passed

    def ready(self) -> bool:
        """Check if quality verifier is ready"""
        # Check if ffprobe is available
        try:
            result = subprocess.run([str(self.ffprobe_path), '-version'], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False