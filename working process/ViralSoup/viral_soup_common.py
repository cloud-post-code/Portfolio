"""
ViralSoup — meme prompts, OpenAI + Gemini helpers, save/history.
"""
from __future__ import annotations

import base64
import json
import os
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

APP_TITLE = "ViralSoup"
DEFAULT_OPENAI_MODEL = "gpt-5-nano"
DEFAULT_GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"
DEFAULT_INPUT_COST_PER_M = 0.15
DEFAULT_OUTPUT_COST_PER_M = 0.60

_APP_ROOT = Path(__file__).resolve().parent
_DEFAULT_OUTPUT_DIR = (_APP_ROOT.parent / "Generated Memes").resolve()
_OUTPUT_ENV = (
    os.environ.get("VIRALSOUP_OUTPUT_DIR")
    or os.environ.get("MEMEFORGE_OUTPUT_DIR")
    or str(_DEFAULT_OUTPUT_DIR)
)
OUTPUT_DIR = Path(_OUTPUT_ENV).expanduser().resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

GEMINI_ASPECT_RATIOS = ("1:1", "2:3", "3:2", "3:4", "4:3", "9:16", "16:9", "21:9")
GEMINI_IMAGE_SIZES = ("1K", "2K", "4K")

# Virality controls use 0–10 (0 = off / none for that axis, 10 = max).
VIRALITY_SLIDER_MIN = 0
VIRALITY_SLIDER_MAX = 10
VIRALITY_SLIDER_DEFAULT = 0
VIRALITY_SLIDER_NEUTRAL = 5  # implicit center for smart auto-tuning (deltas stack on this)

# All 22 virality dimensions — keys used in session_state / slider dicts (0–10).
# To add a new axis: append here; the rest of the system picks it up automatically.
VIRALITY_SLIDER_KEYS: List[tuple[str, str, str]] = [
    ("slider_humor",               "Humor",                "How joke-forward vs dry the meme should feel."),
    ("slider_emotional_intensity", "Emotional intensity",  "Calm/light → emotionally explosive."),
    ("slider_relatability",        "Relatability",         "Instant ‘that’s me’ energy vs niche/obscure."),
    ("slider_simplicity",          "Simplicity",           "Clean one-liner energy vs layered / multi-step joke."),
    ("slider_memetic_compression", "Memetic compression",  "How much meaning is packed into the fewest words / pixels."),
    ("slider_silent_readability",  "Silent readability",   "Works perfectly muted / text-only — no audio or context needed."),
    ("slider_repetition_exposure", "Repetition exposure",  "Leans into familiar, over-exposed formats for instant recognition."),
    ("slider_visual_polish",       "Visual polish",        "Lo-fi raw energy (0) → slick, high-production look (10)."),
    ("slider_identity_signaling",  "Identity signaling",   "How strongly this flags group membership or in-crowd status."),
    ("slider_remixability",        "Remixability",         "How easy this is to copy, riff on, or remix into new variants."),
    ("slider_nostalgia_layer",     "Nostalgia layer",      "Callbacks to past eras, formats, or cultural moments."),
    ("slider_participation",       "Participation",        "Invites comments, duets, stitches, or audience co-creation."),
    ("slider_cultural_relevance",  "Cultural relevance",   "Taps a current trend, moment, or shared cultural reference."),
    ("slider_story_beats",         "Story beats",          "Has a mini-narrative arc — setup → tension → payoff."),
    ("slider_social_tension",      "Social tension",       "Pokes at a shared frustration, conflict, or taboo."),
    ("slider_hook_pacing",         "Hook pacing",          "Speed to the punchline — slow burn (0) vs instant grab (10)."),
    ("slider_reward_density",      "Reward density",       "Jokes-per-second / layers of payoff packed into one piece."),
    ("slider_platform_fit",        "Platform fit",         "How native and optimized this feels for the target platform."),
    ("slider_novelty_familiarity", "Novelty / familiarity","Completely fresh angle (0) → comforting familiar format (10)."),
    ("slider_punchline_contrast",  "Punchline contrast",   "Surprise gap between setup and punchline — subverted expectation."),
    ("slider_absurdity",           "Absurdity",            "Logical / realistic (0) → completely unhinged and surreal (10)."),
    ("slider_edge_risk",           "Edge risk",            "Safe and inoffensive (0) → bold, edgy, potentially controversial (10)."),
]

# Keys shown by default in the UI (users can change selection at any time).
VIRALITY_DEFAULT_ACTIVE_KEYS: List[str] = [
    "slider_humor",
    "slider_emotional_intensity",
    "slider_relatability",
]

_SLIDER_KEY_ORDER = [k for k, _, _ in VIRALITY_SLIDER_KEYS]
_N = len(VIRALITY_SLIDER_KEYS)  # total virality dimensions; referenced in prompt f-strings

# Display: "Category · Template name" — category drives auto virality tuning.
MEME_FORMAT_BY_CATEGORY: List[tuple[str, List[str]]] = [
    (
        "Reaction",
        [
            "Drake yes / no",
            "Distracted boyfriend",
            "Expanding / galaxy brain",
            "Surprised Pikachu",
            "This Is Fine (dog)",
            "Stonks / Meme Man",
            "Change My Mind (street sign)",
            "American Chopper argument",
            "Two Buttons (sweating choice)",
            "They're the same picture (Pam)",
            "Trade Offer (I receive / you receive)",
            "I sleep / real shit (Sleeping Shaq)",
            "Is this a pigeon?",
            "Epic Handshake",
            "Running away balloon",
            "Gru's plan (4-panel board)",
            "Woman yelling at cat",
            "Buff Doge vs Cheems",
            "Waiting skeleton",
            "Panik / Kalm / Panik",
            "Always has been (astronauts)",
            "Chad vs virgin / GigaChad frame",
            "Me and the boys",
            "Homer disappears into bush",
            "Spider-Man pointing (two copies)",
            "Arthur clenched fist",
            "Roll Safe point to temple",
            "Hide the Pain Harold",
            "Monkey puppet side-eye",
            "Evil Kermit shoulder",
            "Disaster Girl smirk",
            "UNO draw 25 dilemma",
        ],
    ),
    (
        "Wojak & characters",
        [
            "Classic Feels Guy (Wojak)",
            "Doomer / Bloomer / Coomer lane",
            "Yes Chad / Nordic GigaChad",
            "NPC Wojak stare",
            "Soyjack vs Chad pointing",
            "Political compass 2×2 wojaks",
            "Colored squares / funny colors map",
            "Brainlet vs galaxy brain wojak",
            "Tradwife / tradguy caricature (gentle parody)",
            "Co-worker two-face meme",
        ],
    ),
    (
        "Dialogue & chat",
        [
            "Fake iPhone iMessage thread",
            "Fake Android SMS",
            "Fake Slack / Teams thread",
            "Fake Discord chat",
            "Group chat chaos (names + bubbles)",
            "Boss / employee text exchange",
            "Customer support transcript",
            "Reddit comment chain screenshot",
            "YouTube comment section parody",
            "Stack Overflow / dev forum parody",
            "Notes app apology / manifesto",
        ],
    ),
    (
        "Fake UI & screenshots",
        [
            "Fake tweet / X post",
            "Fake Instagram post + chrome",
            "Fake LinkedIn humblebrag",
            "Fake Facebook status",
            "Fake TikTok FYP caption bar",
            "Fake Google search results page",
            "Fake Yelp one-star rant",
            "Fake breaking news chyron",
            "Fake notification stack (buzzkill)",
            "Fake dating app profile + chat",
            "Fake Venmo / Cash App caption",
            "Fwd email chain energy",
            "Fake app store review rant",
        ],
    ),
    (
        "Multi-panel & strips",
        [
            "Minimal four-panel strip",
            "Rage comic layout (classic)",
            "Before / after (2-panel)",
            "Expectation vs reality",
            "POV vs what actually happened",
            "Loss-style minimalist panels (abstract)",
            "Oof stones comic progression",
        ],
    ),
    (
        "Charts & data",
        [
            "Line chart joke",
            "Bar chart punchline",
            "Pie chart absurdity",
            "Alignment chart (3×3 labels)",
            "Corporate infographic parody",
            "Map / geography meme",
            "Stock ticker / market panel",
            "Survey results / poll meme",
        ],
    ),
    (
        "Text & macros",
        [
            "Top/bottom Impact font macro",
            "Demotivational poster",
            "Motivational poster parody",
            "Slogan on stock photo",
            "Nobody: / Me: structure",
            "POV one-liner (caption-led)",
            "White text on colored box (Twitter-style)",
            "Increasingly verbose labels",
        ],
    ),
    (
        "Video-first layouts",
        [
            "TikTok text-on-screen first frame",
            "YouTube Shorts thumbnail + arrows",
            "Instagram Reels cover + hook",
            "Freeze-frame with explanatory arrows",
            "Fake lower-third news chyron (talking-head)",
            "Green-screen subject + caption",
        ],
    ),
    (
        "Experimental visuals",
        [
            "Deep fried / nuked aesthetic",
            "Surreal collage dreamscape",
            "AI cursed-image comedy",
            "Absurdist object labeling",
            "Post-irony layer cake (meta on meta)",
            "Vaporwave / glitch nostalgia",
        ],
    ),
    (
        "Classic image macros",
        [
            "Bad Luck Brian yearbook",
            "Success Kid fist pump",
            "First World Problems",
            "Scumbag Steve / Stacy hat",
            "Philosoraptor question",
            "Conspiracy Keanu",
            "Socially Awkward Penguin",
            "Futurama Fry squint",
            "Captain Picard facepalm",
            "Buzz Lightyear everywhere",
        ],
    ),
    (
        "Meta & participatory",
        [
            "Starter pack collage",
            "Bingo card / blackout bingo",
            "Tag yourself I'm…",
            "Put your finger on screen (text prompt)",
            "Choose all squares captcha parody",
            "Quote-tweet bait (written as meme)",
            "Rating scale / 1–10 joke grid",
            "Alignment quiz fake results",
        ],
    ),
    (
        "Brand & ad parody",
        [
            "Fake DTC / infomercial grab",
            "Sponsored post subtle roast",
            "AirPods ad silhouette parody",
            "Luxury brand minimal parody",
        ],
    ),
    (
        "Stock & cinematic",
        [
            "Cinematic still + unrelated caption",
            "WikiHow illustration mismatch",
            "Museum painting + modern caption",
            "Nature documentary freeze + joke",
        ],
    ),
    (
        "General",
        [
            "Reaction image (generic)",
            "Image macro (generic)",
            "Shitpost collage",
            "Wholesome comic moment",
            "Surreal photo edit",
        ],
    ),
]

MEME_FORMAT_OPTIONS: List[str] = [
    f"{cat} · {name}" for cat, names in MEME_FORMAT_BY_CATEGORY for name in names
]


def meme_format_categories() -> List[str]:
    return [cat for cat, _ in MEME_FORMAT_BY_CATEGORY]


def meme_format_labels_for_category(category: str) -> List[str]:
    for cat, names in MEME_FORMAT_BY_CATEGORY:
        if cat == category:
            return [f"{cat} · {name}" for name in names]
    return [f"General · {n}" for n in MEME_FORMAT_BY_CATEGORY[-1][1]]

# Integer deltas added to VIRALITY_SLIDER_NEUTRAL per slider, then clamped to 0–10.
_ARCHETYPE_VIRALITY_DELTAS: Dict[str, Dict[str, int]] = {
    "Reaction": {
        "slider_humor": 1,
        "slider_simplicity": 2,
        "slider_memetic_compression": 1,
        "slider_silent_readability": 2,
        "slider_repetition_exposure": 1,
        "slider_visual_polish": -1,
    },
    "Wojak & characters": {
        "slider_identity_signaling": 2,
        "slider_remixability": 1,
        "slider_nostalgia_layer": 1,
        "slider_participation": 1,
        "slider_cultural_relevance": 1,
        "slider_silent_readability": 1,
    },
    "Dialogue & chat": {
        "slider_simplicity": 1,
        "slider_story_beats": 2,
        "slider_social_tension": 1,
        "slider_hook_pacing": 1,
        "slider_reward_density": 1,
        "slider_silent_readability": 1,
    },
    "Fake UI & screenshots": {
        "slider_cultural_relevance": 1,
        "slider_platform_fit": 2,
        "slider_novelty_familiarity": 1,
        "slider_simplicity": 1,
        "slider_story_beats": 1,
        "slider_visual_polish": 1,
    },
    "Multi-panel & strips": {
        "slider_story_beats": 2,
        "slider_punchline_contrast": 1,
        "slider_reward_density": 1,
        "slider_hook_pacing": -1,
        "slider_simplicity": -1,
    },
    "Charts & data": {
        "slider_memetic_compression": 2,
        "slider_simplicity": 1,
        "slider_visual_polish": 1,
        "slider_relatability": -1,
        "slider_identity_signaling": 1,
    },
    "Text & macros": {
        "slider_simplicity": 2,
        "slider_memetic_compression": 2,
        "slider_silent_readability": 2,
        "slider_visual_polish": -1,
        "slider_punchline_contrast": 1,
    },
    "Video-first layouts": {
        "slider_hook_pacing": 2,
        "slider_platform_fit": 2,
        "slider_silent_readability": 2,
        "slider_simplicity": 1,
        "slider_reward_density": 1,
        "slider_story_beats": -1,
    },
    "Experimental visuals": {
        "slider_absurdity": 2,
        "slider_novelty_familiarity": 2,
        "slider_visual_polish": -2,
        "slider_edge_risk": 1,
        "slider_emotional_intensity": 1,
    },
    "Classic image macros": {
        "slider_repetition_exposure": 2,
        "slider_nostalgia_layer": 1,
        "slider_relatability": 1,
        "slider_memetic_compression": 1,
        "slider_simplicity": 1,
    },
    "Meta & participatory": {
        "slider_participation": 2,
        "slider_remixability": 2,
        "slider_identity_signaling": 1,
        "slider_cultural_relevance": 1,
        "slider_simplicity": -1,
    },
    "Brand & ad parody": {
        "slider_visual_polish": 2,
        "slider_cultural_relevance": 1,
        "slider_platform_fit": 1,
        "slider_edge_risk": 1,
    },
    "Stock & cinematic": {
        "slider_visual_polish": 2,
        "slider_emotional_intensity": 1,
        "slider_punchline_contrast": 2,
        "slider_simplicity": -1,
    },
    "General": {},
}

HUMOR_VIRALITY_DELTAS: Dict[str, Dict[str, int]] = {
    "absurd": {"slider_absurdity": 2, "slider_novelty_familiarity": 1, "slider_humor": 1},
    "ironic": {"slider_edge_risk": 1, "slider_identity_signaling": 1, "slider_punchline_contrast": 1},
    "self-deprecating": {"slider_relatability": 2, "slider_humor": 1, "slider_edge_risk": -1},
    "dark humor": {"slider_edge_risk": 2, "slider_emotional_intensity": 1, "slider_punchline_contrast": 1},
    "cringe": {"slider_emotional_intensity": 2, "slider_participation": 1, "slider_social_tension": 1},
    "satire": {"slider_cultural_relevance": 2, "slider_platform_fit": 1, "slider_edge_risk": 1},
    "wholesome": {"slider_edge_risk": -2, "slider_relatability": 1, "slider_absurdity": -1},
    "savage": {"slider_edge_risk": 2, "slider_humor": 1, "slider_social_tension": 1},
    "existential": {"slider_emotional_intensity": 2, "slider_absurdity": 1, "slider_nostalgia_layer": 1},
    "surreal": {"slider_absurdity": 2, "slider_novelty_familiarity": 2, "slider_visual_polish": -1},
}

PLATFORM_VIRALITY_DELTAS: Dict[str, Dict[str, int]] = {
    "TikTok": {
        "slider_hook_pacing": 2,
        "slider_platform_fit": 2,
        "slider_silent_readability": 2,
        "slider_participation": 1,
    },
    "Instagram": {
        "slider_visual_polish": 2,
        "slider_platform_fit": 2,
        "slider_hook_pacing": 1,
    },
    "X/Twitter": {
        "slider_memetic_compression": 2,
        "slider_cultural_relevance": 1,
        "slider_edge_risk": 1,
        "slider_remixability": 1,
    },
    "Reddit": {
        "slider_remixability": 2,
        "slider_identity_signaling": 1,
        "slider_participation": 1,
        "slider_cultural_relevance": 1,
    },
    "LinkedIn": {
        "slider_edge_risk": -2,
        "slider_visual_polish": 1,
        "slider_story_beats": 1,
        "slider_platform_fit": 2,
    },
    "YouTube Shorts": {
        "slider_hook_pacing": 2,
        "slider_reward_density": 1,
        "slider_silent_readability": 2,
    },
    "Facebook": {
        "slider_relatability": 2,
        "slider_repetition_exposure": 1,
        "slider_edge_risk": -1,
        "slider_simplicity": 1,
    },
}

VIRALITY_PROFILE_FLAVORS: Dict[str, Dict[str, int]] = {
    "Balanced smart": {},
    "Aggressive viral": {
        "slider_hook_pacing": 1,
        "slider_memetic_compression": 1,
        "slider_participation": 1,
        "slider_emotional_intensity": 1,
        "slider_reward_density": 1,
    },
    "Wholesome safe": {
        "slider_edge_risk": -2,
        "slider_social_tension": -1,
        "slider_relatability": 1,
        "slider_visual_polish": 1,
    },
    "Niche in-group": {
        "slider_identity_signaling": 2,
        "slider_cultural_relevance": 1,
        "slider_relatability": -1,
        "slider_novelty_familiarity": 1,
    },
    "Mainstream reach": {
        "slider_simplicity": 2,
        "slider_relatability": 1,
        "slider_identity_signaling": -1,
        "slider_silent_readability": 1,
    },
    "Chaos / shitpost": {
        "slider_absurdity": 2,
        "slider_visual_polish": -2,
        "slider_edge_risk": 1,
        "slider_novelty_familiarity": 1,
    },
}


def _category_from_meme_format(meme_format: str) -> str:
    if " · " in meme_format:
        return meme_format.split(" · ", 1)[0].strip()
    return "General"


def _sum_deltas(*delta_dicts: Dict[str, int]) -> Dict[str, int]:
    out: Dict[str, int] = {k: 0 for k in _SLIDER_KEY_ORDER}
    for d in delta_dicts:
        for key, val in d.items():
            if key in out:
                out[key] += int(val)
    return out


def auto_virality_sliders(
    *,
    meme_format: str,
    humor_style: str,
    platform: str,
    profile_flavor: str = "Balanced smart",
) -> Dict[str, int]:
    """
    Derive 0–10 slider values from meme format category, humor style, platform, and optional flavor.
    """
    category = _category_from_meme_format(meme_format)
    fmt_d = _ARCHETYPE_VIRALITY_DELTAS.get(category, _ARCHETYPE_VIRALITY_DELTAS["General"])
    hum_d = HUMOR_VIRALITY_DELTAS.get(humor_style, {})
    plat_d = PLATFORM_VIRALITY_DELTAS.get(platform, {})
    flavor_d = VIRALITY_PROFILE_FLAVORS.get(profile_flavor, {})
    combined = _sum_deltas(fmt_d, hum_d, plat_d, flavor_d)
    out: Dict[str, int] = {}
    for key in _SLIDER_KEY_ORDER:
        out[key] = max(
            VIRALITY_SLIDER_MIN,
            min(VIRALITY_SLIDER_MAX, VIRALITY_SLIDER_NEUTRAL + combined[key]),
        )
    return out


def random_virality_sliders(
    *,
    meme_format: str,
    humor_style: str,
    platform: str,
    rng: Optional[random.Random] = None,
) -> Dict[str, int]:
    """Sensible random variation around auto_virality_sliders (same flavor pool)."""
    r = rng or random.Random()
    flavors = [k for k in VIRALITY_PROFILE_FLAVORS if k != "Balanced smart"]
    flavor = r.choice(flavors)
    base = auto_virality_sliders(
        meme_format=meme_format, humor_style=humor_style, platform=platform, profile_flavor=flavor
    )
    jitter = {k: r.randint(-1, 1) for k in _SLIDER_KEY_ORDER}
    merged = _sum_deltas(jitter)
    return {
        k: max(VIRALITY_SLIDER_MIN, min(VIRALITY_SLIDER_MAX, base[k] + merged[k]))
        for k in _SLIDER_KEY_ORDER
    }


def shuffle_virality_sliders(*, rng: Optional[random.Random] = None) -> Dict[str, int]:
    """Random 0–10 on every dimension (randomize / shuffle the field)."""
    r = rng or random.Random()
    return {
        k: r.randint(VIRALITY_SLIDER_MIN, VIRALITY_SLIDER_MAX)
        for k in _SLIDER_KEY_ORDER
    }


def zero_virality_sliders() -> Dict[str, int]:
    """All sliders at zero (off)."""
    return {k: VIRALITY_SLIDER_DEFAULT for k in _SLIDER_KEY_ORDER}

def ensure_session_state() -> None:
    if "model_name" not in st.session_state:
        st.session_state.model_name = DEFAULT_OPENAI_MODEL
    if "gemini_model_name" not in st.session_state:
        st.session_state.gemini_model_name = DEFAULT_GEMINI_IMAGE_MODEL
    if "input_cost_per_m" not in st.session_state:
        st.session_state.input_cost_per_m = DEFAULT_INPUT_COST_PER_M
    if "output_cost_per_m" not in st.session_state:
        st.session_state.output_cost_per_m = DEFAULT_OUTPUT_COST_PER_M
    if "meme_aspect_ratio" not in st.session_state:
        st.session_state.meme_aspect_ratio = "1:1"
    if "meme_image_size" not in st.session_state:
        st.session_state.meme_image_size = "2K"
    if "_virality_slider_domain" not in st.session_state:
        st.session_state["_virality_slider_domain"] = "0-10-v1"
        for key, _label, _help in VIRALITY_SLIDER_KEYS:
            st.session_state[key] = VIRALITY_SLIDER_DEFAULT
    else:
        for key, _label, _help in VIRALITY_SLIDER_KEYS:
            if key not in st.session_state:
                st.session_state[key] = VIRALITY_SLIDER_DEFAULT
            else:
                v = int(st.session_state[key])
                st.session_state[key] = max(VIRALITY_SLIDER_MIN, min(VIRALITY_SLIDER_MAX, v))
    # Active slider selection — which axes are visible + sent to the model.
    if "virality_active_keys" not in st.session_state:
        st.session_state["virality_active_keys"] = list(VIRALITY_DEFAULT_ACTIVE_KEYS)





MEME_STEP1_SYSTEM_PROMPT = f"""
You are an elite meme strategist, internet culture analyst, comedy writer, and viral content architect.

STEP 1 ONLY: propose **exactly five** distinct meme text concepts (caption / on-image copy / dialogue) tailored to the user’s **creative brief**, **smart profile flavor**, **example text** (voice / reference copy), the **active virality sliders** provided (each 0–10; **0 = off / none** for that axis, **10 = maximum**), and any **example meme image** attached.

Rules:
- Meme copy must feel native to internet culture, instantly readable, remixable, and aligned to the creative brief and example text (not generic corporate humor).
- Respect safety: no hate, harassment, real-person attacks, or policy-violating content.
- Each option must be meaningfully different (different angle, format hook, or punchline structure).
- Before returning JSON, internally score each option 1–10 on: shareability, clarity, originality, emotional_impact, screenshot_worthiness, comment_bait_potential, remixability.
- If any score is below 8, rewrite that option until all scores are 8+ (still only output the final five).

Return **only** valid JSON with this shape (no markdown fences):
{{
  "options": [
    {{
      "meme_text": "string — the actual words that would appear on the meme / caption",
      "why_it_works": "string — 2–4 sentences: viral logic given the brief, flavor, example text, and sliders",
      "viral_scores": {{
        "shareability": 1,
        "clarity": 1,
        "originality": 1,
        "emotional_impact": 1,
        "screenshot_worthy": 1,
        "comment_bait": 1,
        "remixability": 1
      }},
      "format_hint": "string — e.g. reaction macro, fake screenshot, starter pack, etc."
    }}
  ]
}}

The "options" array must have length exactly 5.
""".strip()


MEME_STEP2_SYSTEM_PROMPT = f"""
You are an elite meme strategist, internet culture analyst, comedy writer, and viral content architect.

STEP 2: The user already chose ONE meme text option. Your job is to produce:
1) A structured **meme_analysis** write-up (markdown) covering viral potential, emotional triggers, identity signaling, why people share, remix potential, platform fit — aligned to the {_N} virality dimensions and brand voice.
2) A separate **image_prompt**: a detailed AI image-generation prompt for Nano Banana / Gemini image models that visually reinforces the joke in under 2 seconds. Include camera angle, emotion, composition, lighting, stylization, mobile readability, meme format references. The image should render the meme text legibly as part of the scene (bold meme typography, high contrast).
3) **negative_prompt**: things to avoid (watermarks, clutter, illegible text, off-brand colors).
4) **suggested_aspect_ratio**: one of: 1:1, 2:3, 3:2, 3:4, 4:3, 9:16, 16:9, 21:9 — pick what fits the stated platform best.

Never output weak or generic memes. Stay policy-safe.

Return **only** valid JSON (no markdown fences):
{{
  "meme_analysis": "markdown string",
  "meme_text_final": "string — repeat the chosen meme text verbatim (may lightly tighten for clarity)",
  "image_prompt": "string",
  "negative_prompt": "string",
  "suggested_aspect_ratio": "string"
}}
""".strip()


def sliders_from_session() -> Dict[str, int]:
    out: Dict[str, int] = {}
    for key, _label, _help in VIRALITY_SLIDER_KEYS:
        raw = int(st.session_state.get(key, VIRALITY_SLIDER_DEFAULT))
        out[key] = max(VIRALITY_SLIDER_MIN, min(VIRALITY_SLIDER_MAX, raw))
    return out


def format_sliders_for_prompt(sliders: Dict[str, int]) -> str:
    """Only list dimensions present in *sliders* (active axes from the UI)."""
    lines = []
    for key, label, _h in VIRALITY_SLIDER_KEYS:
        if key not in sliders:
            continue
        v = max(
            VIRALITY_SLIDER_MIN,
            min(VIRALITY_SLIDER_MAX, int(sliders[key])),
        )
        lines.append(f"- {label}: {v}/10 (0 = off)")
    return "\n".join(lines) if lines else "(no active dimensions — user should select at least one slider axis)"


def format_virality_dimensions_catalog() -> str:
    lines = []
    for key, label, h in VIRALITY_SLIDER_KEYS:
        lines.append(f"- `{key}` — **{label}**: {h}")
    return "\n".join(lines)


VIRALITY_IDEAS_SYSTEM_PROMPT = (
    "You map a user's creative brief into virality controls for meme ideation.\n"
    "Each dimension is an integer **0–10**: **0 = off / none** for that axis, **10 = maximum**.\n"
    'Return **only** valid JSON (no markdown fences) with keys "sliders" (object) and "rationale" (string).\n'
    '"sliders" must contain every required key exactly once.\n\n'
    "Required keys:\n"
    + ", ".join(_SLIDER_KEY_ORDER)
    + "\n\nDimension reference:\n"
    + format_virality_dimensions_catalog()
    + "\n\nUse the full range when the brief implies it; use 0 when an axis clearly does not apply. "
    "Infer tone, risk tolerance, platform energy, and shareability from what is stated or implied. "
    "Stay policy-safe (no hate, harassment, or real-person attacks)."
)


def build_virality_ideas_user_payload(
    *,
    ideas: str,
    platform: str,
    humor_style: str,
    meme_format: str,
    cultural_relevance: str,
) -> str:
    return f"""USER_CREATIVE_BRIEF (free text — primary signal):
{ideas.strip()}

CURRENT_CAMPAIGN_CONTROLS (use as strong hints unless the brief explicitly overrides):
PLATFORM: {platform}
HUMOR_STYLE: {humor_style}
MEME_FORMAT: {meme_format}
CULTURAL_RELEVANCE: {cultural_relevance.strip() or "(none)"}

Return JSON per system instructions."""


def estimate_cost_usd(
    prompt_tokens: int, completion_tokens: int, input_cost_per_m: float, output_cost_per_m: float
) -> float:
    input_cost = (prompt_tokens / 1_000_000) * input_cost_per_m
    output_cost = (completion_tokens / 1_000_000) * output_cost_per_m
    return input_cost + output_cost


def _response_text(response: Any) -> str:
    content = ""
    if response.choices and response.choices[0].message:
        content = response.choices[0].message.content or ""
    return content.strip()


def _openai_json_completion(
    *,
    client: OpenAI,
    model: str,
    system: str,
    user_content: str | List[Dict[str, Any]],
    input_cost_per_m: float,
    output_cost_per_m: float,
) -> tuple[dict[str, Any], dict[str, int], float]:
    """Chat completion expecting JSON object; returns parsed dict + usage + est cost."""
    kwargs: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
    }
    try:
        kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**kwargs)
    except Exception:
        kwargs.pop("response_format", None)
        response = client.chat.completions.create(**kwargs)

    raw = _response_text(response)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            parsed = json.loads(raw[start : end + 1])
        else:
            raise ValueError(f"Model did not return valid JSON: {raw[:500]}...")

    usage = response.usage
    pt = int(getattr(usage, "prompt_tokens", 0) or 0)
    ct = int(getattr(usage, "completion_tokens", 0) or 0)
    tt = int(getattr(usage, "total_tokens", 0) or 0)
    cost = estimate_cost_usd(pt, ct, float(input_cost_per_m), float(output_cost_per_m))
    return parsed, {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": tt}, cost


def normalize_inferred_sliders(parsed: Dict[str, Any]) -> tuple[Dict[str, int], str]:
    """Extract sliders from model JSON; accept nested under \"sliders\" or flat (legacy)."""
    block = parsed.get("sliders")
    if not isinstance(block, dict):
        block = {k: parsed.get(k) for k in _SLIDER_KEY_ORDER}
    out: Dict[str, int] = {}
    for key in _SLIDER_KEY_ORDER:
        raw = block.get(key, VIRALITY_SLIDER_DEFAULT)
        try:
            iv = int(round(float(raw)))
        except (TypeError, ValueError):
            iv = VIRALITY_SLIDER_DEFAULT
        out[key] = max(VIRALITY_SLIDER_MIN, min(VIRALITY_SLIDER_MAX, iv))
    rationale = str(parsed.get("rationale") or parsed.get("notes") or parsed.get("why") or "").strip()
    return out, rationale


def infer_virality_sliders_from_ideas(
    *,
    api_key: str,
    model: str,
    ideas: str,
    platform: str,
    humor_style: str,
    meme_format: str,
    cultural_relevance: str,
    input_cost_per_m: float = DEFAULT_INPUT_COST_PER_M,
    output_cost_per_m: float = DEFAULT_OUTPUT_COST_PER_M,
) -> Dict[str, Any]:
    """One OpenAI JSON call: brief → all virality sliders (0–10), editable in UI after."""
    client = OpenAI(api_key=api_key)
    user_text = build_virality_ideas_user_payload(
        ideas=ideas,
        platform=platform,
        humor_style=humor_style,
        meme_format=meme_format,
        cultural_relevance=cultural_relevance,
    )
    parsed, usage, est = _openai_json_completion(
        client=client,
        model=model,
        system=VIRALITY_IDEAS_SYSTEM_PROMPT,
        user_content=user_text,
        input_cost_per_m=input_cost_per_m,
        output_cost_per_m=output_cost_per_m,
    )
    sliders, rationale = normalize_inferred_sliders(parsed)
    return {
        "sliders": sliders,
        "rationale": rationale,
        "usage_infer": usage,
        "estimated_cost_infer_usd": est,
        "model": model,
    }


def build_step1_user_payload(
    *,
    creative_brief: str,
    profile_flavor: str,
    example_text: str,
    sliders: Dict[str, int],
    has_example_image: bool,
) -> str:
    slider_block = format_sliders_for_prompt(sliders)
    return f"""
CREATIVE_BRIEF (optional):
{creative_brief}

SMART_PROFILE_FLAVOR:
{profile_flavor}

EXAMPLE_TEXT (voice / reference copy):
{example_text}

VIRALITY_SLIDERS (active dimensions, 0=off, 10=max):
{slider_block}

{"An EXAMPLE_MEME image is attached — match its energy, layout language, and visual meme grammar while inventing fresh content." if has_example_image else "No example image was attached; invent a strong visual meme format from the brief, flavor, example text, and slider axes."}

Produce the JSON per system instructions.
""".strip()


def generate_caption_options(
    *,
    api_key: str,
    model: str,
    example_image_bytes: Optional[bytes],
    example_image_mime: str,
    creative_brief: str,
    profile_flavor: str,
    example_text: str,
    sliders: Dict[str, int],
    input_cost_per_m: float = DEFAULT_INPUT_COST_PER_M,
    output_cost_per_m: float = DEFAULT_OUTPUT_COST_PER_M,
) -> Dict[str, Any]:
    client = OpenAI(api_key=api_key)
    user_text = build_step1_user_payload(
        creative_brief=creative_brief,
        profile_flavor=profile_flavor,
        example_text=example_text,
        sliders=sliders,
        has_example_image=example_image_bytes is not None,
    )

    if example_image_bytes:
        b64 = base64.standard_b64encode(example_image_bytes).decode("ascii")
        mime = example_image_mime if "/" in example_image_mime else "image/png"
        user_content: str | List[Dict[str, Any]] = [
            {"type": "text", "text": user_text},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]
    else:
        user_content = user_text

    parsed, usage, est = _openai_json_completion(
        client=client,
        model=model,
        system=MEME_STEP1_SYSTEM_PROMPT,
        user_content=user_content,
        input_cost_per_m=input_cost_per_m,
        output_cost_per_m=output_cost_per_m,
    )
    options = parsed.get("options")
    if not isinstance(options, list) or len(options) != 5:
        raise ValueError("Expected JSON with 'options' array of length 5.")
    return {
        "options": options,
        "usage_step1": usage,
        "estimated_cost_step1_usd": est,
        "model": model,
    }


def build_step2_user_payload(
    *,
    chosen: Dict[str, Any],
    platform: str,
    humor_style: str,
    meme_format: str,
    cultural_relevance: str,
    example_text: str,
    sliders: Dict[str, int],
) -> str:
    slider_block = format_sliders_for_prompt(sliders)
    return f"""
INPUT_VARIABLES:
PLATFORM: {platform}
HUMOR_STYLE: {humor_style}
MEME_FORMAT: {meme_format}
CULTURAL_RELEVANCE: {cultural_relevance}

EXAMPLE_TEXT:
{example_text}

VIRALITY_SLIDERS:
{slider_block}

CHOSEN_OPTION (from step 1):
{json.dumps(chosen, ensure_ascii=False, indent=2)}

Now output JSON per STEP 2 system instructions. The image_prompt must bake in the final meme wording with readable typography.
""".strip()


def generate_meme_pack_step2(
    *,
    api_key: str,
    model: str,
    chosen_option: Dict[str, Any],
    platform: str,
    humor_style: str,
    meme_format: str,
    cultural_relevance: str,
    example_text: str,
    sliders: Dict[str, int],
    input_cost_per_m: float = DEFAULT_INPUT_COST_PER_M,
    output_cost_per_m: float = DEFAULT_OUTPUT_COST_PER_M,
) -> Dict[str, Any]:
    client = OpenAI(api_key=api_key)
    user_text = build_step2_user_payload(
        chosen=chosen_option,
        platform=platform,
        humor_style=humor_style,
        meme_format=meme_format,
        cultural_relevance=cultural_relevance,
        example_text=example_text,
        sliders=sliders,
    )
    parsed, usage, est = _openai_json_completion(
        client=client,
        model=model,
        system=MEME_STEP2_SYSTEM_PROMPT,
        user_content=user_text,
        input_cost_per_m=input_cost_per_m,
        output_cost_per_m=output_cost_per_m,
    )
    for key in ("meme_analysis", "image_prompt"):
        if key not in parsed or not str(parsed.get(key, "")).strip():
            raise ValueError(f"Step 2 JSON missing {key}")
    return {
        "meme_analysis": str(parsed["meme_analysis"]),
        "meme_text_final": str(parsed.get("meme_text_final", chosen_option.get("meme_text", ""))),
        "image_prompt": str(parsed["image_prompt"]),
        "negative_prompt": str(parsed.get("negative_prompt", "")),
        "suggested_aspect_ratio": str(parsed.get("suggested_aspect_ratio", "1:1")),
        "usage_step2": usage,
        "estimated_cost_step2_usd": est,
        "raw_step2": parsed,
    }


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
            maybe = decode_inline_data(part)
            if maybe:
                images.append(maybe)
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


def generate_gemini_meme_image(
    *,
    api_key: str,
    model: str,
    image_prompt: str,
    negative_prompt: str,
    brand_voice: str,
    aspect_ratio: str,
    image_size: str,
) -> bytes:
    from google import genai
    from google.genai import types

    neg = negative_prompt.strip()
    full_prompt = f"""{image_prompt.strip()}

Avoid / negative prompt: {neg if neg else "watermarks, cluttered backgrounds, illegible tiny text, random logos"}

Brand alignment (palette & mood only — do not contradict the joke):
{brand_voice.strip()}
""".strip()

    client = genai.Client(api_key=api_key)
    img_kwargs: Dict[str, Any] = {}
    if aspect_ratio:
        img_kwargs["aspect_ratio"] = aspect_ratio
    if image_size:
        img_kwargs["image_size"] = image_size
    img_cfg = types.ImageConfig(**img_kwargs) if img_kwargs else None
    cfg_full = (
        types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"], image_config=img_cfg)
        if img_cfg
        else None
    )
    cfg_basic = types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"])

    response = None
    last_err: Optional[Exception] = None
    for cfg in ([cfg_full] if cfg_full else []) + [cfg_basic]:
        try:
            response = client.models.generate_content(model=model, contents=full_prompt, config=cfg)
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
    return images[0]


def slugify(value: str, *, max_len: int = 40) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    clean = clean.strip("-")
    if len(clean) > max_len:
        clean = clean[:max_len].rstrip("-")
    return clean or "meme"


def save_meme(
    *,
    image_bytes: bytes,
    metadata: Dict[str, Any],
) -> Dict[str, str]:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    topic = str(metadata.get("meme_slug_source", "meme"))
    stem = f"{timestamp}-{slugify(topic)}"
    png_path = OUTPUT_DIR / f"{stem}.png"
    json_path = OUTPUT_DIR / f"{stem}.json"

    with open(png_path, "wb") as f:
        f.write(image_bytes)
    metadata_out = {**metadata, "png_file": str(png_path), "json_file": str(json_path)}
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metadata_out, f, indent=2, ensure_ascii=False)

    return {"png": str(png_path), "json": str(json_path)}


_STOCK_HISTORY_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif"})


def read_recent_history(*, limit: int = 24) -> List[Path]:
    if not OUTPUT_DIR.is_dir():
        return []
    paths = [p for p in OUTPUT_DIR.iterdir() if p.is_file() and p.suffix.lower() in _STOCK_HISTORY_SUFFIXES]
    paths.sort(key=lambda q: q.stat().st_mtime, reverse=True)
    return paths[:limit]
