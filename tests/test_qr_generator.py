from io import BytesIO

from PIL import Image
import pytest

from qr_generator import (
    contrast_ratio_against_white,
    generate_qr,
    generate_qr_png,
    suggested_filename,
    validate_http_url,
)


def test_validate_http_url_accepts_http_and_https() -> None:
    assert validate_http_url(" https://example.com/path?x=1 ") == "https://example.com/path?x=1"
    assert validate_http_url("http://localhost:8501") == "http://localhost:8501"


@pytest.mark.parametrize(
    "value",
    ["", "example.com", "ftp://example.com", "https://", "https://example.com/a b"],
)
def test_validate_http_url_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        validate_http_url(value)


def test_generate_qr_png_is_rgba_and_transparent() -> None:
    result = generate_qr_png(
        "https://example.com",
        color="#6A0DAD",
        box_size=6,
        border=4,
        error_correction="M",
    )

    image = Image.open(BytesIO(result.png_bytes))
    assert image.format == "PNG"
    assert image.mode == "RGBA"
    assert image.size == (result.pixel_size, result.pixel_size)
    assert image.getpixel((0, 0))[3] == 0
    colors = {color for _, color in image.getcolors(maxcolors=4) or []}
    assert (106, 13, 173, 255) in colors


def test_svg_export_is_valid_svg_and_contains_qr_rectangles() -> None:
    result = generate_qr("https://example.com", color="#123456", box_size=8)
    svg = result.svg_bytes.decode("utf-8")
    assert svg.startswith('<?xml version="1.0"')
    assert '<svg xmlns="http://www.w3.org/2000/svg"' in svg
    assert 'fill="#123456"' in svg
    assert "<rect" in svg


def test_center_logo_area_is_white_in_png_and_svg() -> None:
    result = generate_qr(
        "https://example.com",
        box_size=10,
        error_correction="H",
        logo_area_percent=20,
    )
    image = Image.open(BytesIO(result.png_bytes)).convert("RGBA")
    center = image.getpixel((result.pixel_size // 2, result.pixel_size // 2))
    assert center == (255, 255, 255, 255)
    assert 'fill="#ffffff"' in result.svg_bytes.decode("utf-8")


def test_uploaded_logo_is_embedded_in_png_and_svg() -> None:
    logo = Image.new("RGBA", (40, 20), (255, 0, 0, 255))
    buffer = BytesIO()
    logo.save(buffer, format="PNG")

    result = generate_qr(
        "https://example.com",
        box_size=10,
        error_correction="H",
        logo_area_percent=24,
        logo_bytes=buffer.getvalue(),
    )
    image = Image.open(BytesIO(result.png_bytes)).convert("RGBA")
    assert image.getpixel((result.pixel_size // 2, result.pixel_size // 2))[:3] == (255, 0, 0)
    assert "data:image/png;base64," in result.svg_bytes.decode("utf-8")


def test_logo_area_percent_is_limited() -> None:
    with pytest.raises(ValueError, match="between 0% and 30%"):
        generate_qr("https://example.com", logo_area_percent=31)


def test_border_must_be_at_least_four_modules() -> None:
    with pytest.raises(ValueError, match="at least 4"):
        generate_qr_png("https://example.com", border=3)


def test_suggested_filename_uses_hostname_and_extension() -> None:
    assert suggested_filename("https://Docs.Example.com/page") == "docs.example.com-qr.png"
    assert suggested_filename("https://Docs.Example.com/page", "svg") == "docs.example.com-qr.svg"


def test_contrast_guidance_orders_dark_before_light() -> None:
    assert contrast_ratio_against_white("#000000") > contrast_ratio_against_white("#EEEEEE")
