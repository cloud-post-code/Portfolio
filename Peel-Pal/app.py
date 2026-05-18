import copy
import csv
import io
import os
import uuid

import streamlit as st
from dotenv import load_dotenv

from studio_common import (
    APP_TITLE,
    GEMINI_ASPECT_RATIOS,
    GEMINI_IMAGE_SIZES,
    OUTPUT_DIR,
    build_prompt,
    ensure_session_state,
    generate_images_batch,
    read_recent_history,
    render_sidebar,
    save_outputs,
)

load_dotenv()

st.set_page_config(page_title=f"{APP_TITLE} · Generate", layout="wide")
ensure_session_state()
render_sidebar(show_theme_editor=True)

if "process_notice" in st.session_state:
    st.info(st.session_state.process_notice)
    del st.session_state.process_notice


def _preview_label(user_prompt: str) -> str:
    preview = user_prompt.strip().replace("\n", " ")
    if len(preview) > 140:
        preview = preview[:137] + "…"
    return preview


def _full_prompt_label(user_prompt: str, extra_instructions: str) -> str:
    main = user_prompt.strip()
    extra = extra_instructions.strip()
    if not extra:
        return main
    return f"{main}\n\n---\n{extra}"


def _build_job(
    *,
    theme: dict,
    model_name: str,
    user_prompt: str,
    extra_instructions: str,
    allow_image_text: bool,
    aspect_ratio: str,
    image_size: str,
    image_count: int,
) -> dict:
    compiled_prompt = build_prompt(
        theme,
        user_prompt.strip(),
        extra_instructions,
        allow_image_text=allow_image_text,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
    )
    return {
        "id": str(uuid.uuid4()),
        "compiled_prompt": compiled_prompt,
        "full_prompt_label": _full_prompt_label(user_prompt, extra_instructions),
        "theme": copy.deepcopy(theme),
        "model_name": model_name,
        "aspect_ratio": aspect_ratio,
        "image_size": image_size,
        "allow_image_text": allow_image_text,
        "image_count": int(image_count),
        "preview": _preview_label(user_prompt),
    }


def _parse_prompts_csv_single_column(content: str) -> list[str]:
    """One prompt per row — first column only; extra columns are ignored."""
    reader = csv.reader(io.StringIO(content))
    out: list[str] = []
    for row in reader:
        if not row:
            continue
        p = row[0].strip()
        if p:
            out.append(p)
    return out


def _process_job_queue(api_key: str) -> None:
    """Drain `gen_job_queue`: generate and save each job. On full success, schedule form reset and rerun."""
    jobs_snapshot = list(st.session_state.gen_job_queue)
    st.session_state.gen_job_queue = []
    completed_images = 0
    progress = st.progress(0.0, text="Starting…")

    for idx, job in enumerate(jobs_snapshot):
        progress.progress(
            idx / max(len(jobs_snapshot), 1),
            text=f"Job {idx + 1} of {len(jobs_snapshot)}…",
        )
        try:
            generated = generate_images_batch(
                api_key=api_key,
                model=job["model_name"].strip(),
                compiled_prompt=job["compiled_prompt"],
                count=int(job["image_count"]),
                aspect_ratio=job["aspect_ratio"],
                image_size=job["image_size"],
            )
            save_outputs(images=generated, prompt=job["full_prompt_label"])
            completed_images += len(generated)
        except Exception as exc:
            st.session_state.gen_job_queue = [job] + jobs_snapshot[idx + 1 :]
            progress.progress(1.0, text="Stopped with error.")
            st.error(f"Job {idx + 1} failed: {exc}")
            st.warning("Remaining jobs were put back on the queue.")
            break
    else:
        progress.progress(1.0, text="Done.")
        # Must not mutate widget-bound keys here (widgets already ran); apply on next run.
        st.session_state["_defer_reset_prompt_only"] = True
        st.session_state.process_notice = (
            f"Processed **{len(jobs_snapshot)}** queue job(s), saved **{completed_images}** image(s). "
            "Prompt fields cleared."
        )
        st.rerun()


st.title("Image generation")
st.caption(
    "**Generate brand image** queues the current prompt & settings, clears the prompt fields, "
    "and runs the queue immediately. **Process queue** reruns any jobs still waiting (for example after an error). "
    "Images per run, aspect ratio, and image size stay as you last set them."
)

api_key = os.getenv("GEMINI_API_KEY", "").strip()
if not api_key:
    st.warning("Missing GEMINI_API_KEY. Add it to your environment or a local `.env` file.")

theme = st.session_state.theme
model_name = st.session_state.model_name.strip()
job_queue: list = st.session_state.gen_job_queue

# Streamlit forbids changing widget keys after those widgets render; reset before Prompt/Batch widgets.
if st.session_state.pop("_defer_reset_prompt_only", False):
    st.session_state.gen_main_prompt = ""
    st.session_state.gen_extra_prompt = ""
    st.session_state.gen_allow_image_text = False

st.subheader("Prompt")
user_prompt = st.text_area(
    "Main prompt — describe the image to create",
    placeholder="Example: A homepage hero image for a spring community event with warm morning light…",
    height=160,
    key="gen_main_prompt",
)

extra_instructions = st.text_area(
    "Extra instructions (optional)",
    placeholder="Aspect ratio hints, subjects to avoid, text to include, mood tweaks…",
    height=100,
    key="gen_extra_prompt",
)

st.checkbox(
    "Allow text in the image (headlines, short labels, minimal copy)",
    key="gen_allow_image_text",
    help="Off = no lettering, captions, watermarks, or typography — visuals only.",
)

with st.expander("Bulk prompts — CSV only", expanded=False):
    st.caption(
        "**CSV import only:** **one column** — each **row** is one prompt (uses column **A** only; "
        "ignore other columns). Blank rows and empty first cells are skipped. "
        "Every queued job shares the **same** theme, model, and batch settings below; "
        "**Extra instructions** above apply to each prompt."
    )
    bulk_file = st.file_uploader("Upload .csv", type=["csv"], key="bulk_file_upload")
    bulk_auto_run = st.checkbox(
        "After adding, process the queue immediately",
        key="bulk_auto_process",
        help="Requires GEMINI_API_KEY. Same as clicking **Process queue** after enqueue.",
    )
    bulk_cap = 250
    if st.button("Add all to queue", key="bulk_enqueue_btn"):
        chunks: list[str] = []
        if bulk_file is not None:
            raw = bulk_file.getvalue().decode("utf-8", errors="replace")
            chunks.extend(_parse_prompts_csv_single_column(raw))
        if not chunks:
            st.error("Upload a .csv with at least one non-empty value in column A.")
        elif len(chunks) > bulk_cap:
            st.error(f"Too many prompts at once (max {bulk_cap}). Split into smaller batches.")
        else:
            allow_txt = bool(st.session_state.gen_allow_image_text)
            ar = st.session_state.gen_aspect_ratio
            sz = st.session_state.gen_image_size
            ic = int(st.session_state.image_count)
            for p in chunks:
                st.session_state.gen_job_queue.append(
                    _build_job(
                        theme=theme,
                        model_name=model_name,
                        user_prompt=p,
                        extra_instructions=extra_instructions,
                        allow_image_text=allow_txt,
                        aspect_ratio=ar,
                        image_size=sz,
                        image_count=ic,
                    )
                )
            qn = len(st.session_state.gen_job_queue)
            notice = f"Queued **{len(chunks)}** prompt(s). Queue size: **{qn}**."
            if bulk_auto_run:
                if api_key:
                    st.session_state["_run_process_after_rerun"] = True
                else:
                    notice += (
                        " Set **GEMINI_API_KEY** to use “process immediately”, or click **Process queue** once configured."
                    )
            st.session_state.process_notice = notice
            st.rerun()


def _safe_option_index(options: tuple[str, ...], current: str, fallback: str) -> int:
    if current in options:
        return options.index(current)
    return options.index(fallback)


with st.expander("Batch & resolution", expanded=True):
    st.caption(
        "Several images = several API calls per queued job. "
        "Image size sets Gemini output scale when the model supports it."
    )
    bc1, bc2, bc3 = st.columns(3)
    with bc1:
        st.slider(
            "Images per run",
            min_value=1,
            max_value=12,
            key="image_count",
            help="Each image uses one generate request for this queue entry.",
        )
    with bc2:
        st.selectbox(
            "Aspect ratio",
            options=list(GEMINI_ASPECT_RATIOS),
            index=_safe_option_index(GEMINI_ASPECT_RATIOS, st.session_state.gen_aspect_ratio, "16:9"),
            key="gen_aspect_ratio",
        )
    with bc3:
        st.selectbox(
            "Image size",
            options=list(GEMINI_IMAGE_SIZES),
            index=_safe_option_index(GEMINI_IMAGE_SIZES, st.session_state.gen_image_size, "2K"),
            key="gen_image_size",
            help="1K / 2K / 4K resolution tier from the Gemini API.",
        )

col_gen, col_preview = st.columns([1, 1])

with col_gen:
    if st.button("Generate brand image", type="primary"):
        if not api_key:
            st.error("GEMINI_API_KEY is required before queueing.")
        elif not user_prompt.strip():
            st.error("Enter a main prompt above.")
        else:
            job = _build_job(
                theme=theme,
                model_name=model_name,
                user_prompt=user_prompt,
                extra_instructions=extra_instructions,
                allow_image_text=bool(st.session_state.gen_allow_image_text),
                aspect_ratio=st.session_state.gen_aspect_ratio,
                image_size=st.session_state.gen_image_size,
                image_count=int(st.session_state.image_count),
            )
            st.session_state.gen_job_queue.append(job)
            st.session_state["_defer_reset_prompt_only"] = True
            st.session_state["_run_process_after_rerun"] = True
            st.rerun()

with col_preview:
    st.caption(f"Model: `{model_name}`")
    _txt = "text on" if st.session_state.gen_allow_image_text else "no text"
    st.caption(
        f"Next job batch: **{int(st.session_state.image_count)}** · "
        f"{st.session_state.gen_aspect_ratio} · **{st.session_state.gen_image_size}** · {_txt}"
    )
    st.caption(f"**{len(job_queue)}** job(s) waiting in queue.")
    st.caption("Change the default model ID on the **Model** page.")

st.subheader("Queue")
if not job_queue:
    st.info("Queue is empty. Compose a prompt and click **Generate brand image** to add a job.")
else:
    for job in list(job_queue):
        rid = job["id"]
        c1, c2 = st.columns([5, 1])
        with c1:
            st.markdown(
                f"**{job['image_count']}×** · {job['aspect_ratio']} · **{job['image_size']}** · "
                f"{'text OK' if job['allow_image_text'] else 'no text'}"
            )
            st.caption(job["preview"])
        with c2:
            if st.button("Remove", key=f"queue_rm_{rid}"):
                st.session_state.gen_job_queue = [j for j in st.session_state.gen_job_queue if j["id"] != rid]
                st.rerun()

    pq1, pq2 = st.columns(2)
    with pq1:
        process_clicked = st.button(
            "Process queue",
            type="secondary",
            disabled=not api_key or len(job_queue) == 0,
            help="Runs every queued job in order (each job may issue multiple API calls).",
        )
    with pq2:
        if st.button("Clear queue", disabled=len(job_queue) == 0):
            st.session_state.gen_job_queue = []
            st.session_state.process_notice = "Queue cleared."
            st.rerun()

    if process_clicked:
        if not api_key:
            st.error("GEMINI_API_KEY is required.")
        else:
            _process_job_queue(api_key)

if st.session_state.pop("_run_process_after_rerun", False):
    if api_key:
        _process_job_queue(api_key)

st.divider()
st.subheader("Recent output history")
history = read_recent_history()
st.caption(
    f"**{len(history)}** image(s) under `{OUTPUT_DIR}` (all subfolders; PNG, JPEG, WebP, GIF), newest first."
)
if not history:
    st.info(f"No images found in `{OUTPUT_DIR}`. Generate saves PNGs here by default.")
else:
    cols = st.columns(3)
    for idx, image_file in enumerate(history):
        cols[idx % 3].image(str(image_file), caption=image_file.name, use_container_width=True)
