import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import fitz
import streamlit as st
from docx import Document
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

APP_TITLE = "FrankNPost"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_INPUT_COST_PER_M = 0.15
DEFAULT_OUTPUT_COST_PER_M = 0.60

_APP_ROOT = Path(__file__).resolve().parent
_DEFAULT_OUTPUT_DIR = (_APP_ROOT.parent / "Generated Posts").resolve()
OUTPUT_DIR = Path(
    os.environ.get("FRANKNPOST_OUTPUT_DIR", str(_DEFAULT_OUTPUT_DIR))
).expanduser().resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_UPLOAD_TYPES = ("md", "txt", "docx", "pdf")
POST_MODES = ("blog", "linkedin", "facebook", "instagram")

HUMAN_WRITING_STYLE_RULES = """
Rules for natural, human writing:
- Write like a real person explaining something to another real person, not like a system trying to sound perfect.
- Avoid overly perfect grammar. Use sentence fragments when natural, mix short and long sentences, and avoid stiff formality unless the context requires it.
- Use conversational transitions such as also, but, still, at the same time, the thing is, honestly, and even so. Avoid robotic transitions like furthermore, moreover, additionally, therefore, overall, and in conclusion.
- Create human rhythm: vary sentence length, let some paragraphs feel uneven, and avoid predictable balanced structures.
- Include specific observations, small details, real examples, and grounded comparisons instead of generic claims.
- Avoid repetitive sentence structures and stock phrases like "This shows..." or "It is important to note..."
- Let some imperfection stay. Use contractions such as don't, can't, it's, and you'll when they sound natural.
- Remove generic filler phrases like "in today's world," "since the dawn of time," and "it is worth mentioning."
- Use emotional weight carefully with subtle, concrete cues instead of broad emotional labels.
- Break predictability by occasionally starting with a question, fragment, contrast, or observation.
- Keep vocabulary realistic. Use simple words: use instead of utilize, start instead of commence, many instead of numerous, help instead of facilitate.
- Use personal framing when appropriate: "What stood out to me...", "I didn't expect...", "The strange part was...", or "At first, it seemed..."
- Do not over-explain. Leave obvious things implied when a shorter line sounds more human.
- Edit for voice, not perfection. Read it out loud and loosen anything that sounds like a corporate presentation.
- Before finishing: vary sentence lengths, remove robotic transitions, add specific details, use contractions, simplify vocabulary, cut filler, make rhythm less predictable, and prioritize clarity over polish.
- The goal is natural, specific, grounded, clear, genuinely human writing.
""".strip()


def _with_human_writing_rules(writing_style: str) -> str:
    if "Rules for natural, human writing:" in writing_style:
        return writing_style
    return f"{writing_style.strip()}\n\n{HUMAN_WRITING_STYLE_RULES}".strip()


def default_theme() -> Dict[str, Any]:
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
        "writing_style": _with_human_writing_rules(
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


def default_persona() -> Dict[str, Any]:
    return {
        "persona_name": "The Mother Hobbyist",
        "headline": "A resourceful maker-mom already selling through DMs, local groups, and markets.",
        "at_a_glance": (
            "Female, 35-50 with the average closer to 42; mid-level technical skill; earns "
            "$400-$1,200 per month from the business, with major Q4 spikes."
        ),
        "core_need": (
            "She needs simple back-office infrastructure that matches a life built around school "
            "pickups, family obligations, and short 5-10 minute selling windows."
        ),
        "selling_context": (
            "She has sold handmade goods for 2-4 years through Instagram DMs, Facebook groups, "
            "PayPal/Venmo links, local craft fairs, and manual Notes or spreadsheets. Etsy or "
            "Shopify felt too complex, too costly, or too time-consuming."
        ),
        "personality": "Resourceful, warm, community-driven, careful with risk, and quietly ambitious.",
        "aspirations": (
            "Earn $2,000/month consistently, maintain a real storefront, survive holiday rushes "
            "without missed orders, become a trusted local maker, and eventually grow the income "
            "stream into something independent and meaningful."
        ),
        "fears": (
            "Missing buyer messages, overselling during holidays, hidden fees, wasting money on "
            "tools that do not pay for themselves, looking unprofessional, and losing creative or "
            "family time to admin work."
        ),
        "psychographics": (
            "Family-first, authentic, community-oriented, financially responsible, skeptical of "
            "overcomplicated technology, and deeply attached to craft as personal identity."
        ),
        "watering_holes": (
            "Local mom Facebook groups, buy/sell/trade groups, Instagram maker hashtags, Etsy "
            "seller communities, Pinterest, Nextdoor, school/PTA networks, church bazaars, craft "
            "fairs, holiday markets, maker spaces, and local boutique shops."
        ),
        "day_in_life": (
            "On a November weekday she checks DMs before the kids wake, handles school drop-off, "
            "makes products in short windows, photographs items at the kitchen table, updates "
            "buyers during nap time, misses messages during the 3-6 PM family blackout, then "
            "packages orders after bedtime."
        ),
        "segmentation_outlines": [
            {
                "name": "Core mother hobbyist",
                "outline": (
                    "35-50-year-old maker-mom selling handmade goods as a real household "
                    "contribution. She needs growth that stays compatible with family life."
                ),
            },
            {
                "name": "Social-first seller",
                "outline": (
                    "Runs sales through Instagram DMs, Stories, Facebook groups, and local "
                    "recommendations. She is socially fluent but lacks order tracking, payments, "
                    "inventory, and professional storefront infrastructure."
                ),
            },
            {
                "name": "E-commerce averse Etsy dropout",
                "outline": (
                    "Tried Etsy, Shopify, Square, or similar tools and bounced off because setup, "
                    "fees, SEO, or back-end configuration cost too much time and confidence."
                ),
            },
            {
                "name": "Holiday rush operator",
                "outline": (
                    "Sees 30% or more of annual revenue in October-December. She needs inventory, "
                    "order, and buyer-message support before the season becomes chaotic."
                ),
            },
            {
                "name": "Local trust network seller",
                "outline": (
                    "Sells through school, PTA, church, neighborhood, craft fair, and local "
                    "boutique relationships. Word-of-mouth and community trust drive discovery."
                ),
            },
            {
                "name": "Quietly ambitious future owner",
                "outline": (
                    "Does not call herself an entrepreneur yet, but wants a storefront, repeat "
                    "buyers, better pricing, wholesale possibilities, and income that is fully hers."
                ),
            },
        ],
    }


def ensure_session_state() -> None:
    if "theme" not in st.session_state:
        st.session_state.theme = default_theme()
    else:
        current_style = st.session_state.theme.get("writing_style", "")
        updated_style = _with_human_writing_rules(current_style)
        if updated_style != current_style:
            st.session_state.theme["writing_style"] = updated_style
            if "sb_writing" in st.session_state:
                del st.session_state["sb_writing"]
    if "persona" not in st.session_state:
        st.session_state.persona = default_persona()
    if "model_name" not in st.session_state:
        st.session_state.model_name = DEFAULT_MODEL
    if "input_cost_per_m" not in st.session_state:
        st.session_state.input_cost_per_m = DEFAULT_INPUT_COST_PER_M
    if "output_cost_per_m" not in st.session_state:
        st.session_state.output_cost_per_m = DEFAULT_OUTPUT_COST_PER_M


def clear_sidebar_theme_widget_keys() -> None:
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("sb_"):
            del st.session_state[key]


def clear_sidebar_persona_widget_keys() -> None:
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("sp_"):
            del st.session_state[key]


def _switch_streamlit_page(*, pages_filename: str | None = None, main: bool = False) -> None:
    from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx

    ctx = get_script_run_ctx()
    if ctx is None:
        if main:
            st.switch_page(str(_APP_ROOT / "app.py"))
        elif pages_filename:
            st.switch_page(str(_APP_ROOT / "pages" / pages_filename))
        return

    page_infos = list(ctx.pages_manager.get_pages().values())
    script_paths = [p["script_path"] for p in page_infos if isinstance(p.get("script_path"), str)]
    main_script = Path(ctx.main_script_path).resolve()

    if main:
        for script_path in script_paths:
            if Path(script_path).resolve() == main_script:
                st.switch_page(script_path)
                return
        st.switch_page(str(main_script))
        return

    if not pages_filename:
        return

    target = (_APP_ROOT / "pages" / pages_filename).resolve()
    for script_path in script_paths:
        candidate = Path(script_path)
        if candidate.name == pages_filename or candidate.resolve() == target:
            st.switch_page(script_path)
            return
    st.switch_page(str(target))


def render_sidebar(*, show_theme_editor: bool = True) -> None:
    with st.sidebar:
        st.markdown(f"### {APP_TITLE}")
        if show_theme_editor:
            st.markdown("##### Theme")
            st.caption("Saved in session — expand sections as needed.")
            t = st.session_state.theme
            with st.expander("Brand & overview", expanded=False):
                sb_brand_name = st.text_input("Brand name", value=t["brand_name"], key="sb_brand_name")
                sb_tagline = st.text_input("Tagline", value=t["tagline"], key="sb_tagline")
                sb_overview = st.text_area("Overview", value=t["brand_overview"], height=72, key="sb_overview")
            with st.expander("Colors", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    sb_primary = st.color_picker("Primary", value=t["primary_color"], key="sb_primary")
                with c2:
                    sb_primary_inv = st.color_picker(
                        "Primary inverse", value=t["primary_inverse"], key="sb_primary_inv"
                    )
                c3, c4 = st.columns(2)
                with c3:
                    sb_secondary = st.color_picker("Secondary", value=t["secondary_color"], key="sb_secondary")
                with c4:
                    sb_secondary_inv = st.color_picker(
                        "Secondary inverse", value=t["secondary_inverse"], key="sb_secondary_inv"
                    )
            with st.expander("Business profile", expanded=False):
                sb_category = st.text_input("Category", value=t["product_category"], key="sb_category")
                sb_audience = st.text_area("Target audience", value=t["target_audience"], height=56, key="sb_audience")
            with st.expander("Voice & visuals", expanded=False):
                sb_tones = st.text_area("Tone (one per line)", value="\n".join(t["tones"]), height=64, key="sb_tones")
                sb_writing = st.text_area("Writing style", value=t["writing_style"], height=56, key="sb_writing")
                sb_bg = st.text_input("Background style", value=t["background_style"], key="sb_bg")
                sb_imagery = st.text_input("Imagery style", value=t["imagery_style"], key="sb_imagery")
                sb_typo = st.text_input("Typography", value=t["typography_style"], key="sb_typo")
            if st.button("Reset sample theme", key="sb_reset"):
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

            st.markdown("##### Persona")
            p = st.session_state.persona
            with st.expander("Audience profile", expanded=False):
                sp_name = st.text_input("Persona name", value=p["persona_name"], key="sp_name")
                sp_headline = st.text_area("Headline", value=p["headline"], height=56, key="sp_headline")
                sp_core_need = st.text_area("Core need", value=p["core_need"], height=72, key="sp_core_need")
            with st.expander("Persona details", expanded=False):
                sp_glance = st.text_area("At a glance", value=p["at_a_glance"], height=64, key="sp_glance")
                sp_selling = st.text_area("Selling context", value=p["selling_context"], height=72, key="sp_selling")
                sp_personality = st.text_area("Personality", value=p["personality"], height=56, key="sp_personality")
            with st.expander("Motivations & channels", expanded=False):
                sp_aspirations = st.text_area("Aspirations", value=p["aspirations"], height=72, key="sp_aspirations")
                sp_fears = st.text_area("Fears", value=p["fears"], height=72, key="sp_fears")
                sp_watering = st.text_area("Watering holes", value=p["watering_holes"], height=72, key="sp_watering")
            if st.button("Reset sample persona", key="sp_reset"):
                st.session_state.persona = default_persona()
                clear_sidebar_persona_widget_keys()
                st.rerun()
            st.session_state.persona = {
                **p,
                "persona_name": sp_name.strip(),
                "headline": sp_headline.strip(),
                "core_need": sp_core_need.strip(),
                "at_a_glance": sp_glance.strip(),
                "selling_context": sp_selling.strip(),
                "personality": sp_personality.strip(),
                "aspirations": sp_aspirations.strip(),
                "fears": sp_fears.strip(),
                "watering_holes": sp_watering.strip(),
            }

        st.divider()
        st.caption("Navigate")
        if st.button("Generate", use_container_width=True):
            _switch_streamlit_page(main=True)
        if st.button("Theme", use_container_width=True):
            _switch_streamlit_page(pages_filename="1_Theme.py")
        if st.button("Persona", use_container_width=True):
            _switch_streamlit_page(pages_filename="3_Persona.py")
        if st.button("Model", use_container_width=True):
            _switch_streamlit_page(pages_filename="2_Model.py")


def brand_voice_block(theme: Dict[str, Any]) -> str:
    tones = ", ".join(theme.get("tones", []))
    return (
        f"Brand Name: {theme.get('brand_name', '').strip()}\n"
        f"Tagline: {theme.get('tagline', '').strip()}\n"
        f"Brand Overview: {theme.get('brand_overview', '').strip()}\n"
        f"Category: {theme.get('product_category', '').strip()}\n"
        f"Target Audience: {theme.get('target_audience', '').strip()}\n"
        f"Tones: {tones}\n"
        f"Writing Style: {theme.get('writing_style', '').strip()}\n"
        f"Visual Background Style: {theme.get('background_style', '').strip()}\n"
        f"Imagery Style: {theme.get('imagery_style', '').strip()}\n"
        f"Typography Style: {theme.get('typography_style', '').strip()}\n"
        f"Brand Colors: Primary {theme.get('primary_color', '')}, Secondary {theme.get('secondary_color', '')}"
    )


def persona_brief_block(persona: Dict[str, Any]) -> str:
    if not persona:
        return ""

    segment_lines = []
    for segment in persona.get("segmentation_outlines", []):
        if isinstance(segment, dict):
            name = str(segment.get("name", "")).strip()
            outline = str(segment.get("outline", "")).strip()
            if name and outline:
                segment_lines.append(f"- {name}: {outline}")
        elif str(segment).strip():
            segment_lines.append(f"- {str(segment).strip()}")

    segments = "\n".join(segment_lines)
    return (
        f"Persona Name: {persona.get('persona_name', '').strip()}\n"
        f"Headline: {persona.get('headline', '').strip()}\n"
        f"At a Glance: {persona.get('at_a_glance', '').strip()}\n"
        f"Core Need: {persona.get('core_need', '').strip()}\n"
        f"Selling Context: {persona.get('selling_context', '').strip()}\n"
        f"Personality: {persona.get('personality', '').strip()}\n"
        f"Aspirations: {persona.get('aspirations', '').strip()}\n"
        f"Fears: {persona.get('fears', '').strip()}\n"
        f"Psychographics: {persona.get('psychographics', '').strip()}\n"
        f"Watering Holes: {persona.get('watering_holes', '').strip()}\n"
        f"Day in Life: {persona.get('day_in_life', '').strip()}\n"
        f"Segmentation Outlines:\n{segments}"
    ).strip()


BLOG_SYSTEM_PROMPT = """
You are an expert editorial strategist and long-form content writer specializing in:
- GEO (Generative Engine Optimization)
- SEO (Search Engine Optimization)
- Main Street storytelling
- Local artisan and community-centered brands

Your task is to generate a high-quality blog post that is:
1. Optimized FIRST for GEO visibility and citation by AI systems and answer engines
2. Optimized SECOND for traditional SEO performance
3. Deeply aligned with the provided brand voice
4. Authentic and emotionally resonant for local artisans, makers, shoppers, and Main Street communities

Generate in this exact order:
1. SEO Title
2. Meta Description
3. URL Slug
4. Blog Post
5. FAQ Section
6. Internal Link Suggestions
7. External Reference Suggestions
8. Social Excerpt
9. Pull Quotes
""".strip()

SOCIAL_SYSTEM_PROMPT = """
You are an elite social media strategist, cultural storyteller, and platform-native content creator specializing in:
- Facebook content that builds conversation and community
- Instagram content that drives engagement, shares, saves, and follower growth
- Viral social storytelling
- Authentic human-sounding writing
- Main Street businesses, artisans, makers, and local communities
- Brand voice adaptation
- Emotionally intelligent audience engagement

The primary goal is engagement, shareability, community building, and emotional connection.
Do not optimize for SEO or GEO.

Return in this exact order:
1. Primary Caption/Post
2. Alternate Hook Options
3. Suggested CTA
4. Suggested Hashtags
5. Optional Story/Carousel Ideas
6. Suggested Visual Direction
7. Engagement Prompt
""".strip()

LINKEDIN_SYSTEM_PROMPT = """
You are an elite LinkedIn strategist, founder-brand writer, and narrative positioning expert.
Create LinkedIn content that builds credibility, trust, narrative authority, and long-term relationship equity.

The writing must be:
- Grounded and authentic
- Strategically clear
- Mission-driven and practical
- Human, not hype-driven

Return in this exact order:
1. Primary LinkedIn Post
2. Alternate Hook Options
3. Suggested CTA
4. Suggested Visual/Media Direction
5. Optional Founder Commentary Angle
6. Suggested Follow-Up Post Ideas
7. Suggested Hashtags
""".strip()


def _persona_prompt_section(persona_brief: str) -> str:
    if not persona_brief:
        return ""
    return f"""

Audience Persona:
{persona_brief}
""".rstrip()


def _blog_user_prompt(values: Dict[str, str], brand_voice: str, persona_brief: str = "") -> str:
    return f"""
Brand Voice:
{brand_voice}
{_persona_prompt_section(persona_brief)}

Topic: {values.get("topic", "")}
Primary Keyword: {values.get("primary_keyword", "")}
Secondary Keywords: {values.get("secondary_keywords", "")}
Target Audience Details: {values.get("audience", "")}
Brand/Product/Organization: {values.get("brand_name", "")}
Location or Community Context: {values.get("location", "")}
Desired Call To Action: {values.get("cta", "")}
Optional Supporting Information:
{values.get("supporting_context", "")}

Requirements:
- Include direct-answer sections and practical takeaways.
- Keep voice aligned to the brand block.
- Make the article publication-ready.
""".strip()


def _social_user_prompt(values: Dict[str, str], brand_voice: str, platform: str, persona_brief: str = "") -> str:
    return f"""
Platform: {platform}
Brand Voice:
{brand_voice}
{_persona_prompt_section(persona_brief)}

Content Goal: {values.get("content_goal", "")}
Topic: {values.get("topic", "")}
Brand/Business Name: {values.get("brand_name", "")}
Location/Community: {values.get("location", "")}
Offer/Product/Event: {values.get("offer", "")}
Target Audience: {values.get("audience", "")}
Supporting Context:
{values.get("supporting_context", "")}
Desired CTA: {values.get("cta", "")}

Requirements:
- Sound genuinely human and platform-native.
- Prioritize emotional resonance and conversation.
""".strip()


def _linkedin_user_prompt(values: Dict[str, str], brand_voice: str, persona_brief: str = "") -> str:
    return f"""
Brand Voice:
{brand_voice}
{_persona_prompt_section(persona_brief)}

Topic: {values.get("topic", "")}
Company Name: {values.get("brand_name", "")}
Industry: {values.get("industry", "")}
Core Mission: {values.get("mission", "")}
Current Milestone: {values.get("milestone", "")}
Target Audience: {values.get("audience", "")}
Supporting Context:
{values.get("supporting_context", "")}
Desired CTA: {values.get("cta", "")}

Requirements:
- Show market understanding and operator credibility.
- Sound measured, transparent, and human.
""".strip()


def prompt_for_mode(mode: str, values: Dict[str, str], brand_voice: str, persona_brief: str = "") -> Dict[str, str]:
    if mode == "blog":
        return {"system": BLOG_SYSTEM_PROMPT, "user": _blog_user_prompt(values, brand_voice, persona_brief)}
    if mode == "linkedin":
        return {"system": LINKEDIN_SYSTEM_PROMPT, "user": _linkedin_user_prompt(values, brand_voice, persona_brief)}
    if mode == "facebook":
        return {"system": SOCIAL_SYSTEM_PROMPT, "user": _social_user_prompt(values, brand_voice, "Facebook", persona_brief)}
    if mode == "instagram":
        return {"system": SOCIAL_SYSTEM_PROMPT, "user": _social_user_prompt(values, brand_voice, "Instagram", persona_brief)}
    raise ValueError(f"Unsupported mode: {mode}")


def estimate_cost_usd(prompt_tokens: int, completion_tokens: int, input_cost_per_m: float, output_cost_per_m: float) -> float:
    input_cost = (prompt_tokens / 1_000_000) * input_cost_per_m
    output_cost = (completion_tokens / 1_000_000) * output_cost_per_m
    return input_cost + output_cost


def _response_text(response: Any) -> str:
    content = ""
    if response.choices and response.choices[0].message:
        content = response.choices[0].message.content or ""
    return content.strip()


def generate_post_for_mode(
    *,
    api_key: str,
    model: str,
    mode: str,
    values: Dict[str, str],
    theme: Dict[str, Any],
    persona: Dict[str, Any] | None = None,
    input_cost_per_m: float,
    output_cost_per_m: float,
) -> Dict[str, Any]:
    client = OpenAI(api_key=api_key)
    brand_voice = brand_voice_block(theme)
    persona_brief = persona_brief_block(persona or {})
    prompts = prompt_for_mode(mode, values, brand_voice, persona_brief)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompts["system"]},
            {"role": "user", "content": prompts["user"]},
        ],
    )

    prompt_tokens = int(getattr(response.usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(response.usage, "completion_tokens", 0) or 0)
    total_tokens = int(getattr(response.usage, "total_tokens", 0) or 0)
    est_cost = estimate_cost_usd(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        input_cost_per_m=input_cost_per_m,
        output_cost_per_m=output_cost_per_m,
    )

    return {
        "mode": mode,
        "model": model,
        "system_prompt": prompts["system"],
        "user_prompt": prompts["user"],
        "output_text": _response_text(response),
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
        "estimated_cost_usd": est_cost,
    }


def slugify(value: str, *, max_len: int = 48) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    if len(clean) > max_len:
        clean = clean[:max_len].rstrip("-")
    return clean or "post"


def save_generation(
    result: Dict[str, Any],
    values: Dict[str, str],
    theme: Dict[str, Any],
    persona: Dict[str, Any] | None = None,
) -> Dict[str, str]:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    topic_slug = slugify(values.get("topic", "") or "untitled")
    mode = result["mode"]
    stem = f"{timestamp}-{mode}-{topic_slug}"
    md_path = OUTPUT_DIR / f"{stem}.md"
    meta_path = OUTPUT_DIR / f"{stem}.json"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {mode.title()} Output\n\n")
        f.write(result["output_text"])
        f.write("\n")

    metadata = {
        "created_at": datetime.now().isoformat(),
        "mode": mode,
        "model": result["model"],
        "values": values,
        "theme": theme,
        "persona": persona or {},
        "system_prompt": result["system_prompt"],
        "user_prompt": result["user_prompt"],
        "usage": result["usage"],
        "estimated_cost_usd": result["estimated_cost_usd"],
        "markdown_file": str(md_path),
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return {"markdown": str(md_path), "metadata": str(meta_path)}


def read_recent_history(limit: int = 30) -> List[Path]:
    if not OUTPUT_DIR.is_dir():
        return []
    items = [p for p in OUTPUT_DIR.glob("*.md") if p.is_file()]
    items.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return items[:limit]


def parse_uploaded_file(uploaded_file: Any) -> str:
    suffix = Path(uploaded_file.name).suffix.lower()
    raw_bytes = uploaded_file.getvalue()

    if suffix in {".md", ".txt"}:
        return raw_bytes.decode("utf-8", errors="replace")

    if suffix == ".docx":
        temp_path = OUTPUT_DIR / f".tmp-{datetime.now().timestamp()}-{uploaded_file.name}"
        temp_path.write_bytes(raw_bytes)
        try:
            document = Document(str(temp_path))
            lines = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
            return "\n".join(lines)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    if suffix == ".pdf":
        text_chunks: List[str] = []
        with fitz.open(stream=raw_bytes, filetype="pdf") as pdf:
            for page in pdf:
                page_text = page.get_text("text").strip()
                if page_text:
                    text_chunks.append(page_text)
        return "\n\n".join(text_chunks)

    raise ValueError(f"Unsupported file type: {suffix}")
