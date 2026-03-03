"""
AQI Illustration Module
Provides deterministic, stateless helpers for generating images and plots.
Dependencies: Pillow, matplotlib.
"""

from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt


class PillowEngine:
    def __init__(self, width=800, height=600, background="white"):
        self.image = Image.new("RGB", (width, height), background)
        self.draw = ImageDraw.Draw(self.image)

    def draw_text(self, text, position, font_size=24, color="black"):
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()
        self.draw.text(position, text, fill=color, font=font)

    def draw_shape(self, shape_type, coords, color="black", thickness=2):
        if shape_type == "rectangle":
            self.draw.rectangle(coords, outline=color, width=thickness)
        elif shape_type == "ellipse":
            self.draw.ellipse(coords, outline=color, width=thickness)
        elif shape_type == "line":
            self.draw.line(coords, fill=color, width=thickness)

    def save(self, path, dpi=300):
        self.image.save(path, dpi=(dpi, dpi))


class MatplotlibEngine:
    def __init__(self, width=6, height=4, dpi=300):
        self.fig, self.ax = plt.subplots(figsize=(width, height), dpi=dpi)

    def plot_line(self, x, y, color="black", thickness=2):
        self.ax.plot(x, y, color=color, linewidth=thickness)

    def add_text(self, text, x, y, size=12, color="black"):
        self.ax.text(x, y, text, fontsize=size, color=color)

    def save(self, path):
        self.ax.set_axis_off()
        self.fig.savefig(path, bbox_inches="tight", pad_inches=0)
        plt.close(self.fig)


class AQIIllustration:
    """AQI-facing interface for deterministic rendering."""

    @staticmethod
    def create_simple_image(path, width=800, height=600, background="white", dpi=300):
        engine = PillowEngine(width, height, background)
        engine.save(path, dpi)

    @staticmethod
    def draw_elements(path, elements, width=800, height=600, background="white", dpi=300):
        """
        elements: list of dicts, e.g.
        {
            "type": "text", "text": "...", "position": [x, y],
            "size": 24, "color": "black"
        }
        {
            "type": "shape", "shape": "rectangle", "coords": [x1, y1, x2, y2],
            "color": "blue", "thickness": 3
        }
        """
        engine = PillowEngine(width, height, background)
        for el in elements:
            if el.get("type") == "text":
                engine.draw_text(
                    el["text"],
                    tuple(el["position"]),
                    font_size=el.get("size", 24),
                    color=el.get("color", "black"),
                )
            elif el.get("type") == "shape":
                engine.draw_shape(
                    el["shape"],
                    el["coords"],
                    color=el.get("color", "black"),
                    thickness=el.get("thickness", 2),
                )
        engine.save(path, dpi)

    @staticmethod
    def create_plot(path, x, y, dpi=300):
        engine = MatplotlibEngine(dpi=dpi)
        engine.plot_line(x, y)
        engine.save(path)
