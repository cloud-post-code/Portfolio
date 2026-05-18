# Brand-Aligned Image Generator

Mini localhost app that ingests your brand theme + prompt, generates images with Gemini, and saves outputs to a local folder.

## Features

- Theme Template form matching your provided structure
- Prompt composer that blends brand inputs with your build request
- Gemini image generation (`GEMINI_API_KEY`)
- Auto-save PNG image files
- Local gallery/history from your save folder (default: `./Design Assets/Stock Images`)

## Project Structure

```text
Peel-Pal/
  app.py
  studio_common.py
  Design Assets/
    Stock Images/
  requirements.txt
  .env.example
  (outputs default to ./Design Assets/Stock Images)
```

## Setup

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variable:

```bash
cp .env.example .env
```

Then edit `.env` and set:

```bash
GEMINI_API_KEY=your_real_key
```

## Run

```bash
streamlit run app.py
```

Open the local URL shown by Streamlit (usually `http://localhost:8501`).

## How It Works

1. Fill in the full brand theme template.
2. Enter a build prompt describing the desired image.
3. Click **Generate Brand Image**.
4. App sends a compiled brand-safe prompt to Gemini.
5. Generated images are saved under `Design Assets/Stock Images` inside Peel-Pal, unless `BRAND_IMAGE_OUTPUT_DIR` overrides it.

## Troubleshooting

- **Missing API key**: set `GEMINI_API_KEY` in `.env` or shell environment.
- **No image returned**: try a different model name or a more specific prompt.
- **Model/permission errors**: confirm your Gemini account/project has access to image generation.
- **Dependency issues**: upgrade pip and reinstall requirements.
