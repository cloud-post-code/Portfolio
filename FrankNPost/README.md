# FrankNPost

Streamlit app that **generates social and blog content** from your brand theme, persona, and source material — one OpenAI call per channel.

## What it does

Streamlit post generator for:
- Blog posts (GEO + SEO prompt mode)
- LinkedIn posts
- Facebook posts
- Instagram posts

Each selected mode runs as a separate OpenAI API call, with per-call token usage and estimated cost tracking.

## Features

- Brand theme system (Peel-Pal style) with dedicated Theme page
- Multi-mode generation in one run (`blog`, `linkedin`, `facebook`, `instagram`)
- Inputs from raw text plus uploads: `.md`, `.txt`, `.docx`, `.pdf`
- Mode-specific output saves as Markdown + JSON metadata
- Recent output history from local output folder

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set:

```bash
OPENAI_API_KEY=your_key_here
```

Optional:

```bash
FRANKNPOST_OUTPUT_DIR=/your/output/folder
```

## Run

```bash
streamlit run app.py
```
