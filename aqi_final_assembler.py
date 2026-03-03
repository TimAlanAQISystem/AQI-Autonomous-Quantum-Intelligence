#!/usr/bin/env python3
"""
AQI Final Assembler Module
Concatenates all chapter videos into the final documentary
"""

import os
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger('FinalAssembler')

class FinalAssembler:
    """Final documentary assembly for AQI production"""

    def __init__(self, media_root: Path):
        self.media_root = media_root
        self.ffmpeg_path = media_root / "ffmpeg" / "ffmpeg-8.0.1-essentials_build" / "bin" / "ffmpeg.exe"
        self.output_root = media_root / "output"

    def assemble_documentary(self, chapter_files: List[str], blueprint: Dict) -> str:
        """
        Assemble final documentary from all chapter videos
        Returns path to final documentary
        """
        logger.info("🎞️ Assembling final AQI documentary")

        final_output = self.output_root / "AQI_Documentary_Final.mp4"

        try:
            # Step 1: Create concat file
            concat_file = self._create_concat_file(chapter_files)

            # Step 2: Concatenate all chapters
            self._concatenate_videos(concat_file, final_output)

            # Step 3: Cleanup
            concat_file.unlink()

            # Step 4: Verify final video
            if not final_output.exists():
                raise RuntimeError(f"Final documentary not created: {final_output}")

            # Step 5: Get video info
            duration = self._get_video_duration(final_output)
            logger.info(f"✅ Final documentary assembled: {final_output} ({duration:.1f}s)")

            return str(final_output)

        except Exception as e:
            logger.error(f"❌ Final assembly failed: {e}")
            raise

    def _create_concat_file(self, chapter_files: List[str]) -> Path:
        """Create FFmpeg concat file"""
        concat_file = self.output_root / "chapter_concat_list.txt"

        with open(concat_file, 'w') as f:
            for chapter_file in chapter_files:
                # Ensure absolute path and proper escaping
                abs_path = Path(chapter_file).resolve()
                f.write(f"file '{abs_path}'\n")

        return concat_file

    def _concatenate_videos(self, concat_file: Path, output_file: Path):
        """Concatenate videos using FFmpeg"""
        logger.info(f"Concatenating {len(open(concat_file).readlines())} chapters")

        cmd = [
            str(self.ffmpeg_path), '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(concat_file),
            '-c', 'copy',  # Copy streams to avoid re-encoding
            '-avoid_negative_ts', 'make_zero',
            str(output_file)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.media_root))
        if result.returncode != 0:
            logger.error(f"FFmpeg concat stderr: {result.stderr}")
            raise RuntimeError(f"FFmpeg concatenation failed: {result.stderr}")

    def _get_video_duration(self, video_path: Path) -> float:
        """Get video duration using ffprobe"""
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            str(video_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data['format']['duration'])
        else:
            logger.warning(f"Could not get duration for {video_path}")
            return 0.0

    def ready(self) -> bool:
        """Check if final assembler is ready"""
        # Check if FFmpeg is available
        try:
            result = subprocess.run([str(self.ffmpeg_path), '-version'], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False