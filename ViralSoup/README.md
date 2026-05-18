# ViralSoup

Local Streamlit app for **brand-voice-aligned, audience-targeted memes**: OpenAI generates caption options and final analysis + image prompt; **Gemini Nano Banana** (`gemini-2.5-flash-image`) renders the meme image.

## Features

- **Step 1:** Generate **5** caption/text options with short “why it works” explanations (JSON from OpenAI).
- **Step 2:** Pick one option → OpenAI produces viral analysis + detailed image prompt → Gemini generates the PNG.
- **12 virality sliders** (1–10): humor, emotional intensity, simplicity, cultural relevance, remixability, identity signaling, platform fit, novelty/familiarity, participation, memetic compression, edge/risk, repetition familiarity.
- **Brand theme + persona** (same shape as FrankNPost) via sidebar and dedicated pages.
- Saves **PNG + JSON** metadata under `Generated Memes/` (repo root by default).

## Setup

```bash
cd ViralSoup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set in `.env`:

```bash
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
```

Optional:

```bash
VIRALSOUP_OUTPUT_DIR=/path/to/Generated Memes
```

(`MEMEFORGE_OUTPUT_DIR` is still read as a legacy fallback if set.)

## Run

```bash
streamlit run app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`).

## Models

- **OpenAI:** default `gpt-5-nano` (change on **Model** page). Use a vision-capable model like `gpt-4o-mini` if Step 1 should strongly read your **example meme** image.
- **Gemini image:** default `gemini-2.5-flash-image` (Nano Banana).

## Troubleshooting

- **Missing keys:** set both API keys in `.env`.
- **Step 1 JSON errors:** try `gpt-4o-mini` or rerun; ensure the model supports `response_format` JSON mode.
- **No image from Gemini:** confirm your project can use image generation; try another model ID on the Model page.
