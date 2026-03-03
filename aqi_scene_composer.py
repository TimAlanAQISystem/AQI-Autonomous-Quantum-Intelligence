#!/usr/bin/env python3
"""
AQI Scene Composer Module
Generates individual scene videos for documentary chapters
"""

import os
import json
import subprocess
import logging
import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger('SceneComposer')

class SceneComposer:
    """Autonomous scene composition for AQI documentary production"""

    def __init__(self, media_root: Path):
        self.media_root = media_root
        self.ffmpeg_path = media_root / "ffmpeg" / "ffmpeg-8.0.1-essentials_build" / "bin" / "ffmpeg.exe"
        self.output_root = media_root / "output" / "scenes"
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

    def compose_chapter_scenes(self, chapter_num: int, chapter_data: Dict) -> List[str]:
        """
        Compose all scenes for a chapter
        Returns list of scene video file paths
        """
        logger.info(f"🎭 Composing scenes for Chapter {chapter_num}")

        chapter_scenes_dir = self.scenes_root / f"chapter_{chapter_num}"
        chapter_scenes_dir.mkdir(parents=True, exist_ok=True)

        scene_files = []

        # Get scenes for this chapter
        scenes = chapter_data.get('scenes', [])

        for scene in scenes:
            scene_num = scene['scene_number']
            scene_file = self._compose_scene(chapter_num, scene)
            if scene_file:
                scene_files.append(scene_file)

        logger.info(f"✅ Composed {len(scene_files)} scenes for Chapter {chapter_num}")
        return scene_files

    def _compose_scene(self, chapter_num: int, scene_data: Dict) -> Optional[str]:
        """Compose a single scene video"""
        scene_num = scene_data['scene_number']
        scene_text = scene_data.get('text', '')
        duration = scene_data.get('duration_seconds', 5)
        theme = scene_data.get('theme', 'corporate')

        logger.info(f"🎭 Composing scene {scene_num} (Chapter {chapter_num})")

        scene_filename = f"scene_{chapter_num}.{scene_num}.mp4"
        scene_path = self.scenes_root / f"chapter_{chapter_num}" / scene_filename

        try:
            # Get background color
            bg_color = self.color_map.get(theme, self.color_map['corporate'])

            # Wrap text for display
            wrapped_text = self._wrap_text_for_video(scene_text)

            # Create video with text overlay
            self._create_text_video(
                wrapped_text,
                bg_color,
                duration,
                scene_path
            )

            return str(scene_path)

        except Exception as e:
            logger.error(f"❌ Failed to compose scene {scene_num}: {e}")
            return None

    def _wrap_text_for_video(self, text: str, max_chars_per_line: int = 50) -> str:
        """Wrap text for video display"""
        # Simple text wrapping
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            if len(' '.join(current_line + [word])) <= max_chars_per_line:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        return '\n'.join(lines)

    def _create_text_video(self, text: str, bg_color: str, duration: int, output_path: Path):
        """Create video with text overlay using FFmpeg"""
        # Escape text for FFmpeg
        escaped_text = text.replace("'", "\\'").replace('"', '\\"')

        # FFmpeg command for text overlay video
        cmd = [
            str(self.ffmpeg_path), '-y',
            '-f', 'lavfi',
            '-i', f'color=c=0x{bg_color}:s=1920x1080:d={duration}:r=25',
            '-vf',
            f"drawtext=text='{escaped_text}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.5:boxborderw=10",
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.media_root))
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg text video creation failed: {result.stderr}")

    def ready(self) -> bool:
        """Check if scene composer is ready"""
        # Check if FFmpeg is available
        try:
            result = subprocess.run([str(self.ffmpeg_path), '-version'], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False