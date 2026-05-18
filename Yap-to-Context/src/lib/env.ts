import path from "path";
import { productionLikeDeployment } from "@/lib/deploy-env";

/** PostgreSQL connection URL (Railway injects when Postgres is linked). */
export function getDatabaseUrl(): string {
  const url = process.env.DATABASE_URL?.trim();
  if (url) return url;
  if (productionLikeDeployment()) {
    throw new Error(
      "DATABASE_URL is required in production (link Railway Postgres to this service).",
    );
  }
  throw new Error(
    "DATABASE_URL is not set. Example: postgresql://user:pass@127.0.0.1:5432/yap_to_context",
  );
}

/** OpenAI API key (Railway env var). Throws if missing. */
export function getOpenAiApiKey(): string {
  const v = process.env.OPENAI_API_KEY?.trim();
  if (v) return v;
  throw new Error(
    "OPENAI_API_KEY is not set. Add it as a Railway service variable (or in .env locally).",
  );
}

export function hasOpenAiApiKey(): boolean {
  return !!process.env.OPENAI_API_KEY?.trim();
}

export function getAudioStoragePath(): string {
  const p = process.env.AUDIO_STORAGE_PATH?.trim();
  if (p) return p;
  if (productionLikeDeployment()) return "/data/audio";
  return path.join(process.cwd(), "storage", "audio");
}
