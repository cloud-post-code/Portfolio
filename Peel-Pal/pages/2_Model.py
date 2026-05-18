import os

import streamlit as st
from dotenv import load_dotenv

from studio_common import APP_TITLE, DEFAULT_MODEL, ensure_session_state, render_sidebar

load_dotenv()

st.set_page_config(page_title=f"{APP_TITLE} · Model", layout="wide")
ensure_session_state()
render_sidebar(show_theme_editor=True)

st.title("Model & generation settings")
st.caption("Choose the Gemini model and how many images to request per run.")

api_present = bool(os.getenv("GEMINI_API_KEY", "").strip())
if api_present:
    st.success("GEMINI_API_KEY is set.")
else:
    st.warning("GEMINI_API_KEY is not set. Add it to `.env` or your shell environment.")

model_input = st.text_input(
    "Gemini model ID",
    value=st.session_state.model_name,
    help="Use a model that supports image output.",
)
st.session_state.model_name = model_input.strip() or DEFAULT_MODEL

st.slider(
    "Images per generation run",
    min_value=1,
    max_value=12,
    key="image_count",
    help="One API request per image. Adjustable here or on **Generate** → Batch & resolution.",
)

st.divider()
st.markdown("### About models")
st.markdown(
    """
Gemini image generation uses models that return **image** response parts (multimodal output).

- **Default:** `gemini-2.5-flash-image` — native image output via `generateContent` ([model docs](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash-image)).
- Names and availability can change; check [Google AI Gemini docs](https://ai.google.dev/gemini-api/docs) for the latest image-capable models and quotas.

**Tips**

- If you see permission or model-not-found errors, confirm API access and that the model string matches your project.
- Larger batches mean more API calls (enable **Parallel API calls** on Generate to overlap requests).
- **Aspect ratio** and **Image size** (1K / 2K / 4K) are set on the Generate page.
"""
)
