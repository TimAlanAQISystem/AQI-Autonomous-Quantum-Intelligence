import os
import subprocess
from typing import List, Dict

class FFmpegVideoRenderer:
    def __init__(self, ffmpeg_path: str = "c:\\Users\\signa\\OneDrive\\Desktop\\Agent X\\aqi_media\\ffmpeg\\ffmpeg-8.0.1-essentials_build\\bin\\ffmpeg.exe"):
        self.ffmpeg_path = ffmpeg_path

    def render_scenes(self, render_plan: List[Dict], scene_specs: List[Dict], output_dir: str):
        os.makedirs(output_dir, exist_ok=True)
        rendered_files = []

        for spec in scene_specs:
            scene_id = spec["scene_id"]
            duration = spec.get("duration", 10.0)
            output_file = os.path.join(output_dir, f"scene_{scene_id:03}.mp4")

            # Build filter chain more carefully
            background = spec.get("background", {})
            bg_color = background.get("colors", ["#000000"])[0]

            # Start with input color, then add overlay filters
            vf_parts = []

            # Add element filters
            elements = spec.get("elements", [])
            for element in elements:
                element_type = element.get("type")

                if element_type == "text":
                    text_filter = self._build_text_filter(element)
                    if text_filter:
                        vf_parts.append(text_filter)

                elif element_type == "shape":
                    shape_filter = self._build_shape_filter(element)
                    if shape_filter:
                        vf_parts.append(shape_filter)

                elif element_type == "particles":
                    particle_filter = self._build_particle_filter(element)
                    if particle_filter:
                        vf_parts.append(particle_filter)

                elif element_type == "lines":
                    line_filter = self._build_line_filter(element)
                    if line_filter:
                        vf_parts.append(line_filter)

            # Join filters with commas, or use null if empty
            vf_filter = ",".join(vf_parts) if vf_parts else "null"

            cmd = [
                self.ffmpeg_path,
                "-f", "lavfi",
                "-i", f"color=c={bg_color}:s=1920x1080:d={duration}",
                "-vf", vf_filter,
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-t", str(duration),
                "-y", output_file
            ]

            print(f"Rendering scene {scene_id} with enhanced visuals...")
            subprocess.run(cmd, check=True)
            rendered_files.append(output_file)

        return rendered_files

    def _build_background_filter(self, background):
        """Build background filter based on type"""
        bg_type = background.get("type", "solid")
        colors = background.get("colors", ["#000000"])

        if bg_type == "gradient":
            # For now, use the first color as solid background
            # Gradients are complex in FFmpeg, so we'll use solid colors
            return [f"color=c={colors[0]}"]
        else:
            return [f"color=c={colors[0] if colors else '#000000'}"]

        return ["color=c=#000000"]

    def _build_element_filters(self, elements):
        """Build filters for visual elements"""
        filters = []

        for element in elements:
            element_type = element.get("type")

            if element_type == "text":
                text_filter = self._build_text_filter(element)
                if text_filter:
                    filters.append(text_filter)

            elif element_type == "shape":
                shape_filter = self._build_shape_filter(element)
                if shape_filter:
                    filters.append(shape_filter)

            elif element_type == "particles":
                particle_filter = self._build_particle_filter(element)
                if particle_filter:
                    filters.append(particle_filter)

            elif element_type == "lines":
                line_filter = self._build_line_filter(element)
                if line_filter:
                    filters.append(line_filter)

        return filters

    def _build_text_filter(self, element):
        """Build text overlay filter"""
        content = element.get("content", "")
        font = element.get("font", "Arial")
        size = element.get("size", 48)
        color = element.get("color", "#FFFFFF")
        x = element.get("position", {}).get("x", "(w-text_w)/2")
        y = element.get("position", {}).get("y", "(h-text_h)/2")

        # Escape special characters
        content = content.replace("'", "\\'").replace(":", "\\:")

        filter_str = f"drawtext=text='{content}':fontfile=/Windows/Fonts/arial.ttf:fontsize={size}:fontcolor={color}:x={x}:y={y}"

        if element.get("shadow"):
            filter_str += f",drawtext=text='{content}':fontfile=/Windows/Fonts/arial.ttf:fontsize={size}:fontcolor=black:x={x}+2:y={y}+2"

        if element.get("glow"):
            # Add glow effect with multiple offset text layers
            glow_color = "#00FFFF" if "AQI" in content else "#FFFFFF"
            filter_str += f",drawtext=text='{content}':fontfile=/Windows/Fonts/arial.ttf:fontsize={size}:fontcolor={glow_color}:x={x}-1:y={y}"
            filter_str += f",drawtext=text='{content}':fontfile=/Windows/Fonts/arial.ttf:fontsize={size}:fontcolor={glow_color}:x={x}+1:y={y}"
            filter_str += f",drawtext=text='{content}':fontfile=/Windows/Fonts/arial.ttf:fontsize={size}:fontcolor={glow_color}:x={x}:y={y}-1"
            filter_str += f",drawtext=text='{content}':fontfile=/Windows/Fonts/arial.ttf:fontsize={size}:fontcolor={glow_color}:x={x}:y={y}+1"

        return filter_str

    def _build_shape_filter(self, element):
        """Build shape drawing filter"""
        shape = element.get("shape", "circle")
        color = element.get("color", "#FFFFFF")
        size = element.get("size", 100)

        if shape == "circle":
            # Simple box approximation of circle
            return f"drawbox=x=400:y=200:w={size}:h={size}:color={color}@0.5:t=fill"
        elif shape == "hexagon":
            # Simple rectangle for hexagon
            return f"drawbox=x=800:y=300:w={size}:h={size}:color={color}@0.5:t=fill"

        return None

    def _build_particle_filter(self, element):
        """Build particle effect filter"""
        # Use simpler noise effect
        return "noise=alls=10:allf=t+u"

    def _build_line_filter(self, element):
        """Build line/grid drawing filter"""
        color = element.get("color", "#FFFFFF")
        thickness = element.get("thickness", 2)

        # Draw a simple grid
        return f"drawgrid=w=200:h=200:t={thickness}:c={color}@0.3"

        return None