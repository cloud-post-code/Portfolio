import path from "path";
import { count } from "drizzle-orm";
import { drizzle } from "drizzle-orm/postgres-js";
import { migrate } from "drizzle-orm/postgres-js/migrator";
import postgres from "postgres";
import { v4 as uuidv4 } from "uuid";
import { getDb } from "@/db/client";
import * as schema from "@/db/schema";
import { getDatabaseUrl } from "@/lib/env";

export async function runMigrations(): Promise<void> {
  const url = getDatabaseUrl();
  const migrationClient = postgres(url, { max: 1 });
  const db = drizzle(migrationClient);
  await migrate(db, { migrationsFolder: path.join(process.cwd(), "drizzle") });
  await migrationClient.end({ timeout: 5 });
}

export async function seedRootFolders(): Promise<void> {
  const db = getDb();
  const [row] = await db.select({ c: count() }).from(schema.folders);
  if ((row?.c ?? 0) > 0) return;

  const now = new Date();
  const roots = ["Company", "Blog", "Ideas", "Inbox"] as const;
  for (const name of roots) {
    await db.insert(schema.folders).values({
      id: uuidv4(),
      parentId: null,
      name,
      createdAt: now,
    });
  }
}
