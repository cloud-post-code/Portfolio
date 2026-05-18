import os

import streamlit as st

from viral_soup_common import (
    APP_TITLE,
    DEFAULT_GEMINI_IMAGE_MODEL,
    DEFAULT_INPUT_COST_PER_M,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_OUTPUT_COST_PER_M,
    GEMINI_ASPECT_RATIOS,
    GEMINI_IMAGE_SIZES,
    ensure_session_state,
)


st.set_page_config(page_title=f"{APP_TITLE} · Model", layout="wide")
ensure_session_state()

st.title("Models & pricing")
st.caption("OpenAI for captions/analysis; Gemini Nano Banana for meme images.")

c_key, g_key = st.columns(2)
with c_key:
    if os.getenv("OPENAI_API_KEY", "").strip():
        st.success("OPENAI_API_KEY is set.")
    else:
        st.warning("OPENAI_API_KEY is not set.")
with g_key:
    if os.getenv("GEMINI_API_KEY", "").strip():
        st.success("GEMINI_API_KEY is set.")
    else:
        st.warning("GEMINI_API_KEY is not set.")

st.markdown("### OpenAI (text / vision)")
openai_model = st.text_input("OpenAI model", value=st.session_state.model_name or DEFAULT_OPENAI_MODEL)
st.session_state.model_name = openai_model.strip() or DEFAULT_OPENAI_MODEL

r1, r2 = st.columns(2)
with r1:
    input_cost = st.number_input(
        "Input cost per 1M tokens (USD)",
        min_value=0.0,
        value=float(st.session_state.input_cost_per_m),
        step=0.01,
        format="%.4f",
    )
with r2:
    output_cost = st.number_input(
        "Output cost per 1M tokens (USD)",
        min_value=0.0,
        value=float(st.session_state.output_cost_per_m),
        step=0.01,
        format="%.4f",
    )
st.session_state.input_cost_per_m = float(input_cost)
st.session_state.output_cost_per_m = float(output_cost)

st.markdown("### Gemini (image — Nano Banana)")
gemini_model = st.text_input(
    "Gemini image model",
    value=st.session_state.gemini_model_name or DEFAULT_GEMINI_IMAGE_MODEL,
    help="Default: gemini-2.5-flash-image",
)
st.session_state.gemini_model_name = gemini_model.strip() or DEFAULT_GEMINI_IMAGE_MODEL

ar_idx = (
    list(GEMINI_ASPECT_RATIOS).index(st.session_state.meme_aspect_ratio)
    if st.session_state.meme_aspect_ratio in GEMINI_ASPECT_RATIOS
    else 0
)
sz_idx = (
    list(GEMINI_IMAGE_SIZES).index(st.session_state.meme_image_size)
    if st.session_state.meme_image_size in GEMINI_IMAGE_SIZES
    else 1
)

c3, c4 = st.columns(2)
with c3:
    st.selectbox(
        "Default aspect ratio",
        options=list(GEMINI_ASPECT_RATIOS),
        index=ar_idx,
        key="meme_aspect_ratio",
        help="Step 2 may override from the model’s suggested_aspect_ratio.",
    )
with c4:
    st.selectbox(
        "Image size tier",
        options=list(GEMINI_IMAGE_SIZES),
        index=sz_idx,
        key="meme_image_size",
        help="1K / 2K / 4K when supported by the Gemini API.",
    )

st.divider()
st.markdown("### Defaults")
st.markdown(
    f"- OpenAI default: `{DEFAULT_OPENAI_MODEL}` (change if your account uses a different slug).\n"
    f"- Gemini image default: `{DEFAULT_GEMINI_IMAGE_MODEL}`\n"
    f"- Estimated OpenAI pricing defaults: input `${DEFAULT_INPUT_COST_PER_M}` / output `${DEFAULT_OUTPUT_COST_PER_M}` per 1M tokens"
)
