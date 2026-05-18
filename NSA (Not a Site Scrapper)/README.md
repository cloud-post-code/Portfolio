# NSA (Not a Site Scrapper)

Streamlit app that **crawls company websites in batch** and uses OpenAI to build a structured business profile for each URL. Results append to a CSV after every site so you can stop and still keep progress.

## What it does

1. Paste a list of URLs (one per line).
2. The app queues every URL, then processes them **one after another** without manual steps between sites.
3. For each site it crawls key pages (about, team, services, contact, etc.), extracts text and contact hints, and asks the model for a company profile.
4. Writes or updates **`nsa_profiles.csv`** in this folder after each company finishes.

Output columns include company name, summary, industry, location, social links, about-page details, stakeholders, and more.

## Setup

```bash
cd "NSA (Not a Site Scrapper)"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` in this folder:

```bash
OPENAI_API_KEY=your_key_here
```

## Run

```bash
streamlit run app.py
```

## Settings

- **Model** — sidebar (default `gpt-4o-mini`)
- **Max pages to crawl** — per site (default 10)
- **CSV output path** — defaults to `./nsa_profiles.csv`

Do not refresh the browser tab while a batch is running.
