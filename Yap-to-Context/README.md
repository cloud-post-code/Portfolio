# Yap-to-Context

Next.js app that turns **voice notes and transcripts** into an organized folder tree of documents. Ingest audio or text, let OpenAI extract structure, then browse folders, approve AI folder proposals, and export zips.

## What it does

- **Ingest** — upload or paste transcript content; optional audio storage on disk.
- **Extract** — OpenAI proposes folders, documents, and metadata from what you said.
- **Organize** — browse a tree (Company, Blog, Ideas, Inbox roots seeded on first run).
- **Approvals** — review pending folder proposals before they are applied.
- **Export** — download a folder and its documents as a zip.

Uses **PostgreSQL** for data and a filesystem path for audio files (not stored in the DB).

## Setup

```bash
cd Yap-to-Context
npm install
cp .env.example .env
```

Configure `.env`:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string |
| `OPENAI_API_KEY` | Transcription and extraction |
| `AUTH_SECRET` | Login password and API bearer token |
| `AUDIO_STORAGE_PATH` | Optional; defaults to `./storage/audio` |

Run migrations (see `package.json` scripts: `db:push` or `db:migrate`).

## Run

```bash
npm run dev
```

Open the URL shown in the terminal (default **http://localhost:3000**).

## Production

`npm run build` then `npm start`. See `railway.toml` if deploying to Railway with Postgres and a persistent volume for audio.
