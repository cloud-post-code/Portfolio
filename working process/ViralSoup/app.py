import mimetypes
import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from viral_soup_common import (
    APP_TITLE,
    OUTPUT_DIR,
    VIRALITY_DEFAULT_ACTIVE_KEYS,
    VIRALITY_PROFILE_FLAVORS,
    VIRALITY_SLIDER_KEYS,
    auto_virality_sliders,
    ensure_session_state,
    infer_virality_sliders_from_ideas,
    meme_format_categories,
    meme_format_labels_for_category,
    random_virality_sliders,
    shuffle_virality_sliders,
    zero_virality_sliders,
    generate_caption_options,
    generate_gemini_meme_image,
    generate_meme_pack_step2,
    read_recent_history,
    save_meme,
    sliders_from_session,
)

load_dotenv()


def _current_meme_format_full() -> str:
    """First template in the first category (meme format pickers removed from UI)."""
    cats = meme_format_categories()
    if not cats:
        return ""
    opts = meme_format_labels_for_category(cats[0])
    return opts[0] if opts else ""


def _meme_campaign_context() -> tuple[str, str, str, str]:
    platform = "TikTok"
    humor_style = "absurd"
    meme_format = _current_meme_format_full()
    cultural_relevance = ""
    return platform, humor_style, meme_format, cultural_relevance


def _apply_smart_virality_to_session() -> None:
    vals = auto_virality_sliders(
        meme_format=_current_meme_format_full(),
        humor_style=st.session_state.get("meme_humor_style", "absurd"),
        platform=st.session_state.get("meme_platform", "TikTok"),
        profile_flavor=st.session_state.get("virality_profile_flavor", "Balanced smart"),
    )
    for k, v in vals.items():
        st.session_state[k] = v


def _apply_random_virality_to_session() -> None:
    vals = random_virality_sliders(
        meme_format=_current_meme_format_full(),
        humor_style=st.session_state.get("meme_humor_style", "absurd"),
        platform=st.session_state.get("meme_platform", "TikTok"),
    )
    for k, v in vals.items():
        st.session_state[k] = v


def _apply_shuffle_virality_to_session() -> None:
    for k, v in shuffle_virality_sliders().items():
        st.session_state[k] = v


def _apply_zero_virality_to_session() -> None:
    for k, v in zero_virality_sliders().items():
        st.session_state[k] = v


st.set_page_config(page_title=f"{APP_TITLE} · Build", layout="wide")
ensure_session_state()

openai_key = os.getenv("OPENAI_API_KEY", "").strip()
gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

st.title("Meme builder")
st.caption(
    "**Step 1:** OpenAI proposes 5 caption/text options. **Step 2:** pick one → OpenAI writes analysis + image prompt → "
    "**Gemini Nano Banana** renders the meme PNG."
)

if not openai_key:
    st.warning("Set **OPENAI_API_KEY** in `.env` or your environment.")
if not gemini_key:
    st.warning("Set **GEMINI_API_KEY** in `.env` or your environment.")

st.subheader("Reference inputs")
ex1, ex2 = st.columns([1, 1])
with ex1:
    example_upload = st.file_uploader(
        "Example meme (image)",
        type=["png", "jpg", "jpeg", "webp", "gif"],
        help="Optional. Shown to the model in Step 1 to match meme grammar and energy.",
        key="meme_example_upload",
    )
with ex2:
    example_text = st.text_area(
        "Example text (voice / reference copy)",
        placeholder="Paste sample lines, tone, or phrases that match your brand voice…",
        height=120,
        key="meme_example_text",
    )

example_bytes: bytes | None = None
example_mime = "image/png"
if example_upload is not None:
    example_bytes = example_upload.getvalue()
    guess, _ = mimetypes.guess_type(example_upload.name)
    if example_upload.type:
        example_mime = example_upload.type
    elif guess:
        example_mime = guess

platform, humor_style, meme_format, cultural_relevance = _meme_campaign_context()

st.subheader("Virality sliders (0–10)")
if st.session_state.pop("_virality_ideas_infer_flash", False):
    st.success(
        "Sliders updated from your brief — adjust any slider below. Auto-sync was turned off so inferred values stay until you turn it back on."
    )
st.caption(
    "**0** = off for that axis. Paste a **creative brief** below and use **Set sliders from ideas** to have OpenAI "
    "fill every slider (you can still drag them afterward). **Shuffle all** = random 0–10 each; **Random mix** = smart profile + small jitter; **All zero** clears."
)
st.text_area(
    "Creative brief / ideas (optional)",
    height=100,
    key="meme_virality_ideas",
    placeholder=(
        "Describe vibe, joke angle, what to avoid, platform energy, how bold to be… "
        "Example: cozy fake Instagram DM about a maker skipping lunch during holiday rush; "
        "wholesome; no dunking on customers; want it screenshot-friendly."
    ),
    help="Passed to Step 1 (caption options) and used when you click **Set sliders from ideas**.",
)
flavor_options = list(VIRALITY_PROFILE_FLAVORS.keys())

v_top1, v_top2 = st.columns([1.1, 1.4])
with v_top1:
    st.selectbox(
        "Smart profile flavor",
        options=flavor_options,
        key="virality_profile_flavor",
        help="Layered on top of format + humor + platform when you apply smart sliders.",
    )
with v_top2:
    st.checkbox(
        "Auto-sync sliders when format / humor / platform / flavor change",
        key="meme_auto_virality_sync",
        help="Updates all virality sliders to match the built-in meme defaults and flavor (each rerun). Turned off after **Set sliders from ideas** so inferred values stick.",
    )

v_btn1, v_btn2, v_btn3, v_btn4, v_btn5 = st.columns([1, 1, 1, 1, 1.15])
with v_btn1:
    if st.button("Apply smart sliders", type="secondary", use_container_width=True):
        _apply_smart_virality_to_session()
        st.rerun()
with v_btn2:
    if st.button("Random mix", type="secondary", use_container_width=True):
        _apply_random_virality_to_session()
        st.rerun()
with v_btn3:
    if st.button("Shuffle all", type="secondary", use_container_width=True):
        _apply_shuffle_virality_to_session()
        st.rerun()
with v_btn4:
    if st.button("All zero", type="secondary", use_container_width=True):
        _apply_zero_virality_to_session()
        st.rerun()
with v_btn5:
    if st.button("Set sliders from ideas", type="secondary", use_container_width=True):
        ideas_txt = (st.session_state.get("meme_virality_ideas") or "").strip()
        if not ideas_txt:
            st.warning("Add some text in **Creative brief / ideas** first.")
        elif not openai_key:
            st.error("OPENAI_API_KEY is required for this action.")
        else:
            with st.spinner("Inferring sliders from your brief…"):
                try:
                    _plat, _hum, _mf, _cult = _meme_campaign_context()
                    pack = infer_virality_sliders_from_ideas(
                        api_key=openai_key,
                        model=st.session_state.model_name.strip(),
                        ideas=ideas_txt,
                        platform=_plat,
                        humor_style=_hum,
                        meme_format=_mf,
                        cultural_relevance=_cult,
                        input_cost_per_m=float(st.session_state.input_cost_per_m),
                        output_cost_per_m=float(st.session_state.output_cost_per_m),
                    )
                    for k, v in pack["sliders"].items():
                        st.session_state[k] = v
                    st.session_state["meme_virality_inference_rationale"] = pack.get("rationale", "")
                    st.session_state["meme_virality_inference_meta"] = {
                        "usage": pack.get("usage_infer", {}),
                        "cost_usd": pack.get("estimated_cost_infer_usd", 0.0),
                        "model": pack.get("model", ""),
                    }
                    st.session_state["meme_auto_virality_sync"] = False
                    st.session_state["_virality_ideas_infer_flash"] = True
                    st.rerun()
                except Exception as exc:
                    st.error(f"Inference failed: {exc}")

if st.session_state.get("meme_virality_inference_rationale"):
    meta_inf = st.session_state.get("meme_virality_inference_meta") or {}
    with st.expander("Brief → sliders (model rationale)", expanded=False):
        st.markdown(st.session_state["meme_virality_inference_rationale"] or "_No rationale returned._")
        if meta_inf:
            u = meta_inf.get("usage", {})
            st.caption(
                f"Model: `{meta_inf.get('model', '')}` · "
                f"tokens in/out/total: {u.get('prompt_tokens', 0)} / {u.get('completion_tokens', 0)} / {u.get('total_tokens', 0)} · "
                f"~${float(meta_inf.get('cost_usd', 0) or 0):.6f}"
            )

if st.session_state.get("meme_auto_virality_sync"):
    _apply_smart_virality_to_session()

# ── Dimension picker ──────────────────────────────────────────────────────────
_key_to_label = {k: lbl for k, lbl, _ in VIRALITY_SLIDER_KEYS}
_all_keys = [k for k, _, _ in VIRALITY_SLIDER_KEYS]

# Default to previously saved selection; fall back to default 3 axes.
_default_active = st.session_state.get("virality_active_keys") or list(VIRALITY_DEFAULT_ACTIVE_KEYS)

st.multiselect(
    "Active dimensions (pick any you want — each one becomes a slider below)",
    options=_all_keys,
    default=_default_active,
    format_func=lambda k: _key_to_label.get(k, k),
    key="virality_active_keys",
    help="Select which virality axes are shown as sliders and sent to the model. You can choose as many or as few as you like.",
)

_active_keys: list[str] = st.session_state.get("virality_active_keys") or list(VIRALITY_DEFAULT_ACTIVE_KEYS)
_active_entries = [(k, lbl, hlp) for k, lbl, hlp in VIRALITY_SLIDER_KEYS if k in _active_keys]

if _active_entries:
    _ncols = min(3, len(_active_entries))
    cols = st.columns(_ncols)
    for i, (skey, label, help_txt) in enumerate(_active_entries):
        with cols[i % _ncols]:
            st.slider(label, min_value=0, max_value=10, key=skey, help=help_txt)
else:
    st.info("Select at least one dimension above to see sliders.")

# Build the slider dict — only active axes are passed to the model.
_all_sliders = sliders_from_session()
sliders = {k: v for k, v in _all_sliders.items() if k in _active_keys}

if "meme_step1_options" not in st.session_state:
    st.session_state.meme_step1_options = []

st.divider()
st.subheader("Step 1 — Caption options")
if st.button("Generate 5 options", type="primary", key="btn_step1"):
    if not openai_key:
        st.error("OPENAI_API_KEY is required.")
    else:
        with st.spinner("Calling OpenAI…"):
            try:
                result = generate_caption_options(
                    api_key=openai_key,
                    model=st.session_state.model_name.strip(),
                    example_image_bytes=example_bytes,
                    example_image_mime=example_mime,
                    creative_brief=(st.session_state.get("meme_virality_ideas") or "").strip(),
                    profile_flavor=str(st.session_state.get("virality_profile_flavor", "") or ""),
                    example_text=example_text.strip(),
                    sliders=sliders,
                    input_cost_per_m=float(st.session_state.input_cost_per_m),
                    output_cost_per_m=float(st.session_state.output_cost_per_m),
                )
                st.session_state.meme_step1_options = result["options"]
                st.session_state.meme_option_radio = 0
                st.session_state.meme_step1_meta = {
                    "usage": result["usage_step1"],
                    "cost_usd": result["estimated_cost_step1_usd"],
                    "model": result["model"],
                }
                st.success("Generated 5 options.")
            except Exception as exc:
                st.error(f"Step 1 failed: {exc}")

options = st.session_state.meme_step1_options
if options:
    meta = st.session_state.get("meme_step1_meta", {})
    if meta:
        u = meta.get("usage", {})
        st.caption(
            f"Model: `{meta.get('model', '')}` · "
            f"tokens in/out/total: {u.get('prompt_tokens', 0)} / {u.get('completion_tokens', 0)} / {u.get('total_tokens', 0)} · "
            f"~${meta.get('cost_usd', 0):.6f}"
        )

    labels: list[str] = []
    for idx, opt in enumerate(options):
        mt = str(opt.get("meme_text", "")).strip() or "(empty)"
        preview = mt.replace("\n", " ")
        if len(preview) > 72:
            preview = preview[:69] + "…"
        labels.append(f"Option {idx + 1}: {preview}")

    st.radio(
        "Pick one option",
        options=list(range(len(options))),
        format_func=lambda i: labels[i],
        key="meme_option_radio",
        horizontal=False,
    )
    choice = int(st.session_state.meme_option_radio)

    for idx, opt in enumerate(options):
        with st.expander(f"Option {idx + 1} — full detail", expanded=(idx == choice)):
            st.markdown(f"**Meme text**\n\n{opt.get('meme_text', '')}")
            st.markdown(f"**Why it works**\n\n{opt.get('why_it_works', '')}")
            vs = opt.get("viral_scores") or {}
            if isinstance(vs, dict):
                st.json(vs)
            st.caption(f"Format hint: {opt.get('format_hint', '')}")

st.divider()
st.subheader("Step 2 — Meme image")
if st.button("Generate meme (analysis + image)", type="primary", key="btn_step2", disabled=not options):
    if not openai_key or not gemini_key:
        st.error("Both OPENAI_API_KEY and GEMINI_API_KEY are required for Step 2.")
    elif not options:
        st.error("Run Step 1 first.")
    else:
        idx = min(max(int(st.session_state.get("meme_option_radio", 0)), 0), len(options) - 1)
        chosen = options[idx]
        with st.spinner("OpenAI → Gemini image…"):
            try:
                pack = generate_meme_pack_step2(
                    api_key=openai_key,
                    model=st.session_state.model_name.strip(),
                    chosen_option=chosen,
                    platform=platform,
                    humor_style=humor_style,
                    meme_format=meme_format,
                    cultural_relevance=cultural_relevance.strip(),
                    example_text=example_text.strip(),
                    sliders=sliders,
                    input_cost_per_m=float(st.session_state.input_cost_per_m),
                    output_cost_per_m=float(st.session_state.output_cost_per_m),
                )
                ar = pack.get("suggested_aspect_ratio") or st.session_state.meme_aspect_ratio
                if ar not in (
                    "1:1",
                    "2:3",
                    "3:2",
                    "3:4",
                    "4:3",
                    "9:16",
                    "16:9",
                    "21:9",
                ):
                    ar = st.session_state.meme_aspect_ratio

                img_bytes = generate_gemini_meme_image(
                    api_key=gemini_key,
                    model=st.session_state.gemini_model_name.strip(),
                    image_prompt=pack["image_prompt"],
                    negative_prompt=pack.get("negative_prompt", ""),
                    brand_voice="",
                    aspect_ratio=ar,
                    image_size=st.session_state.meme_image_size,
                )

                slug_src = str(pack.get("meme_text_final") or chosen.get("meme_text", "meme"))
                meta_save = {
                    "created_at": datetime.now().isoformat(),
                    "meme_slug_source": slug_src,
                    "openai_model": st.session_state.model_name,
                    "gemini_model": st.session_state.gemini_model_name,
                    "platform": platform,
                    "humor_style": humor_style,
                    "meme_format": meme_format,
                    "cultural_relevance": cultural_relevance.strip(),
                    "sliders": sliders,
                    "chosen_option_index": idx,
                    "chosen_option": chosen,
                    "step2_pack": {
                        "meme_analysis": pack["meme_analysis"],
                        "meme_text_final": pack.get("meme_text_final"),
                        "image_prompt": pack["image_prompt"],
                        "negative_prompt": pack.get("negative_prompt"),
                        "suggested_aspect_ratio": ar,
                    },
                    "usage_step2": pack.get("usage_step2"),
                    "estimated_cost_step2_usd": pack.get("estimated_cost_step2_usd"),
                    "step1_meta": st.session_state.get("meme_step1_meta"),
                    "output_dir": str(OUTPUT_DIR),
                }
                paths = save_meme(image_bytes=img_bytes, metadata=meta_save)
                st.session_state.meme_last_result = {
                    "image_bytes": img_bytes,
                    "pack": pack,
                    "paths": paths,
                    "aspect_ratio": ar,
                }
                st.success("Meme generated and saved.")
            except Exception as exc:
                st.error(f"Step 2 failed: {exc}")

last = st.session_state.get("meme_last_result")
if last:
    st.markdown("### Latest result")
    u2 = last["pack"].get("usage_step2", {})
    st.caption(
        f"Aspect: **{last.get('aspect_ratio', '')}** · "
        f"Step 2 tokens: {u2.get('prompt_tokens', 0)} / {u2.get('completion_tokens', 0)} · "
        f"~${last['pack'].get('estimated_cost_step2_usd', 0):.6f}"
    )
    st.image(last["image_bytes"], use_container_width=True)
    st.markdown(last["pack"]["meme_analysis"])
    with st.expander("Image prompt (for debugging / reuse)"):
        st.code(last["pack"]["image_prompt"], language="text")
    p = last.get("paths", {})
    if p.get("png"):
        st.caption(f"Saved: `{p['png']}`")

st.divider()
st.subheader("Recent memes")
st.caption(f"Folder: `{OUTPUT_DIR}`")
hist = read_recent_history(limit=24)
if not hist:
    st.info("No saved images yet.")
else:
    gcols = st.columns(4)
    for i, p in enumerate(hist):
        with gcols[i % 4]:
            st.image(str(p), caption=p.name, use_container_width=True)
