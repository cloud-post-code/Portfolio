import base64
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

APP_TITLE = "Brand Image Studio"
# Image-capable model for generateContent (preview IDs often rotate / retire — see Model page).
DEFAULT_MODEL = "gemini-2.5-flash-image"
_DEPRECATED_IMAGE_MODELS = frozenset({"gemini-2.0-flash-preview-image-generation"})
_STUDIO_ROOT = Path(__file__).resolve().parent
# Default: app-local folder `Peel-Pal/Design Assets/Stock Images`.
_DEFAULT_OUTPUT_DIR = (_STUDIO_ROOT / "Design Assets" / "Stock Images").resolve()
OUTPUT_DIR = Path(
    os.environ.get("BRAND_IMAGE_OUTPUT_DIR", str(_DEFAULT_OUTPUT_DIR))
).expanduser().resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Fallback targets if the Streamlit context has no page registry yet.
NAV_PAGE_MAIN = (_STUDIO_ROOT / "app.py").resolve()
NAV_PAGE_THEME = (_STUDIO_ROOT / "pages" / "1_Theme.py").resolve()
NAV_PAGE_MODEL = (_STUDIO_ROOT / "pages" / "2_Model.py").resolve()

GEMINI_ASPECT_RATIOS = ("1:1", "2:3", "3:2", "3:4", "4:3", "9:16", "16:9", "21:9")
GEMINI_IMAGE_SIZES = ("1K", "2K", "4K")


def default_theme() -> Dict[str, Any]:
    # Brand voice from Main Street Text; palette: user primaries + Supplier.html tan (--cream-dark).
    return {
        "primary_color": "#2d722d",
        "primary_inverse": "#ffffff",
        "secondary_color": "#f1ead9",
        "secondary_inverse": "#000000",
        "brand_name": "Main Street",
        "tagline": "The shop that runs itself so you can keep making.",
        "brand_overview": (
            "Main Street is an all-in-one storefront for makers who want to spend more time "
            "creating and less time managing their business—listing from a single photo, "
            "managing inventory across online and in-person sales, and automating marketing. "
            "We exist for artists, makers, and independent creative businesses surviving and "
            "thriving in the age of AI: putting powerful tools in their hands so they can "
            "grow sustainable businesses without losing the joy, originality, and human "
            "connection behind what they make."
        ),
        "product_category": "All-in-one storefront for handmade goods & independent makers",
        "target_audience": (
            "Independent makers and small-scale artisans: ceramics, candles, textiles, jewelry, "
            "baked goods, and similar handmade categories; sellers who run online shops and "
            "physical markets or pop-ups; people whose craft is central to identity and livelihood "
            "and who want to grow without sacrificing creative time."
        ),
        "tones": [
            "Human-centered",
            "Warm",
            "Empowering",
            "Independent",
            "Hopeful about craft",
        ],
        "writing_style": (
            "Clear and supportive; speaks maker-to-maker. Practical about business without "
            "cold corporate tone. Honors handmade work and uniqueness; technology framed as "
            "something that serves the artist, not replaces them."
        ),
        "background_style": (
            "Warm tan paper (#f1ead9 / Supplier --cream-dark) with lighter cream (#faf6ed) lifts; "
            "soft green (#2d722d) accents; natural daylight on a studio desk—never sterile gray tech UI."
        ),
        "imagery_style": (
            "Authentic studios, markets, and maker tables; handcrafted goods in natural light; "
            "human hands, texture, and personality—editorial lifestyle, community-forward, never "
            "anonymous mass-production aesthetics."
        ),
        "typography_style": (
            "Confident sans-serif (Lato-like): strong headlines, readable body copy, generous whitespace; "
            "primary green (#2d722d) on white; black (#000000) on tan (#f1ead9) secondary surfaces—"
            "clear hierarchy, approachable precision."
        ),
    }


def ensure_session_state() -> None:
    if "theme" not in st.session_state:
        st.session_state.theme = default_theme()
    if "model_name" not in st.session_state:
        st.session_state.model_name = DEFAULT_MODEL
    elif st.session_state.model_name.strip() in _DEPRECATED_IMAGE_MODELS:
        st.session_state.model_name = DEFAULT_MODEL
    if "image_count" not in st.session_state:
        st.session_state.image_count = 1
    if "gen_aspect_ratio" not in st.session_state:
        st.session_state.gen_aspect_ratio = "16:9"
    if "gen_image_size" not in st.session_state:
        st.session_state.gen_image_size = "2K"
    if "gen_allow_image_text" not in st.session_state:
        st.session_state.gen_allow_image_text = False
    if "gen_job_queue" not in st.session_state:
        st.session_state.gen_job_queue = []


def clear_sidebar_theme_widget_keys() -> None:
    """Reset sidebar theme widget state so it picks up `session_state.theme` after edits on the Theme page."""
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and k.startswith("sb_"):
            del st.session_state[k]


def _inject_sidebar_compact_theme_styles() -> None:
    """Responsive, denser typography & spacing for sidebar theme UI (vh/clamp scale with viewport)."""
    st.markdown(
        """
<style>
    [data-testid="stSidebar"] .block-container {
        padding-top: 0.45rem;
        padding-bottom: 0.65rem;
        padding-left: 0.55rem;
        padding-right: 0.55rem;
        font-size: clamp(0.68rem, 0.52rem + 0.85vh, 0.82rem);
        line-height: 1.38;
    }
    [data-testid="stSidebar"] label {
        font-size: clamp(0.65rem, 0.5rem + 0.75vh, 0.76rem) !important;
    }
    [data-testid="stSidebar"] .stMarkdown h3 {
        font-size: clamp(0.82rem, 0.62rem + 1.1vh, 1rem);
        margin-bottom: 0.15rem;
        line-height: 1.2;
    }
    [data-testid="stSidebar"] .stMarkdown h5 {
        font-size: clamp(0.74rem, 0.58rem + 0.95vh, 0.88rem);
        margin-top: 0;
        margin-bottom: 0.15rem;
    }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
        font-size: clamp(0.62rem, 0.48rem + 0.65vh, 0.72rem);
        margin-bottom: 0.35rem;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] details summary {
        font-size: clamp(0.68rem, 0.52rem + 0.75vh, 0.78rem);
        padding-top: 0.35rem;
        padding-bottom: 0.35rem;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] details summary span {
        font-size: inherit !important;
    }
    [data-testid="stSidebar"] .stTextArea textarea {
        font-size: clamp(0.65rem, 0.5rem + 0.65vh, 0.76rem) !important;
        line-height: 1.35 !important;
        padding: 0.35rem 0.45rem !important;
    }
    [data-testid="stSidebar"] div[data-baseweb="input"] input {
        font-size: clamp(0.66rem, 0.52rem + 0.65vh, 0.76rem) !important;
        min-height: 2rem !important;
    }
    [data-testid="stSidebar"] button[kind] {
        font-size: clamp(0.66rem, 0.52rem + 0.65vh, 0.76rem);
        min-height: 2.05rem;
        padding-top: 0.2rem;
        padding-bottom: 0.2rem;
    }
    @media (max-height: 720px) {
        [data-testid="stSidebar"] .block-container {
            font-size: clamp(0.62rem, 0.5rem + 0.55vh, 0.74rem);
        }
        [data-testid="stSidebar"] label {
            font-size: clamp(0.6rem, 0.48rem + 0.5vh, 0.72rem) !important;
        }
    }
</style>
""",
        unsafe_allow_html=True,
    )


def _switch_streamlit_page(*, pages_filename: Optional[str] = None, main: bool = False) -> None:
    """
    Navigate using ``script_path`` values from Streamlit’s own page registry when possible.
    Relative paths like ``pages/1_Theme.py`` often fail ``switch_page`` internal matching
    (path normalization / cwd); registry strings match exactly.
    """
    from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx

    ctx = get_script_run_ctx()
    if ctx is None:
        if main:
            st.switch_page(str(NAV_PAGE_MAIN))
        elif pages_filename:
            st.switch_page(str(_STUDIO_ROOT / "pages" / pages_filename))
        return

    raw_infos = list(ctx.pages_manager.get_pages().values())

    def script_paths() -> List[str]:
        out: List[str] = []
        for info in raw_infos:
            sp = info.get("script_path")
            if isinstance(sp, str) and sp.strip():
                out.append(sp)
        return out

    main_script = ctx.main_script_path
    try:
        main_resolved = Path(main_script).expanduser().resolve()
    except OSError:
        main_resolved = Path(main_script)

    if main:
        for sp in script_paths():
            try:
                if Path(sp).expanduser().resolve() == main_resolved:
                    st.switch_page(sp)
                    return
            except OSError:
                continue
        st.switch_page(main_script)
        return

    if pages_filename:
        want = (main_resolved.parent / "pages" / pages_filename).resolve()
        for sp in script_paths():
            try:
                if Path(sp).expanduser().resolve() == want:
                    st.switch_page(sp)
                    return
            except OSError:
                continue
        for sp in script_paths():
            if Path(sp).name == pages_filename:
                st.switch_page(sp)
                return
        st.switch_page(str(want))


def _render_sidebar_navigation() -> None:
    """Multipage navigation via ``st.switch_page`` (registry-aligned paths)."""
    st.caption("Navigate")
    if st.button("Image generation", key="sidebar_nav_generate", use_container_width=True):
        _switch_streamlit_page(main=True)
    if st.button("Theme", key="sidebar_nav_theme", use_container_width=True):
        _switch_streamlit_page(pages_filename="1_Theme.py")
    if st.button("Model", key="sidebar_nav_model", use_container_width=True):
        _switch_streamlit_page(pages_filename="2_Model.py")


def render_sidebar(*, show_theme_editor: bool = True) -> None:
    """Left sidebar: optional theme editor, then page navigation."""
    with st.sidebar:
        _inject_sidebar_compact_theme_styles()
        st.markdown(f"### {APP_TITLE}")

        if show_theme_editor:
            st.markdown("##### Theme")
            st.caption("Saved in session — expand sections as needed.")

            t = st.session_state.theme

            with st.expander("Brand & overview", expanded=False):
                sb_brand_name = st.text_input("Brand name", value=t["brand_name"], key="sb_brand_name")
                sb_tagline = st.text_input("Tagline", value=t["tagline"], key="sb_tagline")
                sb_overview = st.text_area(
                    "Overview",
                    value=t["brand_overview"],
                    height=72,
                    key="sb_overview",
                )

            with st.expander("Colors", expanded=False):
                r1c1, r1c2 = st.columns(2)
                with r1c1:
                    sb_primary = st.color_picker("Primary", value=t["primary_color"], key="sb_primary")
                with r1c2:
                    sb_primary_inv = st.color_picker(
                        "Primary inverse",
                        value=t["primary_inverse"],
                        key="sb_primary_inv",
                    )
                r2c1, r2c2 = st.columns(2)
                with r2c1:
                    sb_secondary = st.color_picker(
                        "Secondary",
                        value=t["secondary_color"],
                        key="sb_secondary",
                    )
                with r2c2:
                    sb_secondary_inv = st.color_picker(
                        "Secondary inverse",
                        value=t["secondary_inverse"],
                        key="sb_secondary_inv",
                    )

            with st.expander("Business profile", expanded=False):
                sb_category = st.text_input("Category", value=t["product_category"], key="sb_category")
                sb_audience = st.text_area(
                    "Target audience",
                    value=t["target_audience"],
                    height=56,
                    key="sb_audience",
                )

            with st.expander("Voice & visuals", expanded=False):
                sb_tones = st.text_area(
                    "Tone (one per line)",
                    value="\n".join(t["tones"]),
                    height=64,
                    key="sb_tones",
                )
                sb_writing = st.text_area(
                    "Writing style",
                    value=t["writing_style"],
                    height=56,
                    key="sb_writing",
                )
                sb_bg = st.text_input("Background style", value=t["background_style"], key="sb_bg")
                sb_imagery = st.text_input("Imagery style", value=t["imagery_style"], key="sb_imagery")
                sb_typo = st.text_input("Typography", value=t["typography_style"], key="sb_typo")

            if st.button("Reset theme to Main Street sample", key="sb_reset_sample"):
                st.session_state.theme = default_theme()
                clear_sidebar_theme_widget_keys()
                st.rerun()

            st.session_state.theme = {
                "primary_color": sb_primary,
                "primary_inverse": sb_primary_inv,
                "secondary_color": sb_secondary,
                "secondary_inverse": sb_secondary_inv,
                "brand_name": sb_brand_name.strip(),
                "tagline": sb_tagline.strip(),
                "brand_overview": sb_overview.strip(),
                "product_category": sb_category.strip(),
                "target_audience": sb_audience.strip(),
                "tones": [line.strip() for line in sb_tones.splitlines() if line.strip()],
                "writing_style": sb_writing.strip(),
                "background_style": sb_bg.strip(),
                "imagery_style": sb_imagery.strip(),
                "typography_style": sb_typo.strip(),
            }

        st.divider()
        _render_sidebar_navigation()


def slugify(value: str, *, max_len: int = 40) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    clean = clean.strip("-")
    if len(clean) > max_len:
        clean = clean[:max_len].rstrip("-")
    return clean or "image"


def short_name_from_prompt(prompt: str, *, max_len: int = 28) -> str:
    """Compact filesystem-safe label from the main brief (first line, before optional --- extras)."""
    main = prompt.strip().split("\n\n---\n", 1)[0].strip()
    line = main.split("\n", 1)[0].strip()
    return slugify(line, max_len=max_len)


def build_prompt(
    theme: Dict[str, Any],
    user_prompt: str,
    extra_instructions: str = "",
    *,
    allow_image_text: bool = False,
    aspect_ratio: Optional[str] = None,
    image_size: Optional[str] = None,
) -> str:
    tones = ", ".join(theme["tones"])
    extra_block = ""
    if extra_instructions.strip():
        extra_block = f"\n\nAdditional creator instructions:\n{extra_instructions.strip()}"

    tech_lines: List[str] = []
    if aspect_ratio:
        tech_lines.append(f"Frame and compose for a {aspect_ratio} aspect ratio.")
    if image_size:
        tech_lines.append(f"Target detail and sharpness appropriate for a {image_size}-class export.")
    technical_section = ""
    if tech_lines:
        technical_section = (
            "\nTechnical framing (apply strictly):\n- "
            + "\n- ".join(tech_lines)
            + "\n"
        )

    if allow_image_text:
        text_rule = (
            "Short on-brand text is allowed only when it clearly improves the scene "
            "(e.g. a concise headline or label). Keep it minimal, legible, and consistent "
            "with the typography guidance below—no watermarks or unrelated copy."
        )
    else:
        text_rule = (
            "Do not include any written text, lettering, captions, logos, watermarks, "
            "UI chrome, or typography in the image — illustration / photography only."
        )

    return f"""
PRIMARY TASK — highest priority
Follow this creative brief first. Sections below adjust mood and palette only; they must not replace or contradict the brief.

Creative directive (execute fully):
{user_prompt.strip()}
{extra_block}{technical_section}
Brand alignment context (secondary — refine look & feel when compatible with the directive above):
- Brand name: {theme["brand_name"]}
- Tagline: {theme["tagline"]}
- Brand overview: {theme["brand_overview"]}
- Product category: {theme["product_category"]}
- Target audience: {theme["target_audience"]}
- Tone keywords: {tones}
- Writing style guidance: {theme["writing_style"]}
- Primary color: {theme["primary_color"]} (inverse: {theme["primary_inverse"]})
- Secondary color: {theme["secondary_color"]} (inverse: {theme["secondary_inverse"]})
- Background style: {theme["background_style"]}
- Imagery style: {theme["imagery_style"]}
- Typography style: {theme["typography_style"]}

Composition, fidelity & safety:
- Produce one high-quality, original brand image aligned with the creative directive.
- Keep composition clean and professional.
- Keep colors aligned to the brand palette; avoid unrelated accent colors.
- Match tone and audience fit from the brand identity where it supports the brief.
- Do not depict logos or trademarks you do not own.
- Text in image: {text_rule}
""".strip()


def decode_inline_data(part: Any) -> Optional[bytes]:
    inline_data = getattr(part, "inline_data", None)
    if inline_data is None:
        return None

    data = getattr(inline_data, "data", None)
    if data is None:
        return None
    if isinstance(data, bytes):
        return data
    if isinstance(data, str):
        try:
            return base64.b64decode(data)
        except Exception:
            return None
    return None


def extract_images_from_response(response: Any) -> List[bytes]:
    images: List[bytes] = []

    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            maybe_image = decode_inline_data(part)
            if maybe_image:
                images.append(maybe_image)

    if images:
        return images

    dict_response = None
    try:
        dict_response = response.model_dump()
    except Exception:
        try:
            dict_response = response.to_dict()
        except Exception:
            dict_response = None

    if not dict_response:
        return images

    for candidate in dict_response.get("candidates", []):
        content = candidate.get("content", {})
        for part in content.get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if not inline:
                continue
            data = inline.get("data")
            if not data:
                continue
            try:
                images.append(base64.b64decode(data))
            except Exception:
                continue
    return images


def generate_images(
    api_key: str,
    model: str,
    compiled_prompt: str,
    *,
    aspect_ratio: Optional[str] = None,
    image_size: Optional[str] = None,
) -> List[bytes]:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    img_kwargs: Dict[str, Any] = {}
    if aspect_ratio:
        img_kwargs["aspect_ratio"] = aspect_ratio
    if image_size:
        img_kwargs["image_size"] = image_size

    img_cfg = types.ImageConfig(**img_kwargs) if img_kwargs else None
    cfg_full = (
        types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=img_cfg,
        )
        if img_cfg
        else None
    )
    cfg_basic = types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"])

    response = None
    last_err: Optional[Exception] = None
    config_attempts = ([cfg_full] if cfg_full else []) + [cfg_basic]
    for cfg in config_attempts:
        try:
            response = client.models.generate_content(
                model=model,
                contents=compiled_prompt,
                config=cfg,
            )
            break
        except Exception as exc:
            last_err = exc
            if cfg is cfg_basic:
                raise

    if response is None:
        raise last_err or RuntimeError("No response from Gemini.")

    images = extract_images_from_response(response)
    if not images:
        raise RuntimeError("No image returned by Gemini for this request.")
    return images


def generate_images_batch(
    api_key: str,
    model: str,
    compiled_prompt: str,
    count: int,
    *,
    aspect_ratio: Optional[str] = None,
    image_size: Optional[str] = None,
) -> List[bytes]:
    """Request ``count`` images (one API call each), in order."""
    if count < 1:
        return []
    chunks: List[bytes] = []
    for _ in range(count):
        chunks.extend(
            generate_images(
                api_key,
                model,
                compiled_prompt,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
            )
        )
    return chunks


def save_outputs(images: List[bytes], prompt: str) -> List[str]:
    """Write PNG files only (no JSON sidecars). Filename includes a short slug from the prompt."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    small_name = short_name_from_prompt(prompt)
    saved: List[str] = []

    for idx, image_bytes in enumerate(images, start=1):
        stem = f"{timestamp}-{small_name}-{idx}"
        image_path = OUTPUT_DIR / f"{stem}.png"

        with open(image_path, "wb") as f:
            f.write(image_bytes)

        saved.append(str(image_path))
    return saved


# Raster formats Streamlit's ``st.image`` handles well (exclude SVG).
_STOCK_HISTORY_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif"})


def read_recent_history(*, limit: Optional[int] = None) -> List[Path]:
    """All raster image files under ``OUTPUT_DIR`` (recursive), newest modification time first."""
    if not OUTPUT_DIR.is_dir():
        return []
    paths: List[Path] = []
    for p in OUTPUT_DIR.rglob("*"):
        if p.is_file() and p.suffix.lower() in _STOCK_HISTORY_SUFFIXES:
            paths.append(p)
    paths.sort(key=lambda q: q.stat().st_mtime, reverse=True)
    if limit is not None:
        paths = paths[:limit]
    return paths
