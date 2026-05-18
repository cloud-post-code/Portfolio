import json
import os
import re

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from post_common import (
    APP_TITLE,
    OUTPUT_DIR,
    POST_MODES,
    SUPPORTED_UPLOAD_TYPES,
    ensure_session_state,
    generate_post_for_mode,
    parse_uploaded_file,
    read_recent_history,
    render_sidebar,
    save_generation,
)


def _segment_options(persona: dict) -> list[dict[str, str]]:
    return [segment for segment in persona.get("segmentation_outlines", []) if isinstance(segment, dict)]


def _segment_context(persona: dict, segment: dict[str, str] | None) -> str:
    parts = [
        f"Persona: {persona.get('persona_name', '').strip()}",
        persona.get("headline", "").strip(),
    ]
    if segment:
        parts.append(f"Selected segment: {segment.get('name', '').strip()}")
        parts.append(segment.get("outline", "").strip())
    parts.extend(
        [
            f"Core need: {persona.get('core_need', '').strip()}",
            f"Key fears: {persona.get('fears', '').strip()}",
            f"Where to reach her: {persona.get('watering_holes', '').strip()}",
        ]
    )
    return "\n".join(part for part in parts if part).strip()

def _is_placeholder_api_key(value: str) -> bool:
    normalized = value.strip().lower()
    return (
        "your_openai_api_key" in normalized
        or normalized in {"your_key_here", "sk-your-key-here", "not-needed"}
    )


def _clear_generation_state() -> None:
    st.session_state.generation_results = []


def _clear_input_widgets() -> None:
    st.session_state.raw_text_input = ""
    st.session_state.prompt_topic = ""
    st.session_state.prompt_location = ""
    st.session_state.prompt_cta = ""
    st.session_state.supporting_context_input = ""
    st.session_state.last_upload_signature = ""
    st.session_state.upload_widget_version = st.session_state.get("upload_widget_version", 0) + 1
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("audience_context_"):
            st.session_state[key] = ""


def _clean_label_value(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip(" -:|")).strip()


def _extract_labeled_value(text: str, labels: tuple[str, ...]) -> str:
    label_pattern = "|".join(re.escape(label) for label in labels)
    pattern = re.compile(rf"^\s*(?:{label_pattern})\s*[:\-]\s*(.+)$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(text)
    return _clean_label_value(match.group(1)) if match else ""


def _fallback_topic(uploaded_text: str, upload_names: list[str]) -> str:
    for line in uploaded_text.splitlines():
        clean = _clean_label_value(line.lstrip("#"))
        if not clean or clean.lower().startswith("source:"):
            continue
        if len(clean) <= 90:
            return clean
    if upload_names:
        stem = os.path.splitext(upload_names[0])[0]
        return _clean_label_value(stem.replace("_", " ").replace("-", " ")).title()
    return ""


def _fallback_cta(uploaded_text: str) -> str:
    cta_words = ("shop", "visit", "book", "sign up", "learn more", "contact", "join", "follow", "download")
    for line in uploaded_text.splitlines():
        clean = _clean_label_value(line)
        if clean and any(word in clean.lower() for word in cta_words):
            return clean
    return ""


def _autofill_prompt_values(uploaded_text: str, upload_names: list[str]) -> dict[str, str]:
    if not uploaded_text:
        return {}
    topic = _extract_labeled_value(uploaded_text, ("Topic", "Title", "Subject", "Campaign", "Post topic"))
    location = _extract_labeled_value(
        uploaded_text,
        ("Location", "Location/community", "Community", "City", "Market", "Region"),
    )
    cta = _extract_labeled_value(uploaded_text, ("CTA", "Desired CTA", "Call to action", "Call-to-action"))
    return {
        "topic": topic or _fallback_topic(uploaded_text, upload_names),
        "location": location,
        "cta": cta or _fallback_cta(uploaded_text),
    }


def _ai_autofill_prompt_values(
    *,
    api_key: str,
    model: str,
    uploaded_text: str,
    upload_names: list[str],
    theme: dict,
    persona: dict,
) -> dict[str, str]:
    client = OpenAI(api_key=api_key)
    source_excerpt = uploaded_text[:12000]
    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You infer prompt variables for a content generator. Return only JSON with "
                    'string keys: "topic", "location", and "cta". Keep topic concise and specific. '
                    "Use location/community only when the source or context supports it; otherwise "
                    "return an empty string. Infer a practical CTA that fits the uploaded content, "
                    "brand, and audience, even when no CTA is explicitly labeled."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Uploaded file names: {', '.join(upload_names)}\n\n"
                    f"Brand: {theme.get('brand_name', '')}\n"
                    f"Category: {theme.get('product_category', '')}\n"
                    f"Target audience: {theme.get('target_audience', '')}\n"
                    f"Persona: {persona.get('persona_name', '')} - {persona.get('headline', '')}\n\n"
                    f"Uploaded content:\n{source_excerpt}"
                ),
            },
        ],
    )
    raw_content = response.choices[0].message.content or "{}"
    parsed = json.loads(raw_content)
    return {
        "topic": _clean_label_value(str(parsed.get("topic", ""))),
        "location": _clean_label_value(str(parsed.get("location", ""))),
        "cta": _clean_label_value(str(parsed.get("cta", ""))),
    }


load_dotenv()

st.set_page_config(page_title=f"{APP_TITLE} · Generate", layout="wide")
ensure_session_state()
render_sidebar(show_theme_editor=True)
if "upload_widget_version" not in st.session_state:
    st.session_state.upload_widget_version = 0
if st.session_state.pop("clear_inputs_after_generation", False):
    _clear_input_widgets()

st.title("Post generator")
st.caption(
    "Generate platform-specific posts in separate API calls for each selected mode "
    "(Blog, LinkedIn, Facebook, Instagram)."
)

api_key = os.getenv("OPENAI_API_KEY", "").strip()
if not api_key:
    st.warning("Missing OPENAI_API_KEY. Add it to `.env` or your shell environment.")
elif _is_placeholder_api_key(api_key):
    st.warning("OPENAI_API_KEY still looks like a placeholder. Replace it with a real OpenAI API key.")

st.subheader("Select output modes")
selected_modes = st.multiselect(
    "Choose one or more outputs",
    options=list(POST_MODES),
    default=["blog"],
    format_func=lambda x: x.title(),
)

st.subheader("Content inputs")
raw_text = st.text_area(
    "Raw text input",
    placeholder="Paste notes, brainstorm, draft copy, call transcript, or context here...",
    height=180,
    key="raw_text_input",
)
uploads = st.file_uploader(
    "Upload supporting files",
    type=list(SUPPORTED_UPLOAD_TYPES),
    accept_multiple_files=True,
    help="Accepted: .md, .txt, .docx, .pdf",
    key=f"uploads_{st.session_state.upload_widget_version}",
)

uploaded_text_chunks: list[str] = []
upload_errors: list[str] = []
upload_names: list[str] = []
if uploads:
    for file in uploads:
        upload_names.append(file.name)
        try:
            parsed = parse_uploaded_file(file).strip()
            if parsed:
                uploaded_text_chunks.append(f"### Source: {file.name}\n{parsed}")
        except Exception as exc:
            upload_errors.append(f"{file.name}: {exc}")
    if upload_errors:
        st.error("Some files could not be parsed:\n- " + "\n- ".join(upload_errors))

uploaded_text = "\n\n".join(uploaded_text_chunks).strip()
prefill_supporting_context = "\n\n".join(part for part in [raw_text.strip(), uploaded_text] if part).strip()
upload_signature = "|".join(f"{file.name}:{file.size}" for file in uploads or [])
if uploaded_text and st.session_state.get("last_upload_signature") != upload_signature:
    autofill_values = {}
    if api_key and not _is_placeholder_api_key(api_key):
        try:
            with st.spinner("Using AI to autofill prompt variables..."):
                autofill_values = _ai_autofill_prompt_values(
                    api_key=api_key,
                    model=st.session_state.model_name,
                    uploaded_text=uploaded_text,
                    upload_names=upload_names,
                    theme=st.session_state.theme,
                    persona=st.session_state.persona,
                )
        except Exception as exc:
            st.warning(f"AI autofill failed, using basic autofill instead: {exc}")
    else:
        st.info("Add a valid OpenAI API key to use AI autofill. Using basic autofill for now.")
    if not any(autofill_values.values()):
        autofill_values = _autofill_prompt_values(uploaded_text, upload_names)
    for field, value in autofill_values.items():
        if value:
            st.session_state[f"prompt_{field}"] = value
    if prefill_supporting_context:
        st.session_state.supporting_context_input = prefill_supporting_context
    st.session_state.last_upload_signature = upload_signature

st.subheader("Prompt variables")
topic = st.text_input("Topic", key="prompt_topic")
location = st.text_input("Location/community", key="prompt_location")
cta = st.text_input("Desired CTA", key="prompt_cta")

persona = st.session_state.persona
segments = _segment_options(persona)
selected_segment: dict[str, str] | None = None
if segments:
    segment_names = [segment.get("name", "Untitled segment") for segment in segments]
    selected_segment_name = st.selectbox(
        "Persona segment",
        options=segment_names,
        help="Autofilled from the End_User_Profile segmentation outlines.",
    )
    selected_segment = next(
        (segment for segment in segments if segment.get("name", "Untitled segment") == selected_segment_name),
        segments[0],
    )
else:
    selected_segment_name = "Core persona"

audience_context = st.text_area(
    "Audience/persona context",
    value=_segment_context(persona, selected_segment),
    height=180,
    key=f"audience_context_{selected_segment_name}",
    help="Editable autofill from the Persona page. This is passed into the prompt as the target audience.",
)

supporting_context = st.text_area(
    "Supporting context (editable merged input)",
    value=prefill_supporting_context,
    height=200,
    key="supporting_context_input",
)

if "generation_results" not in st.session_state:
    st.session_state.generation_results = []

if st.button("Generate posts", type="primary", on_click=_clear_generation_state):
    if not api_key:
        st.error("OPENAI_API_KEY is required before generation.")
    elif _is_placeholder_api_key(api_key):
        st.error("Replace the placeholder OPENAI_API_KEY in `.env` with a real OpenAI API key before generation.")
    elif not selected_modes:
        st.error("Select at least one mode.")
    elif not topic.strip():
        st.error("Topic is required.")
    else:
        values = {
            "topic": topic.strip(),
            "primary_keyword": topic.strip(),
            "secondary_keywords": "",
            "audience": audience_context.strip(),
            "brand_name": st.session_state.theme.get("brand_name", "").strip(),
            "location": location.strip(),
            "cta": cta.strip(),
            "supporting_context": supporting_context.strip(),
            "content_goal": "engagement and clarity",
            "offer": st.session_state.theme.get("product_category", "").strip(),
            "industry": st.session_state.theme.get("product_category", "").strip(),
            "mission": st.session_state.theme.get("brand_overview", "").strip(),
            "milestone": "",
        }

        total_cost = 0.0
        progress = st.progress(0.0, text="Starting generation...")
        for idx, mode in enumerate(selected_modes):
            progress.progress(idx / max(len(selected_modes), 1), text=f"Generating {mode.title()}...")
            try:
                result = generate_post_for_mode(
                    api_key=api_key,
                    model=st.session_state.model_name,
                    mode=mode,
                    values=values,
                    theme=st.session_state.theme,
                    persona=st.session_state.persona,
                    input_cost_per_m=float(st.session_state.input_cost_per_m),
                    output_cost_per_m=float(st.session_state.output_cost_per_m),
                )
                files = save_generation(result, values, st.session_state.theme, st.session_state.persona)
                result["saved_files"] = files
                st.session_state.generation_results.append(result)
                total_cost += float(result["estimated_cost_usd"])
            except Exception as exc:
                st.error(f"{mode.title()} failed: {exc}")
        progress.progress(1.0, text="Done")
        st.caption(f"Combined estimated cost: `${total_cost:.6f}`")
        st.session_state.clear_inputs_after_generation = True
        st.rerun()

results = st.session_state.generation_results
if results:
    st.subheader("Generated outputs")
    total_prompt = sum(int(r["usage"]["prompt_tokens"]) for r in results)
    total_completion = sum(int(r["usage"]["completion_tokens"]) for r in results)
    total_tokens = sum(int(r["usage"]["total_tokens"]) for r in results)
    total_cost = sum(float(r["estimated_cost_usd"]) for r in results)
    st.markdown(
        f"- Input tokens: **{total_prompt}**  \n"
        f"- Output tokens: **{total_completion}**  \n"
        f"- Total tokens: **{total_tokens}**  \n"
        f"- Combined estimated cost: **${total_cost:.6f}**"
    )

    for result in results:
        with st.expander(f"{result['mode'].title()} · ${result['estimated_cost_usd']:.6f}", expanded=True):
            usage = result["usage"]
            st.caption(
                f"Prompt: {usage['prompt_tokens']} · Completion: {usage['completion_tokens']} "
                f"· Total: {usage['total_tokens']}"
            )
            st.markdown(result["output_text"])
            md_path = result["saved_files"]["markdown"]
            with open(md_path, "r", encoding="utf-8") as f:
                st.download_button(
                    f"Download {result['mode'].title()} markdown",
                    data=f.read(),
                    file_name=os.path.basename(md_path),
                    mime="text/markdown",
                )

st.divider()
st.subheader("Recent output history")
st.caption(f"Saved under `{OUTPUT_DIR}`")
history = read_recent_history()
if not history:
    st.info("No saved markdown outputs yet.")
else:
    for p in history:
        with st.expander(p.name):
            st.caption(str(p))
            st.code(p.read_text(encoding="utf-8")[:1200], language="markdown")
