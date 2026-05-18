# Portfolio — Personal Mini Projects

This repo is a collection of **personal tools** I build and run for myself: simple web frontends and scripts that make everyday tasks faster. They are not a commercial product line—just projects I actually use, kept here for easy access.

**You are welcome to clone, test, fork, or borrow anything that is useful.** If something breaks or docs are thin in a subfolder, open an issue or adapt it to your setup.

## What these are

Most folders are **local-first apps** (Streamlit, Flask, or Next.js) meant to run on your machine:

- Quick UIs over APIs (OpenAI, Gemini, etc.)
- One-off workflows (batch site research, doc conversion, post generation)
- Lightweight utilities without heavy deployment ceremony

I treat this repo as a **personal dashboard of frontends**: spin up what I need, use it, move on. Stability and polish vary by project; newer experiments may be rougher than older ones.

## Projects

| Folder | What it does | Stack |
|--------|----------------|-------|
| [**NSA**](NSA/) | **Node Site Agent** — crawl sites in batch, profile companies, stream results to CSV | Streamlit, OpenAI |
| [**DoctorMD**](DoctorMD/) | Convert documents (PDF, Word, HTML, etc.) to Markdown in the browser | Flask |
| [**FrankNPost**](FrankNPost/) | Generate blog, LinkedIn, Facebook, and Instagram posts from themes and uploads | Streamlit, OpenAI |
| [**ViralSoup**](ViralSoup/) | Brand-aligned meme captions + image generation | Streamlit, OpenAI, Gemini |
| [**Peel-Pal**](Peel-Pal/) | Brand-themed image generation studio with local gallery | Streamlit, Gemini |
| [**HabitTracker**](HabitTracker/) | Daily habit check-ins, streaks, sleep logging | Flask, SQLite |
| [**Yap-to-Context**](Yap-to-Context/) | Voice/transcript ingest → organized folder tree and documents | Next.js, Postgres |
| [**Agent System**](Agent%20System/) | Prompt templates for shop-building agents (not a runnable app) | Markdown |

Each runnable project has its own `README.md`, `requirements.txt` or `package.json`, and often a `.env.example`. Start there for setup details.

## Quick start (typical Python app)

```bash
cd <project-folder>
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # if present — add your API keys
```

Then run whatever that project’s README says (usually `streamlit run app.py` or `python app.py`).

**Yap-to-Context** is Node-based:

```bash
cd Yap-to-Context
npm install
cp .env.example .env
npm run dev
```

## API keys and secrets

- **Never commit `.env` files.** They are gitignored per project.
- Most apps need at least an **OpenAI** key; some also use **Gemini** or a database URL (see each project).
- Keys stay on your machine unless you deploy somewhere yourself.

## Using this repo

- **Try it:** Clone, install deps for one folder, run locally.
- **Reuse it:** Copy a project out, rename it, hack on it—no permission needed.
- **Expect personal defaults:** Output paths, models, and UX choices reflect how I work, not a generic product spec.

If you build on something here and improve it, great. This repo exists so useful frontends stay in one place and stay easy to open when needed.

## License

Unless a subfolder states otherwise, treat the code as **personal / use-at-your-own-risk**. No warranty; you are responsible for API usage, costs, and compliance when you run these tools.
