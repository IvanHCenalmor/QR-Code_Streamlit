"""Streamlit interface for the transparent QR-code generator."""

from __future__ import annotations

from io import BytesIO

from PIL import Image
import streamlit as st

from qr_generator import (
    contrast_ratio_against_white,
    generate_qr_png,
    suggested_filename,
)


st.set_page_config(
    page_title="Transparent QR Generator",
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

st.title("Transparent QR Code Generator")
st.write(
    "Turn an HTTP or HTTPS URL into a colored QR code. The downloaded PNG "
    "always has a transparent background."
)

with st.sidebar:
    st.header("How it works")
    st.write(
        "The URL is encoded locally into the QR matrix. This app does not open "
        "the address or send it to another service."
    )
    st.info(
        "Transparent QR codes scan best when placed on a plain, light background "
        "that preserves the empty quiet zone around the code."
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
            index=1,
            format_func=lambda value: {
                "L": "L — approximately 7%",
                "M": "M — approximately 15%",
                "Q": "Q — approximately 25%",
                "H": "H — approximately 30%",
            }[value],
            help="Higher levels tolerate more damage but produce denser codes.",
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

    submitted = st.form_submit_button(
        "Generate QR code",
        type="primary",
        icon=":material/qr_code_2:",
        width="stretch",
    )

if submitted:
    try:
        result = generate_qr_png(
            url=url,
            color=color,
            box_size=box_size,
            border=border,
            error_correction=error_correction,
        )
    except ValueError as exc:
        st.session_state.pop("generated_qr", None)
        st.error(str(exc))
    else:
        st.session_state["generated_qr"] = {
            "result": result,
            "contrast": contrast_ratio_against_white(color),
            "filename": suggested_filename(url),
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
        # Composite the transparent output on white for a predictable preview.
        qr_image = Image.open(BytesIO(result.png_bytes)).convert("RGBA")
        preview = Image.new("RGBA", qr_image.size, "white")
        preview.alpha_composite(qr_image)
        st.image(preview.convert("RGB"), caption="Preview on white", width=360)

    with details_column:
        st.subheader("Output details")
        st.metric("PNG dimensions", f"{result.pixel_size} × {result.pixel_size} px")
        st.metric("QR version", result.version)
        st.metric("Matrix with border", f"{result.module_count} × {result.module_count}")
        st.caption(f"Color contrast against white: {contrast:.2f}:1")

        st.download_button(
            "Download transparent PNG",
            data=result.png_bytes,
            file_name=generated["filename"],
            mime="image/png",
            type="primary",
            icon=":material/download:",
            on_click="ignore",
            width="stretch",
        )

    st.markdown(
        '<div class="qr-note"><strong>Placement tip:</strong> Keep the transparent '
        "quiet zone unobstructed, and avoid placing the PNG on photographs, gradients, "
        "or a background close to the selected QR color.</div>",
        unsafe_allow_html=True,
    )
else:
    st.caption("Adjust the settings and select **Generate QR code** to create the PNG.")
