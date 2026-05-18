import json

import streamlit as st

from studio_common import (
    APP_TITLE,
    clear_sidebar_theme_widget_keys,
    default_theme,
    ensure_session_state,
    render_sidebar,
)

st.set_page_config(page_title=f"{APP_TITLE} · Theme", layout="wide")
ensure_session_state()
render_sidebar(show_theme_editor=False)

st.title("Brand theme")
st.caption("Define colors, voice, and visual direction. These values feed the image generator.")

if st.button("Load sample theme"):
    st.session_state.theme = default_theme()
    clear_sidebar_theme_widget_keys()
    st.success("Loaded sample theme.")
    st.rerun()

t = st.session_state.theme

st.markdown("### Color system")
c1, c2 = st.columns(2)
primary_color = c1.color_picker("Primary color", value=t["primary_color"])
primary_inverse = c2.color_picker("Primary inverse", value=t["primary_inverse"])

c3, c4 = st.columns(2)
secondary_color = c3.color_picker("Secondary color", value=t["secondary_color"])
secondary_inverse = c4.color_picker("Secondary inverse", value=t["secondary_inverse"])

st.markdown("### Brand identity")
brand_name = st.text_input("Brand name", value=t["brand_name"])
tagline = st.text_input("Tagline", value=t["tagline"])
brand_overview = st.text_area(
    "Overview (2–4 sentences)",
    value=t["brand_overview"],
    height=120,
)

st.markdown("### Business profile")
product_category = st.text_input("Category", value=t["product_category"])
target_audience = st.text_area("Target audience", value=t["target_audience"], height=80)

st.markdown("### Voice & personality")
tone_text = st.text_area(
    "Tone (one per line)",
    value="\n".join(t["tones"]),
    height=120,
)
writing_style = st.text_area("Writing style", value=t["writing_style"], height=80)

st.markdown("### Visual identity")
background_style = st.text_input("Background style", value=t["background_style"])
imagery_style = st.text_input("Imagery style", value=t["imagery_style"])
typography_style = st.text_input("Typography", value=t["typography_style"])

st.session_state.theme = {
    "primary_color": primary_color,
    "primary_inverse": primary_inverse,
    "secondary_color": secondary_color,
    "secondary_inverse": secondary_inverse,
    "brand_name": brand_name.strip(),
    "tagline": tagline.strip(),
    "brand_overview": brand_overview.strip(),
    "product_category": product_category.strip(),
    "target_audience": target_audience.strip(),
    "tones": [line.strip() for line in tone_text.splitlines() if line.strip()],
    "writing_style": writing_style.strip(),
    "background_style": background_style.strip(),
    "imagery_style": imagery_style.strip(),
    "typography_style": typography_style.strip(),
}
clear_sidebar_theme_widget_keys()

st.divider()
st.markdown("### Import theme JSON")
theme_json = st.text_area(
    "Paste JSON to merge into the theme",
    placeholder='{"brand_name":"...", "primary_color":"#123456", ...}',
    height=140,
)
if st.button("Apply JSON"):
    try:
        parsed = json.loads(theme_json)
        st.session_state.theme = {**st.session_state.theme, **parsed}
        clear_sidebar_theme_widget_keys()
        st.success("Theme JSON applied.")
        st.rerun()
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON: {e}")
