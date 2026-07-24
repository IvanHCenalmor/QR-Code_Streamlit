from io import BytesIO

from PIL import Image
import pytest

from qr_generator import (
    contrast_ratio_against_white,
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


def test_border_must_be_at_least_four_modules() -> None:
    with pytest.raises(ValueError, match="at least 4"):
        generate_qr_png("https://example.com", border=3)


def test_suggested_filename_uses_hostname() -> None:
    assert suggested_filename("https://Docs.Example.com/page") == "docs.example.com-qr.png"


def test_contrast_guidance_orders_dark_before_light() -> None:
    assert contrast_ratio_against_white("#000000") > contrast_ratio_against_white("#EEEEEE")
