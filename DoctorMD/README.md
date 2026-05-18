# Doctor MD

Local Flask app that **converts documents to Markdown** in the browser. Drop a file, preview the result, copy it, or download a `.md` file.

## What it does

- Accepts common formats: **PDF**, **Word** (`.docx`), **HTML**, **RTF**, **TXT**, **CSV**, and **Markdown** (pass-through).
- Converts structure where possible (headings, bold/italic, tables in Word, etc.).
- Shows a live preview (raw Markdown or rendered) with word/line stats.
- Downloads the converted file with the same base name.

Runs entirely on your machine; files are not uploaded to a third-party conversion service beyond what your own stack does locally.

## Setup

```bash
cd DoctorMD
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

No API key required.

## Run

```bash
python app.py
```

Open **http://127.0.0.1:5050** (default port).

Max upload size: 50 MB per file.
