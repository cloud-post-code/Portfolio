import os

import streamlit as st
from dotenv import load_dotenv

from post_common import APP_TITLE, DEFAULT_MODEL, ensure_session_state, render_sidebar

load_dotenv()

st.set_page_config(page_title=f"{APP_TITLE} · Model", layout="wide")
ensure_session_state()
render_sidebar(show_theme_editor=True)

st.title("Model & pricing")
st.caption("Configure model and estimated token pricing per 1M tokens.")

if os.getenv("OPENAI_API_KEY", "").strip():
    st.success("OPENAI_API_KEY is set.")
else:
    st.warning("OPENAI_API_KEY is not set.")

model = st.text_input("OpenAI model", value=st.session_state.model_name)
st.session_state.model_name = model.strip() or DEFAULT_MODEL

c1, c2 = st.columns(2)
with c1:
    input_cost = st.number_input(
        "Input cost per 1M tokens (USD)",
        min_value=0.0,
        value=float(st.session_state.input_cost_per_m),
        step=0.01,
        format="%.4f",
    )
with c2:
    output_cost = st.number_input(
        "Output cost per 1M tokens (USD)",
        min_value=0.0,
        value=float(st.session_state.output_cost_per_m),
        step=0.01,
        format="%.4f",
    )

st.session_state.input_cost_per_m = float(input_cost)
st.session_state.output_cost_per_m = float(output_cost)

st.divider()
st.markdown("### Default values")
st.markdown(
    "- Default model: `gpt-4o-mini`\n"
    "- Default estimated pricing: input `$0.15` / output `$0.60` per 1M tokens"
)
