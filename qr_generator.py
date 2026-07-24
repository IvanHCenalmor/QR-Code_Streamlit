"""Core utilities for generating transparent QR-code PNG images."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import re
from urllib.parse import urlparse

import qrcode
from PIL import Image, ImageColor, ImageDraw
from qrcode.exceptions import DataOverflowError


ERROR_CORRECTION_LEVELS = {
    "L": qrcode.constants.ERROR_CORRECT_L,
    "M": qrcode.constants.ERROR_CORRECT_M,
    "Q": qrcode.constants.ERROR_CORRECT_Q,
    "H": qrcode.constants.ERROR_CORRECT_H,
}


@dataclass(frozen=True)
class QRCodeResult:
    """Generated QR code and a few useful display properties."""

    png_bytes: bytes
    version: int
    module_count: int
    pixel_size: int


def validate_http_url(value: str) -> str:
    """Return a normalized HTTP(S) URL or raise ``ValueError``."""
    normalized = value.strip()
    if not normalized:
        raise ValueError("Please enter a URL.")
    if any(character.isspace() for character in normalized):
        raise ValueError("The URL cannot contain spaces. Encode spaces as %20.")

    parsed = urlparse(normalized)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("The URL must begin with http:// or https://.")
    if not parsed.netloc or parsed.hostname is None:
        raise ValueError("The URL must include a valid host name.")

    return normalized


def parse_hex_color(value: str) -> tuple[int, int, int, int]:
    """Convert a Pillow-compatible color to an opaque RGBA tuple."""
    try:
        red, green, blue = ImageColor.getrgb(value)
    except ValueError as exc:
        raise ValueError(
            "Choose a valid color, such as #111827, navy, or royalblue."
        ) from exc
    return red, green, blue, 255


def contrast_ratio_against_white(color: str) -> float:
    """Calculate WCAG-style contrast against white for scanability guidance."""
    red, green, blue, _ = parse_hex_color(color)

    def linearize(channel: int) -> float:
        value = channel / 255
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

    luminance = (
        0.2126 * linearize(red)
        + 0.7152 * linearize(green)
        + 0.0722 * linearize(blue)
    )
    return 1.05 / (luminance + 0.05)


def generate_qr_png(
    url: str,
    color: str = "#111827",
    box_size: int = 12,
    border: int = 4,
    error_correction: str = "M",
) -> QRCodeResult:
    """Generate a QR code with colored modules and a transparent background."""
    normalized_url = validate_http_url(url)
    rgba_color = parse_hex_color(color)

    if box_size < 1:
        raise ValueError("Box size must be at least 1 pixel.")
    if border < 4:
        raise ValueError("The quiet-zone border must be at least 4 modules.")
    if error_correction not in ERROR_CORRECTION_LEVELS:
        raise ValueError("Error correction must be one of L, M, Q, or H.")

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECTION_LEVELS[error_correction],
        box_size=1,
        border=border,
    )
    qr.add_data(normalized_url)

    try:
        qr.make(fit=True)
    except DataOverflowError as exc:
        raise ValueError("The URL is too long to fit in a QR code.") from exc

    matrix = qr.get_matrix()
    module_count = len(matrix)
    pixel_size = module_count * box_size

    image = Image.new("RGBA", (pixel_size, pixel_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    for row_index, row in enumerate(matrix):
        for column_index, is_dark in enumerate(row):
            if not is_dark:
                continue

            left = column_index * box_size
            top = row_index * box_size
            right = left + box_size - 1
            bottom = top + box_size - 1
            draw.rectangle((left, top, right, bottom), fill=rgba_color)

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)

    return QRCodeResult(
        png_bytes=buffer.getvalue(),
        version=int(qr.version),
        module_count=module_count,
        pixel_size=pixel_size,
    )


def suggested_filename(url: str) -> str:
    """Create a safe PNG file name based on the URL host."""
    normalized_url = validate_http_url(url)
    hostname = urlparse(normalized_url).hostname or "qr-code"
    stem = re.sub(r"[^A-Za-z0-9.-]+", "-", hostname).strip(".-").lower()
    return f"{stem or 'qr-code'}-qr.png"
