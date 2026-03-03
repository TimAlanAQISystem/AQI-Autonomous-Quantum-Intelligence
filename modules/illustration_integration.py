"""
AQI Illustration Integration Wrapper
Bridges structured AQI illustration requests to rendering functions in illustration.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from illustration import AQIIllustration


class IllustrationRequestError(ValueError):
    """Raised when an illustration request is invalid."""


def _ensure_parent_dir(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _require_sequence(name: str, value: Any, length: int | None = None) -> Sequence[Any]:
    if not isinstance(value, Iterable):
        raise IllustrationRequestError(f"{name} must be a sequence")
    seq = list(value)
    if length is not None and len(seq) != length:
        raise IllustrationRequestError(f"{name} must have length {length}")
    return seq


def _validate_elements(elements: Any) -> List[Dict[str, Any]]:
    if not isinstance(elements, list):
        raise IllustrationRequestError("elements must be a list")
    validated: List[Dict[str, Any]] = []
    for idx, el in enumerate(elements):
        if not isinstance(el, dict):
            raise IllustrationRequestError(f"element {idx} must be an object")
        etype = el.get("type")
        if etype == "text":
            if "text" not in el or "position" not in el:
                raise IllustrationRequestError(f"text element {idx} requires text and position")
            _require_sequence("position", el["position"], 2)
        elif etype == "shape":
            if "shape" not in el or "coords" not in el:
                raise IllustrationRequestError(f"shape element {idx} requires shape and coords")
            _require_sequence("coords", el["coords"], 4)
        else:
            raise IllustrationRequestError(f"element {idx} has unsupported type {etype}")
        validated.append(el)
    return validated


def execute_illustration(request: Dict[str, Any]) -> Path:
    """Execute an illustration request and return the output path."""
    if not isinstance(request, dict):
        raise IllustrationRequestError("request must be a dict")

    mode = request.get("mode")
    output_path = request.get("output_path")
    if not output_path:
        raise IllustrationRequestError("output_path is required")

    path = _ensure_parent_dir(Path(output_path))
    dpi = int(request.get("dpi", 300))

    if mode == "simple_image":
        width = int(request.get("width", 800))
        height = int(request.get("height", 600))
        background = request.get("background", "white")
        AQIIllustration.create_simple_image(str(path), width=width, height=height, background=background, dpi=dpi)
    elif mode == "draw_elements":
        width = int(request.get("width", 800))
        height = int(request.get("height", 600))
        background = request.get("background", "white")
        elements = _validate_elements(request.get("elements"))
        AQIIllustration.draw_elements(
            str(path),
            elements=elements,
            width=width,
            height=height,
            background=background,
            dpi=dpi,
        )
    elif mode == "plot":
        x = _require_sequence("x", request.get("x"))
        y = _require_sequence("y", request.get("y"))
        if len(x) != len(y):
            raise IllustrationRequestError("x and y must have equal length")
        AQIIllustration.create_plot(str(path), x=x, y=y, dpi=dpi)
    else:
        raise IllustrationRequestError("mode must be one of: simple_image, draw_elements, plot")

    return path


__all__ = ["execute_illustration", "IllustrationRequestError"]
