import { drizzle } from "drizzle-orm/postgres-js";
import type { PostgresJsDatabase } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import { and, eq, isNull } from "drizzle-orm";
import * as schema from "./schema";
import { getDatabaseUrl } from "@/lib/env";

export type DbClient = PostgresJsDatabase<typeof schema>;

declare global {
  var __yap_postgres: ReturnType<typeof postgres> | undefined;
  var __yap_db: DbClient | undefined;
}

function createSql() {
  const url = getDatabaseUrl();
  return postgres(url, { max: 10 });
}

export function getDb(): DbClient {
  if (!globalThis.__yap_postgres) {
    globalThis.__yap_postgres = createSql();
  }
  if (!globalThis.__yap_db) {
    globalThis.__yap_db = drizzle(globalThis.__yap_postgres, { schema });
  }
  return globalThis.__yap_db;
}

export async function getRootFolderIdByName(
  name: string,
): Promise<string | undefined> {
  const db = getDb();
  const row = await db
    .select()
    .from(schema.folders)
    .where(
      and(isNull(schema.folders.parentId), eq(schema.folders.name, name)),
    )
    .limit(1);
  return row[0]?.id;
}

export async function requireInboxFolderId(): Promise<string> {
  const id = await getRootFolderIdByName("Inbox");
  if (!id) throw new Error("Inbox folder missing");
  return id;
}
