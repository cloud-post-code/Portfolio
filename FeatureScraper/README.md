# FeatureScraper

Point it at any web page and get back:

- **Feature inventory** — every feature grouped by category (Auth, Forms, Commerce, etc.), with UI components, user actions, and data requirements.
- **Data schema** — all database tables and fields needed to support those features, downloadable as SQL.
- **Cursor prompt** — a self-contained prompt you can paste directly into Cursor to rebuild the entire application from scratch.

## Setup

```bash
cp .env.example .env
# Add your OpenAI API key to .env

pip3 install -r requirements.txt
streamlit run app.py
```

## Usage

1. Paste a URL into the input bar and click **Analyze →**
2. Wait ~15–30 seconds for the scrape + LLM analysis
3. Browse the three output tabs:
   - **Features** — filterable cards grouped by category
   - **Data Schema** — all inferred tables with fields, types, relationships, and indexes
   - **Cursor Prompt** — copy-paste-ready rebuild prompt

Downloads available: features as Markdown, schema as SQL, and the Cursor prompt as `.txt`.

## How it works

1. **scraper.py** fetches the page and extracts a structured summary (nav, forms, buttons, tables, detected libraries, JSON-LD types, visible text).
2. **analyzer.py** sends that summary to GPT-4o with a structured prompt, getting back features + schema + cursor prompt as JSON.
3. **app.py** renders everything in a Streamlit UI with dark-themed cards.

## Models

| Model | Notes |
|---|---|
| `gpt-4o` | Best analysis quality (default) |
| `gpt-4o-mini` | Faster, cheaper, slightly less thorough |
| `gpt-4-turbo` | Alternative if 4o unavailable |
