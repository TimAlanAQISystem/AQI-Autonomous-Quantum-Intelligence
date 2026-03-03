#!/usr/bin/env python3
"""
AQI Video Renderer Module
Handles autonomous video rendering and scene composition using FFmpeg
"""

import os
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger('VideoRenderer')

class VideoRenderer:
    """Autonomous video rendering for AQI documentary production"""

    def __init__(self, media_root: Path):
        self.media_root = media_root
        self.ffmpeg_path = media_root / "ffmpeg" / "ffmpeg-8.0.1-essentials_build" / "bin" / "ffmpeg.exe"
        self.ffprobe_path = media_root / "ffmpeg" / "ffmpeg-8.0.1-essentials_build" / "bin" / "ffprobe.exe"
        self.output_root = media_root / "output" / "documentary"
        self.scenes_root = media_root / "output" / "scenes"

        # Color mapping for thematic backgrounds
        self.color_map = {
            'corporate': '2E3440',      # Dark blue-gray
            'innovation': '5E81AC',     # Blue
            'trust': 'A3BE8C',          # Green
            'authority': 'EBCB8B',      # Yellow
            'vision': 'D08770',         # Orange
            'transformation': 'B48EAD', # Purple
            'leadership': '88C0D0',     # Light blue
            'future': '81A1C1'          # Steel blue
        }

    def render_chapter_video(self, chapter_num: int, scene_files: List[str], voice_file: str) -> str:
        """
        Render complete chapter video with scenes and voice
        Returns path to final chapter video
        """
        logger.info(f"🎬 Rendering Chapter {chapter_num} video")

        chapter_dir = self.output_root / f"chapter_{chapter_num}"
        chapter_dir.mkdir(parents=True, exist_ok=True)

        temp_video = chapter_dir / f"chapter{chapter_num}_temp_video.mp4"
        final_video = chapter_dir / f"chapter{chapter_num}_final.mp4"

        try:
            # Step 1: Concatenate scene videos
            if scene_files:
                self._concatenate_scenes(scene_files, temp_video)
            else:
                # If no scenes, create a placeholder video
                self._create_placeholder_video(chapter_num, temp_video)

            # Step 2: Mix video with voice
            self._mux_audio_video(temp_video, voice_file, final_video)

            # Step 3: Cleanup temp files
            if temp_video.exists():
                temp_video.unlink()

            # Step 4: Verify output
            if not final_video.exists():
                raise RuntimeError(f"Final video not created: {final_video}")

            logger.info(f"✅ Chapter {chapter_num} video rendering complete: {final_video}")
            return str(final_video)

        except Exception as e:
            logger.error(f"❌ Video rendering failed for Chapter {chapter_num}: {e}")
            raise

    def _concatenate_scenes(self, scene_files: List[str], output_file: Path):
        """Concatenate multiple scene videos into one chapter video"""
        logger.info(f"Concatenating {len(scene_files)} scenes")

        # Create concat file
        concat_file = output_file.parent / "concat_list.txt"
        with open(concat_file, 'w') as f:
            for scene_file in scene_files:
                f.write(f"file '{scene_file}'\n")

        # FFmpeg concat command
        cmd = [
            str(self.ffmpeg_path), '-y', '-f', 'concat', '-safe', '0',
            '-i', str(concat_file),
            '-c', 'copy', str(output_file)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.media_root))
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg concat failed: {result.stderr}")

        # Cleanup
        concat_file.unlink()

    def _create_placeholder_video(self, chapter_num: int, output_file: Path):
        """Create a placeholder video when no scenes exist"""
        logger.info(f"Creating placeholder video for Chapter {chapter_num}")

        # Get chapter theme color
        theme_color = self._get_chapter_theme_color(chapter_num)

        # Create a simple colored background video (10 seconds for now)
        cmd = [
            str(self.ffmpeg_path), '-y',
            '-f', 'lavfi', '-i', f'color=c={theme_color}:s=1920x1080:d=10:r=25',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            str(output_file)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.media_root))
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg placeholder creation failed: {result.stderr}")

    def _mux_audio_video(self, video_file: Path, audio_file: str, output_file: Path):
        """Mux video with audio track"""
        logger.info(f"Muxing audio and video: {audio_file} + {video_file}")

        cmd = [
            str(self.ffmpeg_path), '-y',
            '-i', str(video_file),
            '-i', audio_file,
            '-c:v', 'copy',
            '-c:a', 'aac', '-b:a', '128k',
            '-shortest',
            str(output_file)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.media_root))
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg muxing failed: {result.stderr}")

    def _get_chapter_theme_color(self, chapter_num: int) -> str:
        """Get hex color for chapter theme"""
        themes = list(self.color_map.keys())
        theme = themes[(chapter_num - 1) % len(themes)]
        return self.color_map[theme]

    def ready(self) -> bool:
        """Check if video renderer is ready"""
        # Check if FFmpeg is available
        try:
            result = subprocess.run([str(self.ffmpeg_path), '-version'], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False