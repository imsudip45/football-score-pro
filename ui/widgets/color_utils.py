import colorsys
from collections import Counter
from typing import TYPE_CHECKING, Any, Optional, Tuple

if TYPE_CHECKING:
    from PIL import Image as PILImage
else:
    try:
        from PIL import Image as PILImage  # type: ignore[import]
    except Exception:  # Pillow might not be installed yet
        PILImage = None  # type: ignore[misc, assignment]

# Alias for runtime use
Image: Any = PILImage


def _hex(rgb: Tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _is_background(rgb: Tuple[int, int, int]) -> bool:
    """Filter out near-white/near-black and very gray-ish tones likely from backgrounds."""
    r, g, b = rgb
    brightness = 0.299 * r + 0.587 * g + 0.114 * b
    if brightness > 240:  # near white
        return True
    if brightness < 15:  # near black
        return True
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    return s < 0.08 and v > 0.85


def _color_distance(c1: Tuple[int, int, int], c2: Tuple[int, int, int]) -> float:
    return sum((a - b) * (a - b) for a, b in zip(c1, c2)) ** 0.5


def extract_swatches_from_corner(
    image_path: str,
    swatch_size: int = 20,
    x_offset: int = 0,  # unused now
    y_offset: int = 0,  # unused now
) -> Tuple[str, Optional[str], str]:
    """
    Extract color 1 from top-left, color 2 from top-right. Returns: (color1_hex, color2_hex, mode)
    """
    if Image is None:
        raise RuntimeError("Pillow not available")
    im = Image.open(image_path).convert("RGB")
    w, h = im.size
    if w < swatch_size * 2 or h < swatch_size:
        raise ValueError("Image too small for swatch detection")
    # Color 1: sample at (0,0)
    box1 = (0, 0, swatch_size, swatch_size)
    # Color 2: sample at (w-swatch_size, 0)
    box2 = (w - swatch_size, 0, w, swatch_size)

    # Ensure in bounds
    def _box_in_bounds(box):
        x1, y1, x2, y2 = box
        return x1 >= 0 and y1 >= 0 and x2 <= w and y2 <= h

    if not _box_in_bounds(box2):
        raise ValueError("Swatch boxes out of bounds for top-left/top-right test")
    swatch1 = im.crop(box1)
    swatch2 = im.crop(box2)

    def average_color(swatch):
        pixels = list(swatch.getdata())
        n = len(pixels)
        r = sum(p[0] for p in pixels) // n
        g = sum(p[1] for p in pixels) // n
        b = sum(p[2] for p in pixels) // n
        return (r, g, b)

    c1 = average_color(swatch1)
    c2 = average_color(swatch2)

    mode = "double"
    c2_hex = _hex(c2)
    return _hex(c1), c2_hex, mode


def extract_bottom_left_color(
    image_path: str,
    swatch_size: int = 20,
) -> str:
    """
    Extract a solid swatch from the bottom-left corner of the kit image.
    Returns a hex string (e.g., "#FF0000").
    """
    if Image is None:
        raise RuntimeError("Pillow not available")
    im = Image.open(image_path).convert("RGB")
    w, h = im.size
    if w < swatch_size or h < swatch_size:
        raise ValueError("Image too small for bottom-left swatch detection")
    box = (0, max(0, h - swatch_size), swatch_size, h)
    swatch = im.crop(box)
    pixels: list[Any] = list(swatch.getdata())
    if not pixels:
        return "#000000"
    r = sum(p[0] for p in pixels) // len(pixels)
    g = sum(p[1] for p in pixels) // len(pixels)
    b = sum(p[2] for p in pixels) // len(pixels)
    return _hex((r, g, b))


def extract_top_colors(
    image_path: str,
    max_colors: int = 2,
    min_distance: float = 40.0,
    swatch_size: int = 20,
    x_offset: int = 0,
    y_offset: int = 0,
) -> Tuple[str, Optional[str], str]:
    """
    Returns (color1_hex, color2_hex_or_None, mode) where mode in {"single","double"}.
    Strategy:
      1) Try to read two color swatches from the top-left corner (kit images with swatches).
      2) If that fails, fall back to palette quantization + background filtering to find 1-2 distinct colors.
    """
    # First try the explicit swatch method
    try:
        return extract_swatches_from_corner(
            image_path, swatch_size=swatch_size, x_offset=x_offset, y_offset=y_offset
        )
    except Exception:
        pass

    # Fallback approach
    try:
        if Image is None:
            raise RuntimeError("Pillow not available")

        im = Image.open(image_path).convert("RGBA")
        im_small = im.copy()
        im_small.thumbnail((150, 150), Image.Resampling.LANCZOS)
        pixels: list[Any] = [p[:3] for p in im_small.getdata() if p[3] > 10]
        if not pixels:
            return "#2563EB", None, "single"

        pal = im_small.convert("P", palette=Image.Palette.ADAPTIVE, colors=32).convert(
            "RGB"
        )
        pal_pixels: list[Any] = list(pal.getdata())

        counts: Counter = Counter(rgb for rgb in pal_pixels if not _is_background(rgb))
        if not counts:
            counts = Counter(pal_pixels)

        top = [rgb for rgb, _ in counts.most_common(10)]
        if not top:
            return "#2563EB", None, "single"

        c1 = top[0]
        c2 = None
        for candidate in top[1:]:
            if _color_distance(c1, candidate) >= min_distance:
                c2 = candidate
                break

        if c2 is None:
            return _hex(c1), None, "single"
        return _hex(c1), _hex(c2), "double"
    except Exception:
        return "#2563EB", None, "single"
