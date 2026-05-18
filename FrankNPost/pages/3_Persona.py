import json

import streamlit as st

from post_common import (
    APP_TITLE,
    clear_sidebar_persona_widget_keys,
    default_persona,
    ensure_session_state,
    render_sidebar,
)


def _segment_lines(segments: list[dict[str, str]]) -> str:
    return "\n".join(
        f"{segment.get('name', '').strip()}: {segment.get('outline', '').strip()}"
        for segment in segments
        if segment.get("name", "").strip() or segment.get("outline", "").strip()
    )


def _parse_segment_lines(raw_segments: str) -> list[dict[str, str]]:
    parsed: list[dict[str, str]] = []
    for line in raw_segments.splitlines():
        clean = line.strip()
        if not clean:
            continue
        if ":" in clean:
            name, outline = clean.split(":", 1)
            parsed.append({"name": name.strip(), "outline": outline.strip()})
        else:
            parsed.append({"name": clean, "outline": ""})
    return parsed


st.set_page_config(page_title=f"{APP_TITLE} · Persona", layout="wide")
ensure_session_state()
render_sidebar(show_theme_editor=True)

st.title("Audience persona")
st.caption("Edit the end-user profile and segmentation outlines used in every prompt.")

if st.button("Load sample persona"):
    st.session_state.persona = default_persona()
    clear_sidebar_persona_widget_keys()
    st.rerun()

p = st.session_state.persona

st.markdown("### Persona identity")
persona_name = st.text_input("Persona name", value=p["persona_name"])
headline = st.text_area("Headline", value=p["headline"], height=80)
at_a_glance = st.text_area("At a glance", value=p["at_a_glance"], height=100)
core_need = st.text_area("Core need", value=p["core_need"], height=100)

st.markdown("### Context & behavior")
selling_context = st.text_area("Selling context", value=p["selling_context"], height=120)
personality = st.text_area("Personality", value=p["personality"], height=80)
psychographics = st.text_area("Psychographics", value=p["psychographics"], height=100)
watering_holes = st.text_area("Watering holes", value=p["watering_holes"], height=100)

st.markdown("### Motivations")
aspirations = st.text_area("Aspirations", value=p["aspirations"], height=100)
fears = st.text_area("Fears", value=p["fears"], height=100)
day_in_life = st.text_area("Day in life", value=p["day_in_life"], height=120)

st.markdown("### Segmentation outlines")
raw_segments = st.text_area(
    "Segments (one per line as Name: Outline)",
    value=_segment_lines(p.get("segmentation_outlines", [])),
    height=180,
)

st.session_state.persona = {
    "persona_name": persona_name.strip(),
    "headline": headline.strip(),
    "at_a_glance": at_a_glance.strip(),
    "core_need": core_need.strip(),
    "selling_context": selling_context.strip(),
    "personality": personality.strip(),
    "aspirations": aspirations.strip(),
    "fears": fears.strip(),
    "psychographics": psychographics.strip(),
    "watering_holes": watering_holes.strip(),
    "day_in_life": day_in_life.strip(),
    "segmentation_outlines": _parse_segment_lines(raw_segments),
}
clear_sidebar_persona_widget_keys()

st.divider()
st.markdown("### Import persona JSON")
persona_json = st.text_area(
    "Paste JSON to merge into current persona",
    placeholder='{"persona_name":"...", "segmentation_outlines":[{"name":"...", "outline":"..."}]}',
    height=140,
)
if st.button("Apply JSON"):
    try:
        parsed = json.loads(persona_json)
        st.session_state.persona = {**st.session_state.persona, **parsed}
        clear_sidebar_persona_widget_keys()
        st.success("Persona JSON applied.")
        st.rerun()
    except json.JSONDecodeError as exc:
        st.error(f"Invalid JSON: {exc}")
