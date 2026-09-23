"""Streamlit interface for the QR-code generator."""

from __future__ import annotations

from io import BytesIO

from PIL import Image
import streamlit as st

from qr_generator import (
    contrast_ratio_against_white,
    generate_qr,
    suggested_filename,
)


st.set_page_config(
    page_title="QR Generator",
    page_icon="▦",
    layout="centered",
)

st.markdown(
    """
    <style>
      .block-container {max-width: 900px; padding-top: 2.5rem;}
      [data-testid="stMetricValue"] {font-size: 1.15rem;}
      .qr-note {
        padding: 0.85rem 1rem;
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-radius: 0.75rem;
        margin-bottom: 1rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("QR Code Generator")
st.write(
    "Create a colored QR code, optionally reserve a white center area for a logo, "
    "and export the result as PNG or SVG."
)

with st.sidebar:
    st.header("How it works")
    st.write(
        "The URL is encoded locally into the QR matrix. This app does not open "
        "the address or send it to another service."
    )
    st.info(
        "If you add a logo area, use error correction H when possible and test the "
        "final QR with several scanners before publishing it."
    )

with st.form("qr_settings"):
    url = st.text_input(
        "URL",
        value="https://example.com",
        placeholder="https://example.com/page",
        help="Enter a complete HTTP or HTTPS URL.",
    )

    color_column, correction_column = st.columns(2)
    with color_column:
        color = st.color_picker(
            "QR color",
            value="#111827",
            help="Choose the color of the dark QR modules.",
        )
    with correction_column:
        error_correction = st.selectbox(
            "Error correction",
            options=("L", "M", "Q", "H"),
            index=3,
            format_func=lambda value: {
                "L": "L — approximately 7%",
                "M": "M — approximately 15%",
                "Q": "Q — approximately 25%",
                "H": "H — approximately 30%",
            }[value],
            help="Higher levels tolerate more obstruction but produce denser codes.",
        )

    size_column, border_column = st.columns(2)
    with size_column:
        box_size = st.slider(
            "Module size (pixels)",
            min_value=4,
            max_value=24,
            value=12,
            step=1,
        )
    with border_column:
        border = st.slider(
            "Quiet zone (modules)",
            min_value=4,
            max_value=10,
            value=4,
            step=1,
            help="Four modules is the standards-compliant minimum.",
        )

    st.subheader("Logo area")
    use_logo_area = st.checkbox(
        "Reserve white space in the center",
        value=False,
        help="Covers part of the QR matrix with a centered white square for branding.",
    )

    logo_area_percent = 0
    logo_file = None
    if use_logo_area:
        logo_area_percent = st.slider(
            "Center area width (% of QR code)",
            min_value=10,
            max_value=30,
            value=20,
            step=1,
            help="Smaller areas are generally easier for QR scanners to recover.",
        )
        logo_file = st.file_uploader(
            "Logo image (optional)",
            type=("png", "jpg", "jpeg", "webp"),
            help="If omitted, the exported QR will contain only the white center area.",
        )
        if error_correction != "H":
            st.warning("For QR codes with a center logo area, error correction H is recommended.")

    submitted = st.form_submit_button(
        "Generate QR code",
        type="primary",
        icon=":material/qr_code_2:",
        width="stretch",
    )

if submitted:
    try:
        logo_bytes = logo_file.getvalue() if logo_file is not None else None
        result = generate_qr(
            url=url,
            color=color,
            box_size=box_size,
            border=border,
            error_correction=error_correction,
            logo_area_percent=logo_area_percent,
            logo_bytes=logo_bytes,
        )
    except ValueError as exc:
        st.session_state.pop("generated_qr", None)
        st.error(str(exc))
    else:
        st.session_state["generated_qr"] = {
            "result": result,
            "contrast": contrast_ratio_against_white(color),
            "png_filename": suggested_filename(url, "png"),
            "svg_filename": suggested_filename(url, "svg"),
            "has_logo_area": logo_area_percent > 0,
        }

generated = st.session_state.get("generated_qr")
if generated is not None:
    result = generated["result"]
    contrast = generated["contrast"]

    if contrast < 3:
        st.warning(
            "This color has low contrast on white and may be difficult to scan. "
            "A darker color is recommended."
        )

    st.success("QR code generated.")

    preview_column, details_column = st.columns([1.25, 1])
    with preview_column:
        qr_image = Image.open(BytesIO(result.png_bytes)).convert("RGBA")
        preview = Image.new("RGBA", qr_image.size, "white")
        preview.alpha_composite(qr_image)
        st.image(preview.convert("RGB"), caption="Preview on white", width=360)

    with details_column:
        st.subheader("Output details")
        st.metric("PNG dimensions", f"{result.pixel_size} × {result.pixel_size} px")
        st.metric("QR version", result.version)
        st.metric("Matrix with border", f"{result.module_count} × {result.module_count}")
        if generated["has_logo_area"]:
            st.metric("Center white area", f"{result.logo_area_pixels} × {result.logo_area_pixels} px")
        st.caption(f"Color contrast against white: {contrast:.2f}:1")

        st.download_button(
            "Download PNG",
            data=result.png_bytes,
            file_name=generated["png_filename"],
            mime="image/png",
            type="primary",
            icon=":material/download:",
            on_click="ignore",
            width="stretch",
        )
        st.download_button(
            "Download SVG",
            data=result.svg_bytes,
            file_name=generated["svg_filename"],
            mime="image/svg+xml",
            icon=":material/download:",
            on_click="ignore",
            width="stretch",
        )

    st.markdown(
        '<div class="qr-note"><strong>Placement tip:</strong> Keep the outer quiet '
        "zone unobstructed. For branded QR codes, test the exported image at its final "
        "print/display size with more than one scanner.</div>",
        unsafe_allow_html=True,
    )
else:
    st.caption("Adjust the settings and select **Generate QR code** to create the exports.")
