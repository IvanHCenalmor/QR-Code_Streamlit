# Transparent QR Code Generator

A small Streamlit app that converts an HTTP or HTTPS URL into a colored QR code and lets the user download it as a PNG with a transparent background.

## Features

- URL validation for `http://` and `https://` addresses
- Interactive QR color picker
- Transparent PNG output
- Four error-correction levels
- Configurable module size and quiet zone
- Scanability warning for low-contrast colors
- No network request to the encoded URL
- Unit tests and GitHub Actions CI

## Run locally

Python 3.12 is recommended.

```bash
python -m venv .venv
```

Activate the environment:

```bash
# macOS or Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install and run:

```bash
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

Streamlit will print a local address, normally `http://localhost:8501`.

## Run the tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## Deploy on Streamlit Community Cloud

1. Create a GitHub repository and add these files to its root.
2. Push the repository to GitHub.
3. In Streamlit Community Cloud, create an app from that repository.
4. Select `streamlit_app.py` as the entrypoint.
5. Select Python 3.12 in the advanced deployment settings.

The root-level `requirements.txt` provides all packages required by the app.

## Project structure

```text
.
├── .github/workflows/tests.yml
├── .streamlit/config.toml
├── tests/test_qr_generator.py
├── .gitignore
├── LICENSE
├── README.md
├── qr_generator.py
├── requirements-dev.txt
├── requirements.txt
└── streamlit_app.py
```

## Transparent-background note

The quiet zone around a QR code must remain visually empty. Because the PNG is transparent, place it on a plain, light background with strong contrast against the chosen module color. Always test the final design with more than one scanner before publishing it.

## License

MIT
