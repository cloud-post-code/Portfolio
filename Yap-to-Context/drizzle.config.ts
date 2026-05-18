import { defineConfig } from "drizzle-kit";

/** Drizzle Kit CLI only — avoid localhost fallback on Railway (no Postgres on 127.0.0.1). */
function migrationDatabaseUrl(): string {
  const url = process.env.DATABASE_URL?.trim();
  if (url) return url;
  if (process.env.RAILWAY_ENVIRONMENT || process.env.RAILWAY_PROJECT_ID) {
    throw new Error(
      "DATABASE_URL is missing. In Railway: add a Postgres service, open this service → Variables → New variable → Reference → Postgres → DATABASE_URL.",
    );
  }
  return "postgresql://localhost:5432/yap_to_context";
}

export default defineConfig({
  schema: "./src/db/schema.ts",
  out: "./drizzle",
  dialect: "postgresql",
  dbCredentials: {
    url: migrationDatabaseUrl(),
  },
});
